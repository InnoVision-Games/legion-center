import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import { set, merge, cloneDeep } from 'lodash';
import { setCurrentGameId, setInitialState } from './extraActions';
import { extractCurrentGameId } from '../backend/utils';
import { call } from '@decky/api';
import { RootState } from './store';

// Temperature 10°C: Fan Speed 5%
// Temperature 20°C: Fan Speed 5%
// Temperature 30°C: Fan Speed 5%
// Temperature 40°C: Fan Speed 10%
// Temperature 50°C: Fan Speed 15%
// Temperature 60°C: Fan Speed 35%
// Temperature 70°C: Fan Speed 70%
// Temperature 80°C: Fan Speed 80%
// Temperature 90°C: Fan Speed 95%
// Temperature 100°C: Fan Speed 100%

const DEFAULT_FAN_VALUES: FanProfile = {
  10: 5,
  20: 5,
  30: 5,
  40: 10,
  50: 15,
  60: 35,
  70: 70,
  80: 80,
  90: 95,
  100: 100,
  fullFanSpeedEnabled: false
};

type FanSpeed = number;

type FanCurve = {
  10: FanSpeed;
  20: FanSpeed;
  30: FanSpeed;
  40: FanSpeed;
  50: FanSpeed;
  60: FanSpeed;
  70: FanSpeed;
  80: FanSpeed;
  90: FanSpeed;
  100: FanSpeed;
};

export interface FanProfile extends FanCurve {
  fullFanSpeedEnabled: boolean;
}

export type SelectableFanPresetId = 'quiet' | 'balanced' | 'aggressive';
export type FanPresetId = SelectableFanPresetId | 'custom';

export const FAN_PRESETS: Record<SelectableFanPresetId, FanProfile> = {
  quiet: {
    10: 5,
    20: 5,
    30: 5,
    40: 5,
    50: 10,
    60: 25,
    70: 70,
    80: 80,
    90: 95,
    100: 100,
    fullFanSpeedEnabled: false
  },
  balanced: DEFAULT_FAN_VALUES,
  aggressive: {
    10: 15,
    20: 15,
    30: 20,
    40: 25,
    50: 40,
    60: 60,
    70: 85,
    80: 100,
    90: 115,
    100: 115,
    fullFanSpeedEnabled: false
  }
};

const FAN_TEMPERATURES: (keyof FanCurve)[] = [
  10, 20, 30, 40, 50, 60, 70, 80, 90, 100
];

export type FanProfiles = {
  [gameId: string]: FanProfile;
};

export type FanApplyStatus = 'idle' | 'applying' | 'applied' | 'error';

type FanState = {
  fanProfiles: FanProfiles;
  fanPerGameProfilesEnabled: boolean;
  customFanCurvesEnabled: boolean;
  supportsCustomFanCurves: boolean;
  fanApplyStatus: FanApplyStatus;
  fanApplyError?: string;
  fanAppliedAt?: number;
};

const initialState: FanState = {
  fanProfiles: {},
  fanPerGameProfilesEnabled: false,
  customFanCurvesEnabled: false,
  supportsCustomFanCurves: false,
  fanApplyStatus: 'idle',
  fanApplyError: undefined,
  fanAppliedAt: undefined
};

export const fanSlice = createSlice({
  name: 'fan',
  initialState,
  reducers: {
    setCustomFanCurvesEnabled: (state, action: PayloadAction<boolean>) => {
      const enabled = action.payload;
      state.customFanCurvesEnabled = enabled;
      if (enabled) {
        bootstrapFanProfile(state, extractCurrentGameId());
      }
    },
    setFanPerGameProfilesEnabled: (state, action: PayloadAction<boolean>) => {
      const enabled = action.payload;
      state.fanPerGameProfilesEnabled = enabled;
      if (enabled) {
        bootstrapFanProfile(state, extractCurrentGameId());
      }
    },
    setEnableFullFanSpeedMode: (state, action: PayloadAction<boolean>) => {
      const enabled = action.payload;

      const perGameProfilesEnabled = state.fanPerGameProfilesEnabled;

      if (perGameProfilesEnabled) {
        const currentGameId = extractCurrentGameId();
        bootstrapFanProfile(state, currentGameId);
        state.fanProfiles[currentGameId].fullFanSpeedEnabled = enabled;
      } else {
        bootstrapFanProfile(state, 'default');
        state.fanProfiles.default.fullFanSpeedEnabled = enabled;
      }
    },
    applyFanPreset: (state, action: PayloadAction<SelectableFanPresetId>) => {
      const profileId = state.fanPerGameProfilesEnabled
        ? extractCurrentGameId()
        : 'default';
      bootstrapFanProfile(state, profileId);
      state.fanProfiles[profileId] = cloneDeep(FAN_PRESETS[action.payload]);
    },
    copyDefaultFanProfileToCurrent: (state) => {
      if (!state.fanPerGameProfilesEnabled) return;
      const currentGameId = extractCurrentGameId();
      if (!currentGameId || currentGameId === 'default') return;
      bootstrapFanProfile(state, 'default');
      state.fanProfiles[currentGameId] = cloneDeep(state.fanProfiles.default);
    },
    updateFanCurve: (
      state,
      action: PayloadAction<{
        temp: string;
        fanSpeed: number;
      }>
    ) => {
      const { temp, fanSpeed } = action.payload;
      setStateValue({
        sliceState: state,
        key: temp,
        value: fanSpeed
      });
    },
    updateFanProfiles: (state, action: PayloadAction<FanProfiles>) => {
      merge(state.fanProfiles, action.payload);
    },
    setFanApplyState: (
      state,
      action: PayloadAction<{
        status: FanApplyStatus;
        error?: string;
        appliedAt?: number;
      }>
    ) => {
      state.fanApplyStatus = action.payload.status;
      state.fanApplyError = action.payload.error;
      if (typeof action.payload.appliedAt === 'number') {
        state.fanAppliedAt = action.payload.appliedAt;
      }
    }
  },
  extraReducers: (builder) => {
    builder.addCase(setInitialState, (state, action) => {
      const fanProfiles = action.payload.fan as FanProfiles | undefined;

      const customFanCurvesEnabled = Boolean(
        action.payload.customFanCurvesEnabled
      );
      const fanPerGameProfilesEnabled = Boolean(
        action.payload.fanPerGameProfilesEnabled
      );

      state.supportsCustomFanCurves = Boolean(
        action.payload.supportsCustomFanCurves
      );

      state.customFanCurvesEnabled = customFanCurvesEnabled;
      state.fanProfiles = fanProfiles || {};
      bootstrapFanProfile(state, 'default');
      state.fanPerGameProfilesEnabled = fanPerGameProfilesEnabled;
      if (
        action.payload.fanApplyStatus === 'idle' ||
        action.payload.fanApplyStatus === 'applying' ||
        action.payload.fanApplyStatus === 'applied' ||
        action.payload.fanApplyStatus === 'error'
      ) {
        state.fanApplyStatus = action.payload.fanApplyStatus;
      }
      state.fanApplyError = action.payload.fanApplyError;
      if (typeof action.payload.fanAppliedAt === 'number') {
        state.fanAppliedAt = action.payload.fanAppliedAt;
      }
    });
    builder.addCase(setCurrentGameId, (state, action) => {
      /*
        currentGameIdChanged, check if exists in redux store.
        if not exists, bootstrap it on frontend
      */
      const newGameId = action.payload as string;
      bootstrapFanProfile(state, newGameId);
    });
  }
});

// -------------
// selectors
// -------------

export const selectSupportsCustomFanCurves = (state: RootState) => {
  return Boolean(state.fan.supportsCustomFanCurves);
};

export const selectCustomFanCurvesEnabled = (state: RootState) => {
  return Boolean(state.fan.customFanCurvesEnabled);
};

export const selectFanPerGameProfilesEnabled = (state: RootState) => {
  return Boolean(state.fan.fanPerGameProfilesEnabled);
};

export const selectActiveFanProfile = (state: RootState) => {
  const perGameProfilesEnabled = selectFanPerGameProfilesEnabled(state);

  if (perGameProfilesEnabled) {
    const {
      ui: { currentGameId = 'default' }
    } = state;
    return (
      state.fan.fanProfiles?.[currentGameId] ||
      state.fan.fanProfiles?.default ||
      DEFAULT_FAN_VALUES
    );
  } else {
    return state.fan.fanProfiles?.default || DEFAULT_FAN_VALUES;
  }
};

export const selectActiveFanCurve = (state: RootState) => {
  const profile = selectActiveFanProfile(state);

  const p = cloneDeep(profile) as any;
  delete p.fullFanSpeedEnabled;
  const x = p as FanCurve;

  return x;
};

export const selectEnableFullFanSpeedMode = (state: RootState) => {
  const profile = selectActiveFanProfile(state);
  return Boolean(profile.fullFanSpeedEnabled);
};

export const selectActiveFanPreset = (state: RootState): FanPresetId => {
  const profile = selectActiveFanProfile(state);

  for (const [presetId, preset] of Object.entries(FAN_PRESETS)) {
    if (
      profile.fullFanSpeedEnabled === preset.fullFanSpeedEnabled &&
      FAN_TEMPERATURES.every(
        (temperature) => profile[temperature] === preset[temperature]
      )
    ) {
      return presetId as SelectableFanPresetId;
    }
  }

  return 'custom';
};

export const selectFanApplyStatus = (state: RootState) =>
  state.fan.fanApplyStatus;

export const selectFanApplyError = (state: RootState) =>
  state.fan.fanApplyError;

export const selectFanAppliedAt = (state: RootState) => state.fan.fanAppliedAt;

// -------------
// middleware
// -------------

const mutatingActionTypes = [
  fanSlice.actions.setFanPerGameProfilesEnabled.type,
  fanSlice.actions.updateFanCurve.type,
  fanSlice.actions.updateFanProfiles.type,
  fanSlice.actions.applyFanPreset.type,
  fanSlice.actions.copyDefaultFanProfileToCurrent.type,
  fanSlice.actions.setCustomFanCurvesEnabled.type,
  fanSlice.actions.setEnableFullFanSpeedMode.type
];

const FAN_CURVE_SAVE_DEBOUNCE_MS = 200;
let pendingFanSaveStore: any;
let fanSaveTimer: ReturnType<typeof setTimeout> | undefined;
let fanSaveInFlight = false;

const queueFanSave = (store: any, debounce: boolean) => {
  pendingFanSaveStore = store;
  store.dispatch(fanSlice.actions.setFanApplyState({ status: 'applying' }));

  if (fanSaveTimer) clearTimeout(fanSaveTimer);
  fanSaveTimer = undefined;
  if (debounce) {
    fanSaveTimer = setTimeout(() => {
      fanSaveTimer = undefined;
      void flushFanSaveQueue();
    }, FAN_CURVE_SAVE_DEBOUNCE_MS);
  } else {
    void flushFanSaveQueue();
  }
};

const flushFanSaveQueue = async () => {
  if (fanSaveInFlight || !pendingFanSaveStore) return;
  fanSaveInFlight = true;
  try {
    while (pendingFanSaveStore) {
      const store = pendingFanSaveStore;
      pendingFanSaveStore = undefined;
      const state = store.getState();
      const {
        fan: { fanProfiles, fanPerGameProfilesEnabled, customFanCurvesEnabled },
        ui: { currentGameId: currentId }
      } = state;
      const currentGameId =
        fanPerGameProfilesEnabled && currentId ? currentId : 'default';
      const fanInfo = {
        fanProfiles,
        fanPerGameProfilesEnabled,
        customFanCurvesEnabled
      };

      try {
        const applied = await call<
          [fanInfo: typeof fanInfo, currentGameId: string],
          boolean
        >('save_fan_settings', fanInfo, currentGameId);
        if (!pendingFanSaveStore) {
          store.dispatch(
            fanSlice.actions.setFanApplyState(
              applied
                ? {
                    status: customFanCurvesEnabled ? 'applied' : 'idle',
                    appliedAt: Date.now()
                  }
                : {
                    status: 'error',
                    error: 'The firmware did not accept the active fan profile'
                  }
            )
          );
        }
      } catch (error) {
        if (!pendingFanSaveStore) {
          store.dispatch(
            fanSlice.actions.setFanApplyState({
              status: 'error',
              error:
                error instanceof Error
                  ? error.message
                  : 'Could not apply the active fan profile'
            })
          );
        }
      }
    }
  } finally {
    fanSaveInFlight = false;
    if (pendingFanSaveStore) void flushFanSaveQueue();
  }
};

export const saveFanSettingsMiddleware =
  (store: any) => (next: any) => (action: any) => {
    const { type } = action;

    const result = next(action);

    const state = store.getState();

    const {
      fan: { customFanCurvesEnabled }
    } = state;

    if (type === setCurrentGameId.type && customFanCurvesEnabled) {
      queueFanSave(store, false);
    }

    if (mutatingActionTypes.includes(type)) {
      queueFanSave(store, type === fanSlice.actions.updateFanCurve.type);
    }

    return result;
  };

// -------------
// Slice Util functions
// -------------

function setStateValue({
  sliceState,
  key,
  value
}: {
  sliceState: FanState;
  key: string;
  value: any;
}) {
  if (sliceState.fanPerGameProfilesEnabled) {
    const currentGameId = extractCurrentGameId();
    bootstrapFanProfile(sliceState, currentGameId);
    set(sliceState, `fanProfiles.${currentGameId}.${key}`, value);
  } else {
    bootstrapFanProfile(sliceState, 'default');
    set(sliceState, `fanProfiles.default.${key}`, value);
  }
}

function bootstrapFanProfile(state: FanState, newGameId: string) {
  if (!state.fanProfiles) {
    state.fanProfiles = {};
  }
  if (
    // only initialize profile if perGameProfiles are enabled
    (!state.fanProfiles[newGameId] && state.fanPerGameProfilesEnabled) ||
    // always initialize default
    newGameId === 'default'
  ) {
    const defaultProfile = state.fanProfiles?.default;
    const newFanProfile = cloneDeep(defaultProfile || DEFAULT_FAN_VALUES);

    state.fanProfiles[newGameId] = newFanProfile;
  }
}
