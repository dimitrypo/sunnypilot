import pytest

from cereal import log
from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car.tesla.values import CAR, CANBUS, DBC
from openpilot.sunnypilot.selfdrive.controls.lib.tesla_hands_on import TeslaHandsOnMonitor


class TestTeslaHandsOnMonitor:
  def setup_method(self):
    self.monitor = TeslaHandsOnMonitor()
    self.packer = CANPacker(DBC[CAR.TESLA_MODEL_3][Bus.party])
    self.now = 10_000_000_000

  def frame(self, level=0, *, bus=CANBUS.party):
    return self.packer.make_can_msg("EPAS3S_sysStatus", bus, {"EPAS3S_handsOnLevel": level})

  def message(self, level=0, *, timestamp=None, valid=True, frames=None, bus=CANBUS.party):
    event = log.Event.new_message(valid=valid, logMonoTime=self.now if timestamp is None else timestamp)
    frames = [self.frame(level, bus=bus)] if frames is None else frames
    can = event.init("can", len(frames))
    for target, (address, data, src) in zip(can, frames, strict=True):
      target.address, target.dat, target.src = address, data, src
    return event.to_bytes()

  def step(self, level=0, *, elapsed=10_000_000, **kwargs):
    self.now += elapsed
    return self.monitor.update([self.message(level, **kwargs)], self.now)

  def test_startup_and_unrelated_messages_do_not_use_parser_default_zero(self):
    assert self.monitor.update([], self.now) is None
    assert self.step(frames=[(0x123, b"\x00" * 8, CANBUS.party)]) is None
    assert self.step(frames=[]) is None

  def test_valid_zero_level_tracks_the_first_sample_on_cereal_monotonic_clock(self):
    start = self.now + 10_000_000
    for _ in range(30):
      assert self.step() == pytest.approx(start * 1e-9)

  @pytest.mark.parametrize("level", [1, 2, 3])
  def test_every_nonzero_level_ends_the_interval(self, level):
    assert self.step() is not None
    assert self.step(level) is None
    assert self.step() == pytest.approx(self.now * 1e-9)

  @pytest.mark.parametrize("bus", [1, CANBUS.autopilot_party, 128])
  def test_other_buses_cannot_establish_release(self, bus):
    for _ in range(30):
      assert self.step(bus=bus) is None

  def test_wrong_bus_does_not_refresh_valid_signal(self):
    start = self.step()
    assert self.step(bus=CANBUS.autopilot_party, elapsed=90_000_000) == start
    assert self.step(bus=CANBUS.autopilot_party, elapsed=20_000_000) is None

  def test_zero_estimate_expires_without_new_matching_samples(self):
    start = self.step()
    assert self.monitor.update([], self.now + 100_000_000) == start
    assert self.monitor.update([], self.now + 100_000_001) is None

  def test_sample_gap_restarts_interval_instead_of_counting_missing_time(self):
    assert self.step() is not None
    assert self.step(elapsed=100_000_001) == pytest.approx(self.now * 1e-9)

  def test_exact_maximum_sample_gap_preserves_interval(self):
    start = self.step()
    assert self.step(elapsed=100_000_000) == start

  @pytest.mark.parametrize("timestamp_offset", [-100_000_001, 1])
  def test_stale_or_future_sample_cannot_establish_or_preserve_release(self, timestamp_offset):
    assert self.step() is not None
    self.now += 10_000_000
    raw = self.message(timestamp=self.now + timestamp_offset)
    assert self.monitor.update([raw], self.now) is None
    assert self.step() == pytest.approx(self.now * 1e-9)

  @pytest.mark.parametrize("timestamp", [0, 9_999_999_999])
  def test_duplicate_or_backwards_sample_restarts_evidence(self, timestamp):
    assert self.monitor.update([self.message()], self.now) is not None
    sample_time = self.now if timestamp == 0 else timestamp
    assert self.monitor.update([self.message(timestamp=sample_time)], self.now) is None
    assert self.step() == pytest.approx(self.now * 1e-9)

  def test_zero_timestamp_is_not_a_valid_startup_sample(self):
    assert self.monitor.update([self.message(timestamp=0)], self.now) is None

  def test_backwards_current_clock_invalidates_interval(self):
    assert self.step() is not None
    assert self.monitor.update([], self.now - 1) is None
    assert self.step() == pytest.approx(self.now * 1e-9)

  def test_drained_batch_preserves_intermediate_nonzero_level(self):
    assert self.step() is not None
    messages = []
    for level in (0, 1, 0, 0):
      self.now += 10_000_000
      messages.append(self.message(level))
    assert self.monitor.update(messages, self.now) == pytest.approx((self.now - 10_000_000) * 1e-9)

  def test_intermediate_nonzero_in_same_event_also_restarts_interval(self):
    assert self.step() is not None
    frames = [self.frame(level) for level in (0, 1, 0)]
    assert self.step(frames=frames) == pytest.approx(self.now * 1e-9)

  @pytest.mark.parametrize("length", [0, 7, 9])
  def test_wrong_payload_length_invalidates_release(self, length):
    assert self.step() is not None
    assert self.step(frames=[(0x370, b"\x00" * length, CANBUS.party)]) is None
    assert self.step() == pytest.approx(self.now * 1e-9)

  def test_invalid_event_does_not_establish_or_preserve_release(self):
    assert self.step(valid=False) is None
    assert self.step() is not None
    assert self.step(valid=False) is None

  def test_corrupted_checksum_invalidates_release(self):
    assert self.step() is not None
    address, data, bus = self.frame()
    data = data[:-1] + bytes([data[-1] ^ 0xFF])
    assert self.step(frames=[(address, data, bus)]) is None
    assert self.step() == pytest.approx(self.now * 1e-9)

  def test_invalid_counter_sequence_does_not_sustain_release(self):
    assert self.step() is not None
    frame = self.frame()
    for _ in range(10):
      result = self.step(frames=[frame])
    assert result is None

  def test_malformed_serialization_invalidates_release(self):
    assert self.step() is not None
    assert self.monitor.update([b"malformed"], self.now) is None

  def test_non_can_event_invalidates_release(self):
    assert self.step() is not None
    event = log.Event.new_message(valid=True, logMonoTime=self.now)
    event.init("carState")
    assert self.monitor.update([event.to_bytes()], self.now) is None
