from types import SimpleNamespace

import pytest

from openpilot.sunnypilot.selfdrive.controls.lib.tesla_steering_pause import TeslaSteeringPause


class TestTeslaSteeringPause:
  def setup_method(self):
    self.pause = TeslaSteeringPause()
    self.CS = SimpleNamespace(steeringTorque=0.0, steeringRateDeg=0.0, steeringAngleDeg=0.0,
                              steeringDisengage=False, steerFaultTemporary=False, steerFaultPermanent=False, canValid=True)
    self.now = 10.0
    self.target = 0.0

  def step(self, *, torque=None, rate=None, angle=None, dt=0.01, active=True, valid=True, resume_allowed=True):
    for key, value in (("steeringTorque", torque), ("steeringRateDeg", rate), ("steeringAngleDeg", angle)):
      if value is not None:
        setattr(self.CS, key, value)
    self.now += dt
    return self.pause.update(self.CS, requested_active=active, target_angle=self.target, sample_time=self.now, valid=valid,
                             resume_allowed=resume_allowed)

  def enter_pause(self):
    assert not self.step(torque=1.5)

  def assert_recovers_after(self, seconds, **signals):
    assert not self.step(**signals)
    for _ in range(round(seconds / 0.01) - 1):
      assert not self.step()
    assert self.step()

  def test_small_corrections_keep_cooperative_steering(self):
    for _ in range(200):
      assert self.step(torque=0.5, rate=2, angle=1)

  def test_moderate_intervention_is_debounced_in_both_directions(self):
    for direction in (-1, 1):
      self.pause.reset()
      for _ in range(5):
        assert self.step(torque=direction, rate=10 * direction)
      assert not self.step()

  def test_brief_input_spike_does_not_pause(self):
    for _ in range(4):
      assert self.step(torque=1, rate=10)
    assert self.step(torque=0, rate=0)
    for _ in range(4):
      assert self.step(torque=1, rate=10)

  def test_strong_input_yields_immediately_without_motion(self):
    self.enter_pause()
    for _ in range(400):
      assert not self.step()

  def test_no_input_recovers_in_point_two_seconds_despite_angle_or_wheel_return(self):
    self.enter_pause()
    self.assert_recovers_after(0.2, torque=0.1, rate=20, angle=15)

  def test_light_settled_input_recovers_in_half_a_second(self):
    self.enter_pause()
    self.assert_recovers_after(0.5, torque=0.5, angle=2)

  def test_firm_settled_input_recovers_in_one_and_a_half_seconds_without_retrigger(self):
    self.enter_pause()
    self.assert_recovers_after(1.5, torque=1.0, angle=2)
    for _ in range(100):
      assert self.step()

  def test_steady_offset_with_force_keeps_pause(self):
    self.enter_pause()
    for _ in range(500):
      assert not self.step(torque=0.5, angle=10, rate=0)
    self.assert_recovers_after(0.2, torque=0)

  def test_live_target_agreement_can_end_hold(self):
    self.enter_pause()
    for _ in range(200):
      assert not self.step(torque=0.5, angle=10)
    self.target = 10
    self.assert_recovers_after(0.2)

  @pytest.mark.parametrize("angle_error", [-1.0, 0.0, 1.0])
  @pytest.mark.parametrize("torque", [-1.49, -0.5, 0.5, 1.49])
  def test_aligned_held_wheel_recovers_without_retrigger(self, angle_error, torque):
    self.enter_pause()
    self.target = 10.0
    self.assert_recovers_after(0.2, torque=torque, angle=self.target + angle_error, rate=0)
    assert self.pause.reason == "aligned"
    for _ in range(100):
      assert self.step()

  @pytest.mark.parametrize("angle_error", [-1.0001, 1.0001])
  def test_just_outside_alignment_uses_light_contact_delay(self, angle_error):
    self.enter_pause()
    self.assert_recovers_after(0.5, torque=0.5, angle=angle_error)

  @pytest.mark.parametrize("rate", [-5.0, 5.0])
  def test_moving_through_aligned_angle_does_not_resume(self, rate):
    self.enter_pause()
    for _ in range(100):
      assert not self.step(torque=0.5, angle=0, rate=rate)
    self.assert_recovers_after(0.2, rate=0)

  @pytest.mark.parametrize("torque", [-1.5, 1.5])
  def test_strong_override_beats_alignment(self, torque):
    self.enter_pause()
    for _ in range(100):
      assert not self.step(torque=torque, angle=0, rate=0)

  def test_release_and_alignment_share_continuous_recovery_time(self):
    self.enter_pause()
    assert not self.step(torque=0.19)
    for i in range(19):
      assert not self.step(torque=0.21 if i % 2 == 0 else 0.19)
    assert self.step(torque=0.21)

  def test_leaving_alignment_restarts_fast_recovery(self):
    self.enter_pause()
    for _ in range(15):
      assert not self.step(torque=1.0, angle=0)
    assert not self.step(angle=1.01)
    self.assert_recovers_after(0.2, angle=0)

  @pytest.mark.parametrize("torque,delay", [(0.5, 0.5), (1.0, 1.5)])
  def test_alignment_boundary_noise_does_not_delay_ordinary_recovery(self, torque, delay):
    self.enter_pause()
    assert not self.step(torque=torque, angle=0.99)
    for i in range(round(delay / 0.01) - 1):
      assert not self.step(angle=1.01 if i % 2 == 0 else 0.99)
    assert self.step(angle=1.01)

  def test_renewed_correction_resets_both_recovery_timers(self):
    self.enter_pause()
    for _ in range(45):
      assert not self.step(torque=0.5, angle=2)
    for _ in range(10):
      assert not self.step(angle=10)
    self.assert_recovers_after(0.2, angle=0)

  def test_planner_change_resets_alignment_recovery(self):
    self.enter_pause()
    for _ in range(15):
      assert not self.step(torque=0.5, angle=0)
    self.target = 5.0
    assert not self.step()
    self.target = 0.0
    self.assert_recovers_after(0.2)

  def test_continued_maneuver_keeps_pause(self):
    self.enter_pause()
    for _ in range(500):
      assert not self.step(torque=0.5, rate=10)

  def test_release_shortens_firm_delay(self):
    self.enter_pause()
    for _ in range(100):
      assert not self.step(torque=1.0, angle=2)
    self.assert_recovers_after(0.2, torque=0.0)

  def test_renewed_input_restarts_quiet_period(self):
    self.enter_pause()
    for _ in range(10):
      assert not self.step(torque=0)
    assert not self.step(torque=1, rate=10)
    self.assert_recovers_after(0.2, torque=0, rate=0)

  def test_change_to_firmer_contact_does_not_use_short_delay(self):
    self.enter_pause()
    for _ in range(10):
      assert not self.step(torque=0)
    self.assert_recovers_after(1.5, torque=1.0, angle=2)

  def test_disengaged_state_cannot_be_enabled_by_timer(self):
    self.enter_pause()
    for _ in range(500):
      assert not self.step(torque=0, active=False)
    assert not self.pause.paused
    assert self.step(active=True)  # a NEW upstream engagement

  def test_hard_override_requires_upstream_disengagement(self):
    self.CS.steeringDisengage = True
    assert not self.step()
    self.CS.steeringDisengage = False
    for _ in range(400):
      assert not self.step(torque=0)
    assert not self.step(active=False)
    assert self.step(active=True)

  def test_fault_or_invalid_signals_never_advance_release(self):
    for field, invalid_value in (("steerFaultTemporary", True), ("steerFaultPermanent", True), ("canValid", False),
                                 ("steeringTorque", float('nan')), ("steeringAngleDeg", float('inf')),
                                 ("steeringRateDeg", float('nan'))):
      self.setup_method()
      self.enter_pause()
      self.CS.steeringTorque = 0
      original = getattr(self.CS, field)
      setattr(self.CS, field, invalid_value)
      for _ in range(60):
        assert not self.step()
      setattr(self.CS, field, original)
      self.assert_recovers_after(0.2)

  def test_invalid_message_and_target_reset_recovery(self):
    for bad_target in (False, True):
      self.setup_method()
      self.enter_pause()
      if bad_target:
        self.target = float('nan')
      for _ in range(60):
        assert not self.step(torque=0, valid=bad_target)
      self.target = 0
      self.assert_recovers_after(0.2)

  def test_duplicate_timestamp_does_not_advance_timer(self):
    self.enter_pause()
    assert not self.step(torque=0)
    for _ in range(1000):
      assert not self.step(dt=0)
    for _ in range(19):
      assert not self.step()
    assert self.step()

  def test_sample_gap_is_not_counted_as_release(self):
    self.enter_pause()
    for _ in range(10):
      assert not self.step(torque=0)
    assert not self.step(dt=1.0)
    for _ in range(19):
      assert not self.step()
    assert self.step()

  def test_time_going_backwards_cannot_resume(self):
    self.enter_pause()
    assert not self.step(torque=0)
    assert not self.step(dt=-1.0)
    for _ in range(50):
      assert not self.step()

  def test_completed_release_waits_for_angle_envelope_without_restarting_timer(self):
    self.enter_pause()
    for _ in range(100):
      assert not self.step(torque=0, resume_allowed=False)
    assert self.pause.reason == "angle_limit"
    assert self.step(resume_allowed=True)

  def test_angle_envelope_permission_does_not_shortcut_release_timer(self):
    self.enter_pause()
    for _ in range(10):
      assert not self.step(torque=0, resume_allowed=False)
    for _ in range(10):
      assert not self.step(resume_allowed=True)
    assert self.step()
