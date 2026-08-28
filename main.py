import os
import asyncio
import copy
import logging
import time

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
        self._acpi_call_started_at = None
        self._acpi_call_progress = {
            'percent': 0,
            'stage': 'Idle',
            'detail': None,
        }
        self._fan_apply_status = 'idle'
        self._fan_apply_error = None
        self._fan_applied_at = None

        settings.remove_transient_status()
        saved = settings.get_settings()
        saved_charge_limit = saved.get("chargeLimitPercent")
        if type(saved_charge_limit) is not int:
            saved_charge_limit = (
                battery_charge.FIXED_LIMIT_PERCENT
                if saved.get("chargeLimitEnabled", False)
                else battery_charge.DEFAULT_LIMIT_PERCENT
            )
        if saved_charge_limit < battery_charge.DEFAULT_LIMIT_PERCENT:
            result = self._set_charge_limit_hardware(saved_charge_limit)
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
        # Capability and live hardware fields are response-only. Mutating the
        # SettingsManager-owned dictionary here causes those transient values
        # to be persisted the next time any real user setting is saved.
        results = copy.deepcopy(settings.get_settings())

        try:
            results['pluginVersionNum'] = f'{decky.DECKY_PLUGIN_VERSION}'

            results['supportsCustomFanCurves'] = self._fan_backend_available()
        except Exception as e:
            decky.logger.error(e)

        charge_status = self._get_charge_limit_status()
        results['supportsChargeLimit'] = charge_status.supported
        results['chargeLimitEnabled'] = bool(charge_status.enabled)
        results['chargeLimitPercent'] = charge_status.limit
        results['chargeLimitConfigurable'] = charge_status.configurable
        results['chargeLimitMinPercent'] = charge_status.minimum
        results['chargeLimitMaxPercent'] = charge_status.maximum
        results['chargeLimitBackend'] = charge_status.backend
        results['chargeLimitError'] = charge_status.error

        try:
            results['acpiCallDkmsEnabled'] = self._acpi_call_dkms_enabled()
            results['acpiCallDkmsBusy'] = getattr(self, '_acpi_call_busy', False)
            results['acpiCallDkmsInstalled'] = fan_capability.dkms_installed_for_running_kernel()
            progress = self._get_acpi_call_progress_status()
            results['acpiCallDkmsProgress'] = progress['progress']
            results['acpiCallDkmsStage'] = progress['stage']
            results['acpiCallDkmsDetail'] = progress['detail']
            results['acpiCallDkmsElapsedSeconds'] = progress['elapsedSeconds']
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

    def _set_charge_limit_hardware(self, limit):
        legacy_get = self._legacy_charge_getter()
        legacy_set = legion_space.set_charge_limit if legacy_get else None
        return battery_charge.set_charge_limit(
            limit,
            legacy_get=legacy_get,
            legacy_set=legacy_set,
        )

    def _set_acpi_call_progress(self, update):
        """Receive progress from the worker thread using one atomic assignment."""
        previous = getattr(self, '_acpi_call_progress', {}) or {}
        percent = update.get('percent', previous.get('percent', 0))
        self._acpi_call_progress = {
            'percent': max(0, min(100, int(percent))),
            'stage': update.get('stage') or previous.get('stage') or 'Working',
            'detail': update.get('detail'),
        }

    def _get_acpi_call_progress_status(self):
        progress = getattr(self, '_acpi_call_progress', {}) or {}
        started_at = getattr(self, '_acpi_call_started_at', None)
        elapsed = (
            max(0, int(time.monotonic() - started_at))
            if started_at is not None
            else 0
        )
        return {
            'progress': max(0, min(100, int(progress.get('percent', 0)))),
            'stage': progress.get('stage') or 'Idle',
            'detail': progress.get('detail'),
            'elapsedSeconds': elapsed,
        }

    async def get_acpi_call_dkms_status(self):
        busy = getattr(self, '_acpi_call_busy', False)
        # Avoid repeatedly invoking dkms/modprobe while a build is actively
        # using those facilities. The final response performs a fresh check.
        if busy:
            enabled = fan_capability.DEFAULT_ACPI_CALL_PATH.is_file()
            installed = getattr(self, '_acpi_call_was_installed', False)
        else:
            enabled = self._acpi_call_dkms_enabled()
            installed = fan_capability.dkms_installed_for_running_kernel()
        return {
            'enabled': enabled,
            'installed': installed,
            'managed': bool(
                AcpiEnabler is not None and AcpiEnabler.ACPI_CALL_CONF_PATH.exists()
            ),
            'busy': busy,
            **self._get_acpi_call_progress_status(),
        }

    async def set_acpi_call_dkms_enabled(self, enabled: bool):
        if AcpiEnabler is None:
            decky.logger.error('set_acpi_call_dkms_enabled called but AcpiEnabler failed to import')
            return {'success': False, 'error': 'AcpiEnabler is unavailable on this system'}

        if getattr(self, '_acpi_call_busy', False):
            return {'success': False, 'error': 'An acpi_call dkms operation is already in progress'}

        self._acpi_call_was_installed = fan_capability.dkms_installed_for_running_kernel()
        self._acpi_call_busy = True
        self._acpi_call_started_at = time.monotonic()
        self._set_acpi_call_progress({
            'percent': 0,
            'stage': 'Starting',
            'detail': 'Launching the fan-support installer',
        })
        try:
            workdir = os.path.join(decky.DECKY_PLUGIN_RUNTIME_DIR, 'acpi-enabler-work')
            enabler = AcpiEnabler(
                workdir=workdir,
                verbose=True,
                progress_callback=self._set_acpi_call_progress,
            )

            loop = asyncio.get_running_loop()
            if enabled:
                await loop.run_in_executor(None, enabler.enable)
            else:
                await loop.run_in_executor(None, enabler.disable)

            self._acpi_call_busy = False
            status = await self.get_acpi_call_dkms_status()
            status['busy'] = False
            if enabled and not status['enabled']:
                return {
                    'success': False,
                    'enabled': False,
                    'error': 'acpi_call installation completed but /proc/acpi/call is unavailable'
                }
            return {'success': True, **status}
        except Exception as e:
            decky.logger.error(f'error while {"enabling" if enabled else "disabling"} acpi_call dkms|{e}')
            self._set_acpi_call_progress({
                'stage': 'Failed',
                'detail': str(e),
            })
            return {
                'success': False,
                'error': str(e),
                **self._get_acpi_call_progress_status(),
            }
        finally:
            self._acpi_call_busy = False
            self._acpi_call_started_at = None

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

    async def set_charge_limit(self, limit):
        try:
            # Keep the v0.1.x boolean RPC shape working for an older frontend
            # during Decky's plugin reload window, while v0.1.2+ sends an exact
            # percentage.
            if isinstance(limit, bool):
                requested_limit = (
                    battery_charge.FIXED_LIMIT_PERCENT
                    if limit
                    else battery_charge.DEFAULT_LIMIT_PERCENT
                )
            elif type(limit) is int:
                requested_limit = limit
            else:
                raise ValueError('charge limit must be an integer percentage')

            result = self._set_charge_limit_hardware(requested_limit)
            if result.success:
                settings.set_setting('chargeLimitEnabled', bool(result.enabled))
                settings.set_setting('chargeLimitPercent', result.limit)
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
