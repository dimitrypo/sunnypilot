from types import SimpleNamespace

import pytest

from openpilot.sunnypilot.selfdrive.controls.lib.tesla_steering_pause import TeslaSteeringPause


class TestTeslaSteeringPause:
  def setup_method(self):
    self.pause = TeslaSteeringPause()
    self.CS = SimpleNamespace(steeringTorque=0.0, steeringRateDeg=0.0, steeringAngleDeg=2.0,
                              steeringDisengage=False, steerFaultTemporary=False, steerFaultPermanent=False, canValid=True)
    self.now = 10.0
    self.target = 0.0
    self.zero_since = None

  def step(self, *, torque=None, rate=None, angle=None, dt=0.01, active=True, valid=True, resume_allowed=True):
    for key, value in (("steeringTorque", torque), ("steeringRateDeg", rate), ("steeringAngleDeg", angle)):
      if value is not None:
        setattr(self.CS, key, value)
    self.now += dt
    return self.pause.update(self.CS, requested_active=active, target_angle=self.target, sample_time=self.now, valid=valid,
                             resume_allowed=resume_allowed, hands_on_zero_since=self.zero_since)

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

  @pytest.mark.parametrize("torque", [-1.49, -0.8, 0.8, 1.49])
  def test_firm_settled_input_remains_paused_without_a_timeout(self, torque):
    self.enter_pause()
    for _ in range(1000):
      assert not self.step(torque=torque, angle=2)

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
    assert self.step()

  @pytest.mark.parametrize("angle_error", [-1.0, 0.0, 1.0])
  @pytest.mark.parametrize("torque,rate", [(-4.0, -90.0), (-0.5, 0.0), (0.5, 0.0), (4.0, 90.0)])
  def test_aligned_held_wheel_recovers_immediately_without_retrigger(self, angle_error, torque, rate):
    self.enter_pause()
    self.target = 10.0
    assert self.step(torque=torque, angle=self.target + angle_error, rate=rate)
    assert self.pause.reason == "aligned"
    for _ in range(100):
      assert self.step()

  @pytest.mark.parametrize("angle_error", [-1.0001, 1.0001])
  def test_just_outside_alignment_uses_light_contact_delay(self, angle_error):
    self.enter_pause()
    self.assert_recovers_after(0.5, torque=0.5, angle=angle_error)

  @pytest.mark.parametrize("angle", [-1.0001, 1.0001])
  def test_strong_input_just_outside_alignment_keeps_pause(self, angle):
    self.enter_pause()
    for _ in range(100):
      assert not self.step(torque=2.0, angle=angle, rate=90)

  def test_alignment_cannot_override_a_true_hard_disengagement(self):
    self.enter_pause()
    self.CS.steeringDisengage = True
    for _ in range(100):
      assert not self.step(torque=2.0, angle=0, rate=90)

  def test_eps_release_recovers_despite_residual_torque_and_motion(self):
    self.enter_pause()
    self.zero_since = self.now
    self.assert_recovers_after(0.2, torque=1.0, rate=20, angle=15)
    assert self.pause.reason == "released_eps"
    for _ in range(100):
      assert self.step()  # Residual torque must not immediately pause again.
    self.zero_since = None
    for _ in range(5):
      assert self.step()
    assert not self.step()  # Renewed detected input restores ordinary entry.

  def test_eps_release_does_not_inherit_time_from_before_the_handover(self):
    self.enter_pause()
    self.zero_since = self.now - 10
    self.assert_recovers_after(0.2, torque=1.0)

  @pytest.mark.parametrize("torque", [-1.5, 1.5])
  def test_renewed_strong_force_vetoes_filtered_eps_release(self, torque):
    self.enter_pause()
    self.zero_since = self.now
    for _ in range(100):
      assert not self.step(torque=torque)
    self.assert_recovers_after(0.2, torque=1.0)

  def test_new_eps_zero_interval_resets_release_evidence(self):
    self.enter_pause()
    self.zero_since = self.now
    for _ in range(19):
      assert not self.step(torque=1.0)
    self.zero_since = self.now + 0.01
    self.assert_recovers_after(0.2)

  def test_unavailable_eps_signal_cannot_release_firm_input(self):
    self.enter_pause()
    self.zero_since = self.now
    for _ in range(19):
      assert not self.step(torque=1.0)
    self.zero_since = None
    for _ in range(200):
      assert not self.step()

  def test_torque_and_eps_release_do_not_restart_same_quiet_period(self):
    self.enter_pause()
    self.zero_since = self.now
    assert not self.step(torque=0.1)
    for i in range(19):
      assert not self.step(torque=0.9 if i % 2 else 0.1)
    assert self.step(torque=0.9)

  def test_confirmed_eps_zero_defers_moderate_entry_until_holding_is_reported(self):
    self.zero_since = self.now - 1
    for _ in range(30):
      assert self.step(torque=1.0, rate=20, angle=5)
    # EPS is filtered: the normal entry debounce starts when that estimate
    # changes, whereas current strong force still takes priority immediately.
    self.zero_since = None
    for _ in range(5):
      assert self.step()
    assert not self.step()

  @pytest.mark.parametrize("zero_since", [float('nan'), float('inf'), -1.0, 100.0])
  def test_invalid_eps_interval_cannot_release_firm_input(self, zero_since):
    self.enter_pause()
    self.zero_since = zero_since
    for _ in range(100):
      assert not self.step(torque=1.0)

  def test_alignment_is_rechecked_when_planner_changes(self):
    assert self.step(torque=2, angle=0, rate=90)
    self.target = 5.0
    assert not self.step()
    self.target = 0.0
    assert self.step()

  def test_continued_maneuver_keeps_pause(self):
    self.enter_pause()
    for _ in range(500):
      assert not self.step(torque=0.5, rate=10)

  def test_release_ends_firm_hold_after_point_two_seconds(self):
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
    for _ in range(200):
      assert not self.step(torque=1.0, angle=2)
    self.assert_recovers_after(0.5, torque=0.5)

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

  def test_duplicate_sample_cannot_trigger_alignment_recovery(self):
    self.enter_pause()
    assert not self.step(angle=0, dt=0)
    assert self.step()

  def test_alignment_waits_for_envelope_only_when_recovering(self):
    self.enter_pause()
    assert not self.step(angle=0, resume_allowed=False)
    assert self.step(resume_allowed=True)
    assert self.step(resume_allowed=False)  # Do not newly pause active steering.

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
