def tesla_steering_pause_status(status: str, fingerprint: str | None, CS, CC, messages_valid: bool) -> str:
  """Show the personal Model 3's actual steering availability during a soft pause."""
  if (fingerprint == "TESLA_MODEL_3" and messages_valid and status == "engaged" and
      CS.canValid and not (CS.steerFaultTemporary or CS.steerFaultPermanent or CS.steeringDisengage) and
      CC.enabled and not CC.latActive):
    # CC.longActive can be false while Tesla's stock ACC is controlling speed.
    return "long_only"
  return status
