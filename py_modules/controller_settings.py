import os
import subprocess
from settings import SettingsManager

settings_directory = os.environ["DECKY_PLUGIN_SETTINGS_DIR"]
settings_path = os.path.join(settings_directory, 'settings.json')
setting_file = SettingsManager(name="settings", settings_directory=settings_directory)
setting_file.read()

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

def modprobe_acpi_call():
    # Decky's backend process sets LD_LIBRARY_PATH to point at its own
    # bundled libraries, which gets inherited by any child process spawned
    # from inside it. os.system() runs its command through `/bin/sh -c`,
    # and that inherited LD_LIBRARY_PATH makes the system's `sh` binary
    # try to load Decky's bundled (mismatched) libreadline.so instead of
    # the real one -- it fails to even start, with a `symbol lookup
    # error: undefined symbol: rl_trim_arg_from_keyseq` logged every time
    # this function runs (i.e. every time the plugin panel is opened, via
    # get_settings() -> supports_custom_fan_curves()). subprocess.run()
    # below with an explicitly cleared LD_LIBRARY_PATH already does this
    # correctly and its result is what's actually used -- there was never
    # a reason to also shell out via os.system() first.
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = ""
    result = subprocess.run(["modprobe", "acpi_call"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)

    # `modprobe` can print a harmless message to stderr even on success --
    # e.g. re-running it against a module that's already loaded is a
    # normal no-op, but some modprobe/kmod builds still write an
    # informational line to stderr for that case. Treating ANY stderr
    # output as failure meant a routine warning here could make this
    # silently report "acpi_call unsupported", which in turn made
    # save_fan_settings() skip its entire custom-fan-curve/TDP branch --
    # sliders would appear to do nothing even though acpi_call was loaded
    # and working fine (confirmed by Full Fan Speed / Charge Limit, which
    # don't go through this check). The exit code is what actually
    # indicates success or failure here.
    if result.returncode != 0:
        return False
    return True

def supports_custom_fan_curves():
    try:
        if modprobe_acpi_call():
            return True
        return False
    except Exception as e:
        return False
