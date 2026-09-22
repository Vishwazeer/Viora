"""Viora – HMS package init. Exports the active adapter based on settings."""
from agent.hms.base import HMSAdapter
from config.settings import HMSProvider, get_settings

_settings = get_settings()
_adapter_instance: HMSAdapter | None = None


def get_hms_adapter() -> HMSAdapter:
    global _adapter_instance
    if _adapter_instance is None:
        if _settings.HMS_PROVIDER == HMSProvider.EKA_CARE:
            from agent.hms.eka_adapter import EkaCareAdapter
            _adapter_instance = EkaCareAdapter()
        else:
            from agent.hms.mock_adapter import MockHMSAdapter
            _adapter_instance = MockHMSAdapter()
    return _adapter_instance
