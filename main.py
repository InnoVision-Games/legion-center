import os
import asyncio
import logging

# The decky plugin module is located at decky-loader/plugin
# For easy intellisense checkout the decky-loader code repo
# and add the `decky-loader/plugin/imports` path to `python.analysis.extraPaths` in `.vscode/settings.json`

import decky
import battery_charge
import fan_capability
import fan_control
import legion_configurator
import legion_space
import controller_enums
import controllers
import file_timeout
import plugin_update
import controller_settings as settings

try:
    from acpi_enabler import AcpiEnabler
except Exception as e:
    AcpiEnabler = None
    logging.error(f"failed to import AcpiEnabler|{e}")

try:
    LOG_LOCATION = f"/tmp/legionCenter.log"
    logging.basicConfig(
        level = logging.INFO,
        filename = LOG_LOCATION,
        format="[%(asctime)s | %(filename)s:%(lineno)s:%(funcName)s] %(levelname)s: %(message)s",
        filemode = 'w',
        force = True)
except Exception as e:
    logging.error(f"exception|{e}")

class Plugin:
    # Asyncio-compatible long-running code, executed in a task when the plugin is loaded
    async def _main(self):
        decky.logger.info("Legion Center starting up")
        self._acpi_call_busy = False

        saved = settings.get_settings()
        if saved.get("chargeLimitEnabled", False):
            result = self._set_charge_limit_hardware(True)
            if not result.success:
                decky.logger.error(
                    f"failed to restore saved charge limit: {result.error}"
                )

        if saved.get("customFanCurvesEnabled", False) and self._fan_backend_available():
            profile = (saved.get("fan") or {}).get("default")
            if profile:
                try:
                    if not fan_control.apply_fan_profile(
                        profile,
                        legion_space.set_full_fan_speed,
                        legion_space.set_active_fan_curve,
                    ):
                        decky.logger.error("failed to restore the saved default fan profile")
                except ValueError as error:
                    decky.logger.error(f"saved default fan profile is invalid: {error}")

    async def get_settings(self):
        results = settings.get_settings()

        try:
            results['pluginVersionNum'] = f'{decky.DECKY_PLUGIN_VERSION}'

            results['supportsCustomFanCurves'] = self._fan_backend_available()
        except Exception as e:
            decky.logger.error(e)

        charge_status = self._get_charge_limit_status()
        results['supportsChargeLimit'] = charge_status.supported
        results['chargeLimitEnabled'] = bool(charge_status.enabled)
        results['chargeLimitBackend'] = charge_status.backend
        results['chargeLimitError'] = charge_status.error

        try:
            results['acpiCallDkmsEnabled'] = self._acpi_call_dkms_enabled()
            results['acpiCallDkmsBusy'] = getattr(self, '_acpi_call_busy', False)
            results['acpiCallDkmsInstalled'] = fan_capability.dkms_installed_for_running_kernel()
        except Exception as e:
            decky.logger.error(f'error while checking acpi_call dkms status {e}')

        return results

    def _acpi_call_dkms_enabled(self):
        try:
            return self._fan_backend_available()
        except Exception as e:
            decky.logger.error(f'error while checking acpi_call dkms status {e}')
            return False

    def _fan_backend_available(self):
        return fan_capability.ensure_acpi_call_available()

    def _legacy_charge_getter(self):
        return legion_space.get_charge_limit if self._fan_backend_available() else None

    def _get_charge_limit_status(self):
        return battery_charge.get_charge_limit_status(
            legacy_get=self._legacy_charge_getter()
        )

    def _set_charge_limit_hardware(self, enabled: bool):
        legacy_get = self._legacy_charge_getter()
        legacy_set = legion_space.set_charge_limit if legacy_get else None
        return battery_charge.set_charge_limit(
            enabled,
            legacy_get=legacy_get,
            legacy_set=legacy_set,
        )

    async def get_acpi_call_dkms_status(self):
        return {
            'enabled': self._acpi_call_dkms_enabled(),
            'installed': fan_capability.dkms_installed_for_running_kernel(),
            'managed': bool(
                AcpiEnabler is not None and AcpiEnabler.ACPI_CALL_CONF_PATH.exists()
            ),
            'busy': getattr(self, '_acpi_call_busy', False)
        }

    async def set_acpi_call_dkms_enabled(self, enabled: bool):
        if AcpiEnabler is None:
            decky.logger.error('set_acpi_call_dkms_enabled called but AcpiEnabler failed to import')
            return {'success': False, 'error': 'AcpiEnabler is unavailable on this system'}

        if getattr(self, '_acpi_call_busy', False):
            return {'success': False, 'error': 'An acpi_call dkms operation is already in progress'}

        self._acpi_call_busy = True
        try:
            workdir = os.path.join(decky.DECKY_PLUGIN_RUNTIME_DIR, 'acpi-enabler-work')
            enabler = AcpiEnabler(workdir=workdir, verbose=True)

            loop = asyncio.get_running_loop()
            if enabled:
                await loop.run_in_executor(None, enabler.enable)
            else:
                await loop.run_in_executor(None, enabler.disable)

            status = await self.get_acpi_call_dkms_status()
            if enabled and not status['enabled']:
                return {
                    'success': False,
                    'enabled': False,
                    'error': 'acpi_call installation completed but /proc/acpi/call is unavailable'
                }
            return {'success': True, **status}
        except Exception as e:
            decky.logger.error(f'error while {"enabling" if enabled else "disabling"} acpi_call dkms|{e}')
            return {'success': False, 'error': str(e)}
        finally:
            self._acpi_call_busy = False

    async def save_controller_settings(self, controller, currentGameId):
        controllerProfiles = controller.get('controllerProfiles')
        controllerPerGameProfilesEnabled = controller.get('perGameProfilesEnabled') or False
        controllerRemappingEnabled  = controller.get('controllerRemappingEnabled') or False

        settings.set_setting('controllerPerGameProfilesEnabled', controllerPerGameProfilesEnabled)
        settings.set_setting('controllerRemappingEnabled', controllerRemappingEnabled)
        result = settings.set_all_controller_profiles(controllerProfiles)

        if controllerRemappingEnabled:
            # double-sync just in case the first one doesn't register
            for _ in range(2):
                # sync settings.json to actual controller hardware
                if currentGameId:
                    controllers.sync_controller_profile_settings(currentGameId)
                    # sync touchpad
                    controllers.sync_touchpad(currentGameId)
                    # sync gyros
                    controllers.sync_gyros(currentGameId)
        return result

    async def disable_fan_profiles(self, resetCurve = False):
        settings.set_setting('customFanCurvesEnabled', False)
        return fan_control.restore_firmware_fan_control(
            legion_space.set_full_fan_speed,
            legion_space.set_tdp_mode,
            resetCurve,
        )

    async def save_fan_settings(self, fanInfo, currentGameId):
        fanProfiles = fanInfo.get('fanProfiles', {})
        fanPerGameProfilesEnabled = fanInfo.get('fanPerGameProfilesEnabled', False)
        customFanCurvesEnabled = fanInfo.get('customFanCurvesEnabled', False)

        settings.set_setting('fanPerGameProfilesEnabled', fanPerGameProfilesEnabled)
        settings.set_setting('customFanCurvesEnabled', customFanCurvesEnabled)
        settings.set_all_fan_profiles(fanProfiles)

        try:
            active_fan_profile = fanProfiles.get('default')

            if customFanCurvesEnabled and self._fan_backend_available():
                if fanPerGameProfilesEnabled:
                    fan_profile = fanProfiles.get(currentGameId)
                    if fan_profile:
                        active_fan_profile = fan_profile

                if not active_fan_profile:
                    raise ValueError("No active fan profile is available")
                return fan_control.apply_fan_profile(
                    active_fan_profile,
                    legion_space.set_full_fan_speed,
                    legion_space.set_active_fan_curve,
                )
            elif not customFanCurvesEnabled and self._fan_backend_available():
                return fan_control.restore_firmware_fan_control(
                    legion_space.set_full_fan_speed,
                    legion_space.set_tdp_mode,
                    True,
                )

            return True
        except Exception as e:
            decky.logger.error(f'save_fan_settings error {e}')
            return False

    async def set_power_led(self, enabled):
        # Wrapped in try/except (matching set_charge_limit below) so that
        # an exception anywhere in here -- including inside
        # legion_space.set_power_light() -- gets logged explicitly rather
        # than silently disappearing. This method previously had no
        # try/except at all: if anything raised, nothing about it showed
        # up in journalctl under any legion_space/legion-center-related
        # grep, which is exactly the symptom reported (toggle flips in
        # the UI -- that's local Redux state, no backend round trip
        # needed for it -- but no visible effect and no log line at all
        # from get_power_light()'s unconditional logging on the way in).
        try:
            settings.set_setting('powerLedEnabled', enabled)

            legion_space.set_power_light(enabled)
        except Exception as e:
            decky.logger.error(f'error while setting power led {e}')

    async def set_charge_limit(self, enabled):
        try:
            result = self._set_charge_limit_hardware(bool(enabled))
            if result.success:
                settings.set_setting('chargeLimitEnabled', bool(result.enabled))
            else:
                decky.logger.error(f'error while setting charge limit: {result.error}')
            return result.to_dict()
        except Exception as e:
            decky.logger.error(f'error while setting charge limit {e}')
            return {'success': False, 'error': str(e)}

    async def remap_button(self, button: str, action: str):
        decky.logger.info(f"remap_button {button} {action}")
        controller_code = None
        if button in ['Y3', 'M2', 'M3']:
            controller_code = controller_enums.Controller['RIGHT'].value
        elif button in ['Y1', 'Y2']:
            controller_code = controller_enums.Controller['LEFT'].value
        if not controller_code:
            return
        btn_code = controller_enums.RemappableButtons[button].value
        action_code = controller_enums.RemapActions[action].value
        remap_command = legion_configurator.create_button_remap_command(controller_code, btn_code, action_code)

        legion_configurator.send_command(remap_command)

    async def set_touchpad(self, enable: bool):
        t_toggle = legion_configurator.create_touchpad_command(enable)
        decky.logger.info(t_toggle)

        legion_configurator.send_command(t_toggle)

    async def ota_update(self):
        # trigger ota update
        try:
            with file_timeout.time_limit(15):
                plugin_update.ota_update()
        except Exception as e:
            logging.error(e)

    # Function called first during the unload process, utilize this to handle your plugin being removed
    async def _unload(self):
        decky.logger.info("Legion Center shutting down")

    # Migrations that should be performed before entering `_main()`.
    async def _migration(self):
        decky.logger.info("Migrating")
        # Here's a migration example for logs:
        # - `~/.config/decky-template/template.log` will be migrated to `decky.DECKY_PLUGIN_LOG_DIR/template.log`
        decky.migrate_logs(os.path.join(decky.DECKY_USER_HOME,
                                               ".config", "decky-template", "template.log"))
        # Here's a migration example for settings:
        # - `~/homebrew/settings/template.json` is migrated to `decky.DECKY_PLUGIN_SETTINGS_DIR/template.json`
        # - `~/.config/decky-template/` all files and directories under this root are migrated to `decky.DECKY_PLUGIN_SETTINGS_DIR/`
        decky.migrate_settings(
            os.path.join(decky.DECKY_HOME, "settings", "template.json"),
            os.path.join(decky.DECKY_USER_HOME, ".config", "decky-template"))
        # Here's a migration example for runtime data:
        # - `~/homebrew/template/` all files and directories under this root are migrated to `decky.DECKY_PLUGIN_RUNTIME_DIR/`
        # - `~/.local/share/decky-template/` all files and directories under this root are migrated to `decky.DECKY_PLUGIN_RUNTIME_DIR/`
        decky.migrate_runtime(
            os.path.join(decky.DECKY_HOME, "template"),
            os.path.join(decky.DECKY_USER_HOME, ".local", "share", "decky-template"))

    async def log_info(self, info):
        logging.info(info)
