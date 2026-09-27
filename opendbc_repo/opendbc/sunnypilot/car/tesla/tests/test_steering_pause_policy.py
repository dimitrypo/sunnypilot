from types import SimpleNamespace

import pytest

from opendbc.can import CANPacker, CANParser
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.tesla.carcontroller import CarController
from opendbc.car.tesla.carstate import CarState
from opendbc.car.tesla.interface import CarInterface
from opendbc.car.tesla.values import CAR, CANBUS, DBC, TeslaFlags, TeslaSafetyFlags
from opendbc.sunnypilot.car.tesla.values import TeslaFlagsSP


def get_params(candidate=CAR.TESLA_MODEL_3, *, alpha_long=False, modern_encoding=False):
  fingerprint = gen_empty_fingerprint()
  if modern_encoding:
    fingerprint[CANBUS.party][0x054] = 8
  return CarInterface.get_params(candidate, fingerprint, [], alpha_long, False, False)


class ParsedTeslaState:
  def __init__(self, CP):
    self.state = CarState(CP, structs.CarParamsSP())
    self.parsers = CarState.get_can_parsers(CP, structs.CarParamsSP())
    self.packer = CANPacker(DBC[CP.carFingerprint][Bus.party])
    self.now = 10_000_000_000
    # Register the lazily requested CAN messages before feeding actual frames.
    self.state.update(self.parsers)

  def update(self, level, *, status=1, error=0, brake=0):
    self.now += 10_000_000
    frames = [
      self.packer.make_can_msg("EPAS3S_sysStatus", CANBUS.party, {
        "EPAS3S_handsOnLevel": level,
        "EPAS3S_eacStatus": status,
        "EPAS3S_eacErrorCode": error,
      }),
      self.packer.make_can_msg("DI_state", CANBUS.party, {"DI_cruiseState": 2}),
      self.packer.make_can_msg("ESP_status", CANBUS.party, {"ESP_driverBrakeApply": brake}),
    ]
    assert 0x370 in self.parsers[Bus.party].update([(self.now, frames)])
    result, _ = self.state.update(self.parsers)
    assert self.state.hands_on_level == level
    return result


@pytest.mark.parametrize("candidate", [CAR.TESLA_MODEL_3, CAR.TESLA_MODEL_Y, CAR.TESLA_MODEL_X])
@pytest.mark.parametrize("alpha_long", [False, True])
@pytest.mark.parametrize("modern_encoding", [False, True])
def test_only_personal_model_3_gets_paired_pause_flags(candidate, alpha_long, modern_encoding):
  CP = get_params(candidate, alpha_long=alpha_long, modern_encoding=modern_encoding)
  personal = candidate == CAR.TESLA_MODEL_3
  assert bool(CP.flags & TeslaFlags.STEERING_PAUSE) == personal
  assert bool(CP.safetyConfigs[0].safetyParam & TeslaSafetyFlags.STEERING_PAUSE) == personal
  assert bool(CP.safetyConfigs[0].safetyParam & TeslaSafetyFlags.LONG_CONTROL) == alpha_long
  assert CP.openpilotLongitudinalControl == alpha_long
  assert bool(CP.flags & TeslaFlags.FSD_14) == (personal and modern_encoding)
  assert bool(CP.safetyConfigs[0].safetyParam & TeslaSafetyFlags.FSD_14) == (personal and modern_encoding)
  assert CP.flags & TeslaFlags.MISSING_DAS_SETTINGS  # Independent existing car flag.


@pytest.mark.parametrize("candidate", [CAR.TESLA_MODEL_3, CAR.TESLA_MODEL_Y, CAR.TESLA_MODEL_X])
def test_level_three_disengagement_changes_only_for_personal_model_3(candidate):
  parser = ParsedTeslaState(get_params(candidate))
  for level in (0, 1, 2, 3, 3, 2, 0):
    result = parser.update(level)
    assert result.steeringDisengage == (level == 3 and candidate != CAR.TESLA_MODEL_3)
    assert result.cruiseState.enabled
    assert not result.steerFaultTemporary
    assert not result.steerFaultPermanent


def test_model_3_without_policy_flag_retains_original_hard_override():
  CP = get_params()
  CP.flags &= ~TeslaFlags.STEERING_PAUSE.value
  parser = ParsedTeslaState(CP)
  assert parser.update(3).steeringDisengage


@pytest.mark.parametrize("candidate", [CAR.TESLA_MODEL_3, CAR.TESLA_MODEL_Y])
@pytest.mark.parametrize("level", [0, 1, 2, 3])
def test_high_angle_rate_safety_fault_remains_full_disengagement(candidate, level):
  parser = ParsedTeslaState(get_params(candidate))
  result = parser.update(level, status=0, error=9)
  assert result.steeringDisengage
  assert result.steerFaultTemporary


@pytest.mark.parametrize("status,error,temporary,permanent", [(0, 3, True, False), (3, 4, False, True)])
def test_other_eps_fault_reporting_remains_intact(status, error, temporary, permanent):
  parser = ParsedTeslaState(get_params())
  result = parser.update(3, status=status, error=error)
  assert result.steerFaultTemporary == temporary
  assert result.steerFaultPermanent == permanent
  assert not result.steeringDisengage


def test_brake_signal_survives_level_three_pause():
  result = ParsedTeslaState(get_params()).update(3, brake=2)
  assert result.brakePressed
  assert not result.steeringDisengage


@pytest.mark.parametrize("modern_encoding", [False, True])
@pytest.mark.parametrize("cancel", [False, True])
def test_controller_inhibits_level_three_steering_and_preserves_speed_or_explicit_cancel(modern_encoding, cancel):
  CP = get_params(alpha_long=True, modern_encoding=modern_encoding)
  CP_SP = structs.CarParamsSP(flags=TeslaFlagsSP.COOP_STEERING)
  controller = CarController(DBC[CP.carFingerprint], CP, CP_SP)
  parser = ParsedTeslaState(CP)
  state = parser.update(3)
  state.vEgo = state.vEgoRaw = 10.0
  state.steeringAngleDeg = 12.0
  CS = SimpleNamespace(out=state.as_reader(), hands_on_level=parser.state.hands_on_level)
  CC = structs.CarControl.new_message(enabled=True, latActive=True, longActive=True)
  CC.actuators.steeringAngleDeg = 10.0
  CC.actuators.accel = 0.5
  CC.cruiseControl.cancel = cancel

  actuators, frames = controller.update(CC.as_reader(), structs.CarControlSP(), CS, 10_000_000_000)
  receiver = CANParser(DBC[CP.carFingerprint][Bus.party], [("DAS_steeringControl", 50), ("DAS_control", 25)], CANBUS.party)
  updated = receiver.update([(10_000_000_000, frames)])
  assert {0x488, 0x2B9} <= updated
  assert receiver.vl["DAS_steeringControl"]["DAS_steeringControlType"] == 0
  assert actuators.steeringAngleDeg == pytest.approx(state.steeringAngleDeg)
  assert receiver.vl["DAS_control"]["DAS_accState"] == (13 if cancel else 4)
  assert receiver.vl["DAS_control"]["DAS_accelMin"] == pytest.approx(0.5, abs=0.04)
