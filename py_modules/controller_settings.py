import os
from settings import SettingsManager
import fan_capability

settings_directory = os.environ["DECKY_PLUGIN_SETTINGS_DIR"]
settings_path = os.path.join(settings_directory, 'settings.json')
setting_file = SettingsManager(name="settings", settings_directory=settings_directory)
setting_file.read()

TRANSIENT_STATUS_KEYS = (
    'pluginVersionNum',
    'supportsCustomFanCurves',
    'supportsChargeLimit',
    'chargeLimitBackend',
    'chargeLimitConfigurable',
    'chargeLimitMinPercent',
    'chargeLimitMaxPercent',
    'chargeLimitError',
    'acpiCallDkmsEnabled',
    'acpiCallDkmsBusy',
    'acpiCallDkmsInstalled',
)

def deep_merge(origin, destination):
    for k, v in origin.items():
        if isinstance(v, dict):
            n = destination.setdefault(k, {})
            deep_merge(v, n)
        else:
            destination[k] = v

    return destination

def get_settings():
    setting_file.read()
    return setting_file.settings

def remove_transient_status():
    """Remove live capability fields persisted by older plugin builds."""
    settings = get_settings()
    changed = False
    for key in TRANSIENT_STATUS_KEYS:
        if key in settings:
            del settings[key]
            changed = True
    if changed:
        setting_file.settings = settings
        setting_file.commit()
    return changed

def set_setting(name: str, value):
    return setting_file.setSetting(name, value)

def set_all_controller_profiles(controller_profiles):
    settings = get_settings()

    if not settings.get('controller'):
        settings['controller'] = {}
    profiles = settings['controller']
    deep_merge(controller_profiles, profiles)

    setting_file.settings['controller'] = profiles
    setting_file.commit()

def set_all_fan_profiles(fan_profiles):
    settings = get_settings()
    if not settings.get('fan'):
        settings['fan'] = {}

    profiles = settings['fan']
    deep_merge(fan_profiles, profiles)
    setting_file.settings['fan'] = profiles
    setting_file.commit()

def merge_settings(new_settings):
    settings = get_settings()

    deep_merge(new_settings, settings)

    setting_file.settings = settings
    setting_file.commit()

def supports_custom_fan_curves():
    try:
        return fan_capability.ensure_acpi_call_available()
    except Exception:
        return False
