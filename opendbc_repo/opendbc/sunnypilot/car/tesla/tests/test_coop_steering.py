import unittest
from types import SimpleNamespace
from unittest.mock import patch

from opendbc.car.tesla.teslacan import TeslaCAN
from opendbc.car.tesla.values import CAR, TeslaFlags
from opendbc.sunnypilot.car.interfaces import _initialize_coop_steering
from opendbc.sunnypilot.car.tesla.coop_steering import CoopSteeringCarController
from opendbc.sunnypilot.car.tesla.values import TeslaFlagsSP


class TestPersonalCooperativeSteering(unittest.TestCase):
  def test_model_3_ignores_saved_toggle(self):
    CP = SimpleNamespace(brand="tesla", carFingerprint=CAR.TESLA_MODEL_3, flags=0)
    for saved in ({}, {"TeslaCoopSteering": "0"}, {"TeslaCoopSteering": "1"}, {"TeslaCoopSteering": None}):
      with self.subTest(saved=saved):
        CP_SP = SimpleNamespace(flags=TeslaFlagsSP.HAS_VEHICLE_BUS.value)
        _initialize_coop_steering(CP, CP_SP, saved)
        self.assertEqual(CP_SP.flags, TeslaFlagsSP.HAS_VEHICLE_BUS.value | TeslaFlagsSP.COOP_STEERING.value)
        self.assertEqual(CoopSteeringCarController.coop_steering_status_update(CP_SP).control_type, 2)

  def test_other_teslas_retain_saved_toggle(self):
    for platform in (CAR.TESLA_MODEL_Y, CAR.TESLA_MODEL_X):
      for enabled in (False, True):
        with self.subTest(platform=platform, enabled=enabled):
          CP = SimpleNamespace(brand="tesla", carFingerprint=platform, flags=0)
          CP_SP = SimpleNamespace(flags=0)
          _initialize_coop_steering(CP, CP_SP, {"TeslaCoopSteering": str(int(enabled))})
          self.assertEqual(bool(CP_SP.flags & TeslaFlagsSP.COOP_STEERING.value), enabled)

  def test_other_brands_unchanged(self):
    CP = SimpleNamespace(brand="mock", carFingerprint="MOCK")
    CP_SP = SimpleNamespace(flags=16)
    _initialize_coop_steering(CP, CP_SP, {"TeslaCoopSteering": "1"})
    self.assertEqual(CP_SP.flags, 16)

  def test_startup_diagnostic_records_effective_mode(self):
    CP = SimpleNamespace(brand="tesla", carFingerprint=CAR.TESLA_MODEL_3, flags=TeslaFlags.FSD_14.value)
    CP_SP = SimpleNamespace(flags=0)
    with patch("opendbc.sunnypilot.car.interfaces.carlog.info") as log:
      _initialize_coop_steering(CP, CP_SP, {"TeslaCoopSteering": "0"})
    log.assert_called_once_with({
      "event": "tesla_cooperative_steering_config",
      "fingerprint": CAR.TESLA_MODEL_3,
      "stored_preference": "0",
      "forced_for_personal_model_3": True,
      "effective_cooperative": True,
      "fsd_14": True,
      "active_can_control_type": 1,
    })

  def test_cooperative_can_type_and_disabled_command(self):
    # Exercise the actual CAN command builder without needing the compiled CAN
    # packer: forced cooperative mode must retain FSD 14 mapping and OFF=0.
    packer = SimpleNamespace(make_can_msg=lambda name, bus, values: values)
    for flags, cooperative_type in ((0, 2), (TeslaFlags.FSD_14.value, 1)):
      with self.subTest(flags=flags):
        tesla_can = TeslaCAN(SimpleNamespace(flags=flags), packer)
        command = tesla_can.create_steering_control(5.0, True, 2)
        self.assertEqual(command["DAS_steeringControlType"], cooperative_type)
        command = tesla_can.create_steering_control(5.0, False, 2)
        self.assertEqual(command["DAS_steeringControlType"], 0)


if __name__ == "__main__":
  unittest.main()
