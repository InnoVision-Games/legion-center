import { call, fetchNoCors } from '@decky/api';
import { Router } from '@decky/ui';
import { RemapActions, RemappableButtons } from './constants';

export enum ServerAPIMethods {
  REMAP_BUTTON = 'remap_button',
  LOG_INFO = 'log_info',
  GET_SETTINGS = 'get_settings',
  SET_POWER_LED = 'set_power_led',
  SET_CHARGE_LIMIT = 'set_charge_limit',
  GET_ACPI_CALL_DKMS_STATUS = 'get_acpi_call_dkms_status',
  SET_ACPI_CALL_DKMS_ENABLED = 'set_acpi_call_dkms_enabled'
}

export type AcpiCallDkmsStatus = {
  enabled: boolean;
  installed: boolean;
  managed?: boolean;
  busy: boolean;
};

export type AcpiCallDkmsResult = {
  success: boolean;
  enabled?: boolean;
  installed?: boolean;
  error?: string;
};

export type ChargeLimitResult = {
  success: boolean;
  supported?: boolean;
  enabled?: boolean;
  backend?: string;
  error?: string;
};

export const remapButton = async (
  button: RemappableButtons,
  action: RemapActions
) => {
  await call<[button: RemappableButtons, action: RemapActions], void>(
    ServerAPIMethods.REMAP_BUTTON,
    button,
    action
  );
};

export const logInfo = (info: any) => {
  call<[info: string], void>(
    ServerAPIMethods.LOG_INFO,
    JSON.stringify(info)
  ).catch(() => {});
};

export const setPowerLed = async (enabled: boolean) => {
  await call<[enabled: boolean], void>(ServerAPIMethods.SET_POWER_LED, enabled);
};

export const setChargeLimit = async (enabled: boolean) => {
  return await call<[enabled: boolean], ChargeLimitResult>(
    ServerAPIMethods.SET_CHARGE_LIMIT,
    enabled
  );
};

export const getSettings = async () => {
  return await call<[], { [s: string]: any }>(ServerAPIMethods.GET_SETTINGS);
};

export const extractDisplayName = () =>
  `${Router.MainRunningApp?.display_name || 'default'}`;

export const extractCurrentGameId = () =>
  `${Router.MainRunningApp?.appid || 'default'}`;

export const getLatestVersionNum = async () => {
  const response = await fetchNoCors(
    'https://raw.githubusercontent.com/InnoVision-Games/legion-center/main/package.json',
    { method: 'GET' }
  );

  const body = await response.text();
  if (body && typeof body === 'string') {
    try {
      return JSON.parse(body)['version'];
    } catch {
      return '';
    }
  }
  return '';
};

export const otaUpdate = async () => {
  return call<[], void>('ota_update');
};

export const getAcpiCallDkmsStatus = async () => {
  return await call<[], AcpiCallDkmsStatus>(
    ServerAPIMethods.GET_ACPI_CALL_DKMS_STATUS
  );
};

export const setAcpiCallDkmsEnabled = async (enabled: boolean) => {
  return await call<[enabled: boolean], AcpiCallDkmsResult>(
    ServerAPIMethods.SET_ACPI_CALL_DKMS_ENABLED,
    enabled
  );
};
