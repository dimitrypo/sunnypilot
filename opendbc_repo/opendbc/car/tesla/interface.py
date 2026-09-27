from opendbc.car import Bus, get_safety_config, structs
from opendbc.car.carlog import carlog
from opendbc.car.interfaces import CarInterfaceBase
from opendbc.car.tesla.carcontroller import CarController
from opendbc.car.tesla.carstate import CarState
from opendbc.car.tesla.values import TeslaSafetyFlags, TeslaFlags, CANBUS, CAR, DBC, FSD_14_FW, Ecu
from opendbc.car.tesla.radar_interface import RadarInterface, RADAR_START_ADDR

from opendbc.sunnypilot.car.tesla.values import TeslaFlagsSP, TeslaSafetyFlagsSP


class CarInterface(CarInterfaceBase):
  CarState = CarState
  CarController = CarController
  RadarInterface = RadarInterface

  @staticmethod
  def _get_params(ret: structs.CarParams, candidate, fingerprint, car_fw, alpha_long, is_release, docs) -> structs.CarParams:
    ret.brand = "tesla"

    ret.safetyConfigs = [get_safety_config(structs.CarParams.SafetyModel.tesla)]

    ret.steerLimitTimer = 0.4
    ret.steerActuatorDelay = 0.1
    ret.steerAtStandstill = True

    ret.steerControlType = structs.CarParams.SteerControlType.angle

    # Model X and HW 2.5 vehicles are missing DAS_settings
    if 0x293 not in fingerprint[CANBUS.autopilot_party]:
      ret.flags |= TeslaFlags.MISSING_DAS_SETTINGS.value

    # Radar support is intended to work for:
    # - Tesla Model 3 vehicles built approximately mid-2017 through early-2021
    # - Tesla Model Y vehicles built approximately mid-2020 through early-2021
    # - Vehicles equipped with the Continental ARS4-B radar (used on HW2 / HW2.5 / early HW3)
    # - Radar CAN lines must be tapped and connected to CAN bus 1 (normally not used for tesla vehicles)
    ret.radarUnavailable = RADAR_START_ADDR not in fingerprint[1] or Bus.radar not in DBC[candidate]

    ret.alphaLongitudinalAvailable = True
    if alpha_long:
      ret.openpilotLongitudinalControl = True
      ret.safetyConfigs[0].safetyParam |= TeslaSafetyFlags.LONG_CONTROL.value

      ret.vEgoStopping = 0.1
      ret.vEgoStarting = 0.1
      ret.stoppingDecelRate = 0.3

    eps_encoding_match = any(fw.ecu == Ecu.eps and fw.fwVersion in FSD_14_FW.get(candidate, []) for fw in car_fw)
    # Personal Model 3 is always cooperative. On newer firmware, the old 2-bit
    # value 1 encodes 3-bit LANE_KEEP_ASSIST (010). Reuse the paired legacy FSD_14
    # encoding flags; this does not assert that the car has FSD 14 installed.
    # Fresh CAN evidence also works when the cached EPS version is old/missing.
    # These exact buses/messages are upstream's 3-bit detector (opendbc PR #3802).
    redundant_braking_seen = 0x489 in fingerprint[CANBUS.autopilot_party]
    autonomy_health_seen = 0x054 in fingerprint[CANBUS.party]
    model_3_3_bit_can = candidate == CAR.TESLA_MODEL_3 and (redundant_braking_seen or autonomy_health_seen)
    if eps_encoding_match or model_3_3_bit_can:
      ret.flags |= TeslaFlags.FSD_14.value
      ret.safetyConfigs[0].safetyParam |= TeslaSafetyFlags.FSD_14.value

    if candidate == CAR.TESLA_MODEL_3:
      # This policy requires the matching Panda firmware. Keep the car-side and
      # safety flags paired; other Tesla platforms retain full force override.
      ret.flags |= TeslaFlags.STEERING_PAUSE.value
      ret.safetyConfigs[0].safetyParam |= TeslaSafetyFlags.STEERING_PAUSE.value
      carlog.info({
        "event": "tesla_steering_protocol",
        "fingerprint": candidate,
        "eps_encoding_match": eps_encoding_match,
        "redundant_braking_on_bus_2": redundant_braking_seen,
        "autonomy_health_on_bus_0": autonomy_health_seen,
        "legacy_fsd14_encoding_flag": bool(ret.flags & TeslaFlags.FSD_14.value),
        "steering_pause_policy": bool(ret.flags & TeslaFlags.STEERING_PAUSE.value),
      })

    ret.dashcamOnly = candidate in (CAR.TESLA_MODEL_X,)  # dashcam only, pending find invalidLkasSetting signal

    return ret

  @staticmethod
  def _get_params_sp(stock_cp: structs.CarParams, ret: structs.CarParamsSP, candidate, fingerprint: dict[int, dict[int, int]],
                     car_fw: list[structs.CarParams.CarFw], alpha_long: bool, is_release_sp: bool, docs: bool) -> structs.CarParamsSP:

    stock_cp.enableBsm = True

    if candidate == CAR.TESLA_MODEL_X:
      stock_cp.dashcamOnly = False

    if 0x3DF in fingerprint[1]:
      ret.flags |= TeslaFlagsSP.HAS_VEHICLE_BUS.value
      ret.safetyParam |= TeslaSafetyFlagsSP.HAS_VEHICLE_BUS

    return ret
