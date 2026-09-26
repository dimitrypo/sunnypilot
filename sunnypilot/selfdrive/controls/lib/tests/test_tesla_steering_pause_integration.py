import math
import sys
from types import SimpleNamespace

import pytest

from cereal import car, log
from opendbc.car.lateral import apply_steer_angle_limits_vm, get_max_angle_delta_vm, get_max_angle_vm
from opendbc.car.tesla.carcontroller import get_safety_CP
from opendbc.car.tesla.interface import CarInterface
from opendbc.car.tesla.values import CarControllerParams
from opendbc.car.vehicle_model import VehicleModel
from openpilot.selfdrive.controls.lib.latcontrol_angle import LatControlAngle
from openpilot.selfdrive.controls.lib.longcontrol import LongControl
from openpilot.sunnypilot.selfdrive.controls.controlsd_ext import ControlsExt
from openpilot.sunnypilot.selfdrive.controls.lib.tesla_steering_pause import TeslaSteeringPause


class SubMasterStub(dict):
  def __init__(self, messages):
    super().__init__(messages)
    self.valid = dict.fromkeys(messages, True)
    self.valid["lateralManeuverPlan"] = False
    self.alive = dict.fromkeys(messages, True)
    self.logMonoTime = {"carState": 10_000_000_000}
    self.checked_services = []

  def all_checks(self, services):
    self.checked_services = services
    return all(self.valid[service] and self.alive[service] for service in services)


class TestTeslaSteeringPauseIntegration:
  @pytest.fixture(autouse=True)
  def setup_controls(self, mocker):
    self.mocker = mocker
    self.controls = ControlsExt.__new__(ControlsExt)
    self.controls.tesla_steering_pause = TeslaSteeringPause()
    self.controls.tesla_safety_vm = VehicleModel(get_safety_CP())
    self.controls.VM = SimpleNamespace(get_steer_from_curvature=mocker.Mock(side_effect=lambda curvature, speed, roll: curvature))
    self.controls.blinker_pause_lateral = SimpleNamespace(update=mocker.Mock(return_value=False))
    self.CS = SimpleNamespace(steeringTorque=0.0, steeringRateDeg=0.0, steeringAngleDeg=0.0, vEgo=20.0, vEgoRaw=20.0,
                              steeringDisengage=False, steerFaultTemporary=False, steerFaultPermanent=False, canValid=True)
    self.ss = SimpleNamespace(active=True, enabled=True)
    self.mads = SimpleNamespace(available=False, active=False)
    self.sm = SubMasterStub({
      "carState": self.CS,
      "carOutput": SimpleNamespace(actuatorsOutput=SimpleNamespace(steeringAngleDeg=0.0)),
      "selfdriveState": self.ss,
      "selfdriveStateSP": SimpleNamespace(mads=self.mads),
      "liveParameters": SimpleNamespace(roll=0.0, angleOffsetDeg=0.0),
      "modelV2": SimpleNamespace(),
      "lateralManeuverPlan": SimpleNamespace(),
    })
    self.cloudlog = mocker.patch("openpilot.sunnypilot.selfdrive.controls.controlsd_ext.cloudlog")

  def step(self, lat_active=True, curvature=0.0):
    self.sm.logMonoTime["carState"] += 10_000_000
    return self.controls.apply_tesla_steering_pause(self.sm, lat_active, curvature)

  def assert_release_delay(self):
    for _ in range(50):
      assert not self.step()
    assert self.step()

  def test_hard_override_and_fault_latch_until_upstream_disengages(self):
    self.CS.steeringDisengage = self.CS.steerFaultTemporary = True
    assert not self.step(lat_active=False)
    self.CS.steeringDisengage = self.CS.steerFaultTemporary = False
    for _ in range(400):
      assert not self.step()
    self.ss.active = False
    assert not self.step(lat_active=False)
    self.ss.active = True
    assert self.step()

  def test_temporary_fault_preserves_pause_and_restarts_release_delay(self):
    self.CS.steeringTorque = 1.5
    assert not self.step()
    self.CS.steeringTorque = 0.0
    for _ in range(40):
      assert not self.step()
    self.CS.steerFaultTemporary = True
    assert not self.step(lat_active=False)
    self.CS.steerFaultTemporary = False
    self.assert_release_delay()

  def test_blinker_suppression_cannot_clear_hard_override(self):
    self.CS.steeringDisengage = True
    assert not self.step()
    self.CS.steeringDisengage = False
    self.controls.blinker_pause_lateral.update.return_value = True
    for _ in range(400):
      assert not self.step(lat_active=self.controls.get_lat_active(self.sm))
    self.controls.blinker_pause_lateral.update.return_value = False
    assert not self.step(lat_active=self.controls.get_lat_active(self.sm))

  def test_actuator_suppression_remains_authoritative_after_recovery(self):
    self.CS.steeringTorque = 1.5
    assert not self.step()
    self.CS.steeringTorque = 0.0
    for _ in range(100):
      assert not self.step(lat_active=False)
    assert not self.controls.tesla_steering_pause.paused
    assert self.step(lat_active=True)

  def test_mads_uses_its_own_upstream_engagement_state(self):
    self.mads.available = True
    self.mads.active = True
    self.ss.active = self.ss.enabled = False
    self.CS.steeringDisengage = True
    assert not self.step()
    self.CS.steeringDisengage = False
    for _ in range(100):
      assert not self.step()
    self.mads.active = False
    assert not self.step(lat_active=False)
    self.mads.active = True
    assert self.step()

  def test_live_planner_angle_keeps_offset_hold_until_release(self):
    self.CS.steeringTorque = 1.5
    self.CS.steeringAngleDeg = 10.0
    assert not self.step()
    self.CS.steeringTorque = 0.5
    # These normally follow measured steering during the pause. Neither should
    # replace the independent planned target used to detect a held correction.
    self.controls.curvature = self.controls.desired_curvature = -math.radians(10)
    for _ in range(400):
      assert not self.step(curvature=0.0)
    self.controls.VM.get_steer_from_curvature.assert_called_with(-0.0, 20.0, 0.0)
    self.CS.steeringTorque = 0.0
    self.assert_release_delay()

  def test_stale_selected_plan_resets_recovery(self):
    for use_maneuver_plan in (False, True):
      self.controls.tesla_steering_pause.reset()
      self.sm.valid["lateralManeuverPlan"] = use_maneuver_plan
      selected_plan = "lateralManeuverPlan" if use_maneuver_plan else "modelV2"
      self.CS.steeringTorque = 1.5
      assert not self.step()
      self.CS.steeringTorque = 0.0
      for _ in range(40):
        assert not self.step()
      self.sm.alive[selected_plan] = False
      assert not self.step()
      assert selected_plan in self.sm.checked_services
      self.sm.alive[selected_plan] = True
      self.assert_release_delay()

  def test_absent_personal_helper_preserves_other_vehicle_permissions(self):
    self.controls.tesla_steering_pause = None
    for permission in (True, False):
      assert self.controls.apply_tesla_steering_pause({}, permission, 0.0) == permission

  def actual_controls(self):
    # Isolate eager discovery of unrelated vehicles and model-process startup.
    # state_control, ControlsExt, both controllers, VehicleModel and Cap'n Proto
    # messages are real. Sensor messages and process transports are stand-ins.
    # patch.dict restores sys.modules so these import stubs cannot leak to tests.
    with self.mocker.mock_module.patch.dict(sys.modules, {
      "opendbc.car.car_helpers": SimpleNamespace(interfaces={}),
      "openpilot.selfdrive.modeld.modeld": SimpleNamespace(LAT_SMOOTH_SECONDS=0.0),
    }):
      from openpilot.selfdrive.controls.controlsd import Controls

    controls = Controls.__new__(Controls)
    controls.__dict__.update(self.controls.__dict__)
    controls.CP = CarInterface.get_non_essential_params("TESLA_MODEL_3")
    controls.CP.openpilotLongitudinalControl = True
    controls.CP_SP = SimpleNamespace(pcmCruiseSpeed=True, enableGasInterceptor=False)
    controls.CI = CarInterface
    controls.VM = VehicleModel(controls.CP)
    controls.LaC = LatControlAngle(controls.CP, controls.CP_SP, controls.CI, 0.01)
    controls.LoC = LongControl(controls.CP, controls.CP_SP)
    controls.LaC.reset = self.mocker.Mock(wraps=controls.LaC.reset)
    controls.LoC.reset = self.mocker.Mock(wraps=controls.LoC.reset)
    controls.curvature = controls.desired_curvature = 0.0
    controls.steer_limited_by_safety = False
    controls.calibrated_pose = None
    controls.sm = self.sm

    self.CS = car.CarState.new_message()
    self.CS.vEgo = 20.0
    self.CS.vEgoRaw = 20.0
    self.CS.vCruise = 90.0
    self.CS.steeringAngleDeg = 12.0
    self.CS.steeringTorque = 1.5
    self.CS.steeringPressed = True
    self.CS.canValid = True
    self.sm.update({
      "carState": self.CS,
      "liveParameters": SimpleNamespace(stiffnessFactor=1.0, steerRatio=controls.CP.steerRatio, roll=0.0, angleOffsetDeg=0.0),
      "modelV2": SimpleNamespace(action=SimpleNamespace(desiredCurvature=0.0),
                                  meta=SimpleNamespace(laneChangeState=log.LaneChangeState.off)),
      "longitudinalPlan": SimpleNamespace(aTarget=0.3, shouldStop=False),
      "onroadEvents": [],
      "liveDelay": SimpleNamespace(lateralDelay=0.2),
    })
    self.controls = controls
    return controls

  def state_control_step(self):
    self.sm.logMonoTime["carState"] += 10_000_000
    return self.controls.state_control()

  def test_actual_controller_preserves_speed_and_resumes_from_measured_angle(self):
    controls = self.actual_controls()
    CC, lateral_log = self.state_control_step()
    assert CC.enabled and CC.longActive and not CC.latActive
    assert CC.actuators.accel > 0
    assert CC.actuators.steeringAngleDeg == self.CS.steeringAngleDeg
    assert not lateral_log.active
    assert controls.LaC.reset.call_count == 1
    assert controls.LoC.reset.call_count == 0
    assert self.CS.steeringPressed  # No synthetic hands-off signal was substituted.

    self.CS.steeringTorque = 0.0
    for _ in range(50):
      CC, _ = self.state_control_step()
      assert CC.enabled and CC.longActive and not CC.latActive
      assert CC.actuators.accel > 0
      assert CC.actuators.steeringAngleDeg == self.CS.steeringAngleDeg
    CC, lateral_log = self.state_control_step()
    assert CC.enabled and CC.longActive and CC.latActive and lateral_log.active
    assert 0 < self.CS.steeringAngleDeg - CC.actuators.steeringAngleDeg < 1.0
    assert controls.LoC.reset.call_count == 0

  def test_actual_controller_hard_override_survives_temporary_fault_clearance(self):
    controls = self.actual_controls()
    self.CS.steeringDisengage = self.CS.steerFaultTemporary = True
    CC, _ = self.state_control_step()
    assert not CC.latActive
    self.CS.steeringDisengage = self.CS.steerFaultTemporary = False
    self.CS.steeringTorque = 0.0
    for _ in range(100):
      CC, _ = self.state_control_step()
      assert not CC.latActive
    assert controls.tesla_steering_pause.hard_disengaged
    # Full disengagement still belongs to selfdrived/Panda; the helper neither
    # defeats that upstream state nor re-arms itself before a new engagement.
    self.ss.active = self.ss.enabled = False
    CC, _ = self.state_control_step()
    assert not (CC.latActive or CC.longActive or CC.enabled)

  @pytest.mark.parametrize("direction", [-1, 1])
  def test_recovery_waits_for_supported_angle_without_an_abrupt_clamp(self, direction):
    controls = self.actual_controls()
    self.CS.steeringAngleDeg = 30.0 * direction
    CC, _ = self.state_control_step()
    assert not CC.latActive
    self.CS.steeringTorque = 0.0
    for _ in range(100):
      CC, _ = self.state_control_step()
      assert CC.enabled and CC.longActive and not CC.latActive
      assert CC.actuators.steeringAngleDeg == self.CS.steeringAngleDeg
    assert controls.tesla_steering_pause.reason == "angle_limit"

    max_angle = get_max_angle_vm(self.CS.vEgoRaw, controls.tesla_safety_vm, CarControllerParams)
    # Model a wheel returning within the existing envelope after release.
    self.CS.steeringAngleDeg = direction * (max_angle - 1.0)
    CC, _ = self.state_control_step()
    assert CC.latActive  # The completed release timer was not restarted.
    actual_command = apply_steer_angle_limits_vm(CC.actuators.steeringAngleDeg, self.CS.steeringAngleDeg,
                                                self.CS.vEgoRaw, self.CS.steeringAngleDeg, CC.latActive,
                                                CarControllerParams, controls.tesla_safety_vm)
    max_step = min(get_max_angle_delta_vm(self.CS.vEgoRaw, controls.tesla_safety_vm, CarControllerParams),
                   CarControllerParams.ANGLE_LIMITS.MAX_ANGLE_RATE)
    assert abs(actual_command - self.CS.steeringAngleDeg) <= max_step + 1e-9
    assert abs(actual_command) <= max_angle

  @pytest.mark.parametrize("invalid_speed", [float('nan'), float('inf'), -float('inf')])
  def test_nonfinite_raw_speed_cannot_resume(self, invalid_speed):
    self.CS.steeringTorque = 1.5
    assert not self.step()
    self.CS.steeringTorque = 0.0
    self.CS.vEgoRaw = invalid_speed
    for _ in range(100):
      assert not self.step()
    self.CS.vEgoRaw = 20.0
    self.assert_release_delay()

  def test_recovery_waits_for_last_applied_angle_to_catch_up(self):
    self.CS.steeringTorque = 1.5
    self.CS.steeringAngleDeg = 30.0
    self.sm["carOutput"].actuatorsOutput.steeringAngleDeg = 30.0
    assert not self.step()
    self.CS.steeringTorque = 0.0
    for _ in range(100):
      assert not self.step()
    self.CS.steeringAngleDeg = 10.0
    # The measured angle entered the envelope, but the last CAN command did not.
    assert not self.step()
    assert self.controls.tesla_steering_pause.reason == "angle_limit"
    self.sm["carOutput"].actuatorsOutput.steeringAngleDeg = 10.0
    assert self.step()

  def test_stale_car_output_blocks_recovery_without_restarting_quiet_time(self):
    self.CS.steeringTorque = 1.5
    assert not self.step()
    self.CS.steeringTorque = 0.0
    self.sm.alive["carOutput"] = False
    for _ in range(100):
      assert not self.step()
    self.sm.alive["carOutput"] = True
    assert self.step()

  @pytest.mark.parametrize("invalid_angle", [float('nan'), float('inf')])
  def test_nonfinite_applied_angle_blocks_recovery(self, invalid_angle):
    self.CS.steeringTorque = 1.5
    assert not self.step()
    self.CS.steeringTorque = 0.0
    self.sm["carOutput"].actuatorsOutput.steeringAngleDeg = invalid_angle
    for _ in range(100):
      assert not self.step()
    self.sm["carOutput"].actuatorsOutput.steeringAngleDeg = 0.0
    assert self.step()

  def test_stale_car_output_does_not_itself_pause_active_steering(self):
    self.sm.alive["carOutput"] = False
    assert self.step()
