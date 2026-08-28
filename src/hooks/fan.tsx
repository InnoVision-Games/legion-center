import { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useQuickAccessVisible } from '@decky/api';
import {
  fanSlice,
  selectActiveFanPreset,
  selectCustomFanCurvesEnabled,
  selectEnableFullFanSpeedMode,
  selectFanAppliedAt,
  selectFanApplyError,
  selectFanApplyStatus,
  selectFanPerGameProfilesEnabled,
  selectSupportsCustomFanCurves
} from '../redux-modules/fanSlice';
import type { SelectableFanPresetId } from '../redux-modules/fanSlice';
import { getFanTelemetry } from '../backend/utils';
import type { FanTelemetry } from '../backend/utils';

const FAN_TELEMETRY_POLL_INTERVAL_MS = 2000;

export const useEnableFullFanSpeedMode = () => {
  const result = useSelector(selectEnableFullFanSpeedMode);
  const dispatch = useDispatch();

  const setter = (enabled: boolean) => {
    return dispatch(fanSlice.actions.setEnableFullFanSpeedMode(enabled));
  };
  return {
    enableFullFanSpeedMode: result,
    setEnableFullFanSpeedMode: setter
  };
};

export const useFanPreset = () => {
  const fanPreset = useSelector(selectActiveFanPreset);
  const dispatch = useDispatch();

  const setFanPreset = (preset: SelectableFanPresetId) => {
    return dispatch(fanSlice.actions.applyFanPreset(preset));
  };

  return { fanPreset, setFanPreset };
};

export const useCopyGlobalFanProfile = () => {
  const dispatch = useDispatch();
  const copyGlobalFanProfile = () =>
    dispatch(fanSlice.actions.copyDefaultFanProfileToCurrent());
  return copyGlobalFanProfile;
};

export const useFanApplyState = () => {
  const fanApplyStatus = useSelector(selectFanApplyStatus);
  const fanApplyError = useSelector(selectFanApplyError);
  const fanAppliedAt = useSelector(selectFanAppliedAt);
  return { fanApplyStatus, fanApplyError, fanAppliedAt };
};

export const useFanTelemetry = () => {
  const isQuickAccessVisible = useQuickAccessVisible();
  const [telemetry, setTelemetry] = useState<FanTelemetry>();
  const [telemetryError, setTelemetryError] = useState<string>();

  useEffect(() => {
    if (!isQuickAccessVisible) return;
    let cancelled = false;

    const poll = async () => {
      try {
        const result = await getFanTelemetry();
        if (cancelled) return;
        setTelemetry(result);
        setTelemetryError(result.error);
      } catch (error) {
        if (cancelled) return;
        setTelemetryError(
          error instanceof Error
            ? error.message
            : 'Could not read fan telemetry'
        );
      }
    };

    void poll();
    const interval = setInterval(poll, FAN_TELEMETRY_POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [isQuickAccessVisible]);

  const telemetryAgeSeconds = telemetry
    ? Math.max(0, Math.floor((Date.now() - telemetry.sampledAt) / 1000))
    : undefined;
  return { telemetry, telemetryError, telemetryAgeSeconds };
};

export const useSupportsCustomFanCurves = () => {
  const result = useSelector(selectSupportsCustomFanCurves);
  return result;
};

export const useCustomFanCurvesEnabled = () => {
  const enabled = useSelector(selectCustomFanCurvesEnabled);
  const dispatch = useDispatch();

  const setter = (enabled: boolean) => {
    return dispatch(fanSlice.actions.setCustomFanCurvesEnabled(enabled));
  };

  return { customFanCurvesEnabled: enabled, setCustomFanCurvesEnabled: setter };
};

export const useFanPerGameProfilesEnabled = () => {
  const fanPerGameProfilesEnabled = useSelector(
    selectFanPerGameProfilesEnabled
  );
  const dispatch = useDispatch();

  const setter = (enabled: boolean) => {
    return dispatch(fanSlice.actions.setFanPerGameProfilesEnabled(enabled));
  };

  return { fanPerGameProfilesEnabled, setFanPerGameProfilesEnabled: setter };
};
