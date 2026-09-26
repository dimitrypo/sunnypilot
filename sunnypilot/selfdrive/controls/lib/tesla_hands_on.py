"""Read Tesla's existing EPS hands-on estimate without changing published CarState."""
import capnp

from cereal import log
from opendbc.can import CANParser
from opendbc.car import Bus
from opendbc.car.tesla.values import CAR, CANBUS, DBC


class TeslaHandsOnMonitor:
  MESSAGE = "EPAS3S_sysStatus"
  ADDRESS = 0x370
  SIGNAL = "EPAS3S_handsOnLevel"
  MAX_GAP_NANOS = 100_000_000

  def __init__(self):
    self.parser = CANParser(DBC[CAR.TESLA_MODEL_3][Bus.party], [(self.MESSAGE, 100)], CANBUS.party)
    self.last_sample_nanos = None
    self.last_now_nanos = None
    self.zero_since_nanos = None

  def update(self, can_messages: list[bytes], now_nanos: int) -> float | None:
    """Return the current zero-level interval's start, in monotonic seconds.

    now_nanos must use the same time.monotonic clock as cereal logMonoTime. The
    caller drains its CAN socket without conflation; this helper owns no socket.
    A missing/stale/invalid estimate returns None, never an assumed hands-off.
    The EPS signal estimates driver input; it does not prove physical contact.
    """
    if now_nanos <= 0 or (self.last_now_nanos is not None and now_nanos < self.last_now_nanos):
      self.zero_since_nanos = None
      return None
    self.last_now_nanos = now_nanos

    for raw in can_messages:
      try:
        with log.Event.from_bytes(raw) as event:
          if not event.valid or event.which() != "can":
            self.zero_since_nanos = None
            continue

          frames = [(frame.address, frame.dat, frame.src) for frame in event.can
                    if frame.address == self.ADDRESS and frame.src == CANBUS.party]
          if not frames:
            continue

          timestamp = event.logMonoTime
          if (timestamp <= 0 or timestamp > now_nanos or now_nanos - timestamp > self.MAX_GAP_NANOS or
              (self.last_sample_nanos is not None and timestamp <= self.last_sample_nanos)):
            self.zero_since_nanos = None
            continue
          if self.last_sample_nanos is None or timestamp - self.last_sample_nanos > self.MAX_GAP_NANOS:
            self.zero_since_nanos = None
          self.last_sample_nanos = timestamp

          # Several frames can share one event timestamp. Process their order so
          # a nonzero level between two zero readings still starts a new interval.
          for frame in frames:
            if len(frame[1]) != 8:
              self.zero_since_nanos = None
              continue
            updated = self.parser.update([(timestamp, [frame])])
            if self.ADDRESS not in updated or not self.parser.can_valid:
              self.zero_since_nanos = None
            elif self.parser.vl[self.MESSAGE][self.SIGNAL] != 0:
              self.zero_since_nanos = None
            elif self.zero_since_nanos is None:
              self.zero_since_nanos = timestamp
      except (capnp.KjException, ValueError):
        self.zero_since_nanos = None

    if self.last_sample_nanos is None or now_nanos - self.last_sample_nanos > self.MAX_GAP_NANOS:
      self.zero_since_nanos = None
    return self.zero_since_nanos * 1e-9 if self.zero_since_nanos is not None else None
