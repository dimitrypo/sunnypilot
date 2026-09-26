from types import SimpleNamespace

from openpilot.selfdrive.ui.sunnypilot.tesla_status import tesla_steering_pause_status


class TestTeslaSteeringPauseStatus:
  def setup_method(self):
    self.CS = SimpleNamespace(canValid=True, steerFaultTemporary=False, steerFaultPermanent=False, steeringDisengage=False)
    self.CC = SimpleNamespace(enabled=True, latActive=False, longActive=True)

  def status(self, status="engaged", fingerprint="TESLA_MODEL_3", valid=True):
    return tesla_steering_pause_status(status, fingerprint, self.CS, self.CC, valid)

  def test_paused_steering_with_either_speed_controller(self):
    for long_active in (True, False):
      self.CC.longActive = long_active
      assert self.status() == "long_only"

  def test_steering_recovery_restores_existing_status(self):
    self.CC.latActive = True
    assert self.status() == "engaged"

  def test_preserves_override_and_disabled_statuses(self):
    for status in ("override", "disengaged", "lat_only", "long_only"):
      assert self.status(status=status) == status
    self.CC.enabled = False
    assert self.status() == "engaged"

  def test_invalid_or_stale_messages_do_not_change_status(self):
    assert self.status(valid=False) == "engaged"
    self.CS.canValid = False
    assert self.status() == "engaged"

  def test_faults_and_hard_override_do_not_change_status(self):
    for fault in ("steerFaultTemporary", "steerFaultPermanent", "steeringDisengage"):
      setattr(self.CS, fault, True)
      assert self.status() == "engaged"
      setattr(self.CS, fault, False)

  def test_other_vehicles_unchanged(self):
    for fingerprint in (None, "TESLA_MODEL_Y", "TESLA_MODEL_X", "HONDA_CIVIC"):
      assert self.status(fingerprint=fingerprint) == "engaged"
