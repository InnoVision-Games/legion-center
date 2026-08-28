import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import { setCurrentGameId, setInitialState } from './extraActions';
import { RootState } from './store';
import {
  extractDisplayName,
  setChargeLimit,
  setPowerLed
} from '../backend/utils';
// import type { RootState } from './store';

type UiStateType = {
  initialLoading: boolean;
  currentGameId: undefined | string;
  currentDisplayName: undefined | string;
  chargeLimitEnabled?: boolean;
  chargeLimitPercent: number;
  chargeLimitConfigurable: boolean;
  chargeLimitMinPercent: number;
  chargeLimitMaxPercent: number;
  supportsChargeLimit: boolean;
  chargeLimitBackend?: string;
  chargeLimitBusy: boolean;
  chargeLimitError?: string;
  powerLedEnabled: boolean;
  pluginVersionNum?: string;
  acpiCallDkmsEnabled: boolean;
  acpiCallDkmsInstalled: boolean;
  acpiCallDkmsBusy: boolean;
  acpiCallDkmsProgress: number;
  acpiCallDkmsStage: string;
  acpiCallDkmsDetail?: string;
  acpiCallDkmsElapsedSeconds: number;
  acpiCallDkmsError?: string;
};

// Define the initial state using that type
const initialState: UiStateType = {
  initialLoading: true,
  currentGameId: undefined,
  currentDisplayName: undefined,
  pluginVersionNum: '',
  supportsChargeLimit: false,
  chargeLimitPercent: 100,
  chargeLimitConfigurable: false,
  chargeLimitMinPercent: 80,
  chargeLimitMaxPercent: 100,
  chargeLimitBusy: false,
  powerLedEnabled: true,
  acpiCallDkmsEnabled: false,
  acpiCallDkmsInstalled: false,
  acpiCallDkmsBusy: false,
  acpiCallDkmsProgress: 0,
  acpiCallDkmsStage: 'Idle',
  acpiCallDkmsDetail: undefined,
  acpiCallDkmsElapsedSeconds: 0,
  acpiCallDkmsError: undefined
};

export const uiSlice = createSlice({
  name: 'ui',
  // `createSlice` will infer the state type from the `initialState` argument
  initialState,
  reducers: {
    setInitialLoading: (state, action: PayloadAction<boolean>) => {
      state.initialLoading = action.payload;
    },
    setChargeLimitPercent(state, action: PayloadAction<number>) {
      state.chargeLimitPercent = action.payload;
      state.chargeLimitEnabled = action.payload < 100;
    },
    syncChargeLimitState(
      state,
      action: PayloadAction<{ enabled: boolean; limit: number }>
    ) {
      state.chargeLimitEnabled = action.payload.enabled;
      state.chargeLimitPercent = action.payload.limit;
    },
    setChargeLimitBusy(state, action: PayloadAction<boolean>) {
      state.chargeLimitBusy = action.payload;
    },
    setChargeLimitError(state, action: PayloadAction<string | undefined>) {
      state.chargeLimitError = action.payload;
    },
    setPowerLedEnabled(state, action: PayloadAction<boolean>) {
      state.powerLedEnabled = action.payload;
    },
    setAcpiCallDkmsEnabled(state, action: PayloadAction<boolean>) {
      state.acpiCallDkmsEnabled = action.payload;
    },
    setAcpiCallDkmsInstalled(state, action: PayloadAction<boolean>) {
      state.acpiCallDkmsInstalled = action.payload;
    },
    setAcpiCallDkmsBusy(state, action: PayloadAction<boolean>) {
      state.acpiCallDkmsBusy = action.payload;
    },
    setAcpiCallDkmsProgress(
      state,
      action: PayloadAction<{
        progress?: number;
        stage?: string;
        detail?: string;
        elapsedSeconds?: number;
      }>
    ) {
      if (typeof action.payload.progress === 'number') {
        state.acpiCallDkmsProgress = action.payload.progress;
      }
      if (typeof action.payload.stage === 'string') {
        state.acpiCallDkmsStage = action.payload.stage;
      }
      state.acpiCallDkmsDetail = action.payload.detail;
      if (typeof action.payload.elapsedSeconds === 'number') {
        state.acpiCallDkmsElapsedSeconds = action.payload.elapsedSeconds;
      }
    },
    setAcpiCallDkmsError(state, action: PayloadAction<string | undefined>) {
      state.acpiCallDkmsError = action.payload;
    }
  },
  extraReducers: (builder) => {
    builder.addCase(setInitialState, (state, action) => {
      if (action) state.initialLoading = false;
      if (action.payload?.pluginVersionNum) {
        state.pluginVersionNum = `${action.payload.pluginVersionNum}`;
      }
      if (typeof action.payload?.chargeLimitEnabled === 'boolean') {
        state.chargeLimitEnabled = Boolean(action.payload?.chargeLimitEnabled);
      }
      if (typeof action.payload?.chargeLimitPercent === 'number') {
        state.chargeLimitPercent = action.payload.chargeLimitPercent;
      } else if (state.chargeLimitEnabled) {
        // Backward compatibility for a v0.1.x settings file.
        state.chargeLimitPercent = 80;
      }
      state.chargeLimitConfigurable = Boolean(
        action.payload?.chargeLimitConfigurable
      );
      if (typeof action.payload?.chargeLimitMinPercent === 'number') {
        state.chargeLimitMinPercent = action.payload.chargeLimitMinPercent;
      }
      if (typeof action.payload?.chargeLimitMaxPercent === 'number') {
        state.chargeLimitMaxPercent = action.payload.chargeLimitMaxPercent;
      }
      state.supportsChargeLimit = Boolean(action.payload?.supportsChargeLimit);
      state.chargeLimitBackend = action.payload?.chargeLimitBackend;
      state.chargeLimitError = action.payload?.chargeLimitError;
      if (typeof action.payload?.powerLedEnabled === 'boolean') {
        state.powerLedEnabled = action.payload.powerLedEnabled;
      }
      if (typeof action.payload?.acpiCallDkmsEnabled === 'boolean') {
        state.acpiCallDkmsEnabled = action.payload.acpiCallDkmsEnabled;
      }
      if (typeof action.payload?.acpiCallDkmsInstalled === 'boolean') {
        state.acpiCallDkmsInstalled = action.payload.acpiCallDkmsInstalled;
      }
      if (typeof action.payload?.acpiCallDkmsBusy === 'boolean') {
        state.acpiCallDkmsBusy = action.payload.acpiCallDkmsBusy;
      }
      if (typeof action.payload?.acpiCallDkmsProgress === 'number') {
        state.acpiCallDkmsProgress = action.payload.acpiCallDkmsProgress;
      }
      if (typeof action.payload?.acpiCallDkmsStage === 'string') {
        state.acpiCallDkmsStage = action.payload.acpiCallDkmsStage;
      }
      state.acpiCallDkmsDetail = action.payload?.acpiCallDkmsDetail;
      if (typeof action.payload?.acpiCallDkmsElapsedSeconds === 'number') {
        state.acpiCallDkmsElapsedSeconds =
          action.payload.acpiCallDkmsElapsedSeconds;
      }
    });
    builder.addCase(setCurrentGameId, (state, action) => {
      if (action?.payload) {
        state.currentGameId = action.payload;
        state.currentDisplayName = extractDisplayName();
      }
    });
  }
});

export const getPluginVersionNumSelector = (state: RootState) =>
  state.ui.pluginVersionNum;

export const getInitialLoading = (state: RootState) => state.ui.initialLoading;

export const selectCurrentGameId = (state: RootState) =>
  state.ui?.currentGameId || 'default';

export const selectCurrentGameDisplayName = (state: RootState) =>
  state.ui?.currentDisplayName || 'default';

export const selectChargeLimitEnabled = (state: RootState) =>
  Boolean(state.ui?.chargeLimitEnabled);

export const selectChargeLimitPercent = (state: RootState) =>
  state.ui?.chargeLimitPercent ?? 100;

export const selectChargeLimitConfigurable = (state: RootState) =>
  Boolean(state.ui?.chargeLimitConfigurable);

export const selectChargeLimitMinPercent = (state: RootState) =>
  state.ui?.chargeLimitMinPercent ?? 80;

export const selectChargeLimitMaxPercent = (state: RootState) =>
  state.ui?.chargeLimitMaxPercent ?? 100;

export const selectSupportsChargeLimit = (state: RootState) =>
  Boolean(state.ui?.supportsChargeLimit);

export const selectChargeLimitBackend = (state: RootState) =>
  state.ui?.chargeLimitBackend;

export const selectChargeLimitBusy = (state: RootState) =>
  Boolean(state.ui?.chargeLimitBusy);

export const selectChargeLimitError = (state: RootState) =>
  state.ui?.chargeLimitError;

export const selectPowerLedEnabled = (state: RootState) =>
  Boolean(state.ui?.powerLedEnabled);

export const selectAcpiCallDkmsEnabled = (state: RootState) =>
  Boolean(state.ui?.acpiCallDkmsEnabled);

export const selectAcpiCallDkmsInstalled = (state: RootState) =>
  Boolean(state.ui?.acpiCallDkmsInstalled);

export const selectAcpiCallDkmsBusy = (state: RootState) =>
  Boolean(state.ui?.acpiCallDkmsBusy);

export const selectAcpiCallDkmsProgress = (state: RootState) =>
  state.ui?.acpiCallDkmsProgress ?? 0;

export const selectAcpiCallDkmsStage = (state: RootState) =>
  state.ui?.acpiCallDkmsStage ?? 'Idle';

export const selectAcpiCallDkmsDetail = (state: RootState) =>
  state.ui?.acpiCallDkmsDetail;

export const selectAcpiCallDkmsElapsedSeconds = (state: RootState) =>
  state.ui?.acpiCallDkmsElapsedSeconds ?? 0;

export const selectAcpiCallDkmsError = (state: RootState) =>
  state.ui?.acpiCallDkmsError;

let chargeLimitRequestSequence = 0;

export const uiSliceMiddleware =
  (store: any) => (next: any) => (action: any) => {
    const { type } = action;
    const previousChargeLimitEnabled = selectChargeLimitEnabled(
      store.getState()
    );
    const previousChargeLimitPercent = selectChargeLimitPercent(
      store.getState()
    );

    const result = next(action);

    if (type === uiSlice.actions.setChargeLimitPercent.type) {
      const requestSequence = ++chargeLimitRequestSequence;
      store.dispatch(uiSlice.actions.setChargeLimitBusy(true));
      store.dispatch(uiSlice.actions.setChargeLimitError(undefined));
      setChargeLimit(action.payload)
        .then((response) => {
          if (requestSequence !== chargeLimitRequestSequence) return;
          if (response?.success) {
            store.dispatch(
              uiSlice.actions.syncChargeLimitState({
                enabled: Boolean(response.enabled),
                limit:
                  typeof response.limit === 'number'
                    ? response.limit
                    : action.payload
              })
            );
          } else {
            store.dispatch(
              uiSlice.actions.syncChargeLimitState({
                enabled: previousChargeLimitEnabled,
                limit: previousChargeLimitPercent
              })
            );
            store.dispatch(
              uiSlice.actions.setChargeLimitError(
                response?.error || 'Failed to update the charge limit'
              )
            );
          }
        })
        .catch((error) => {
          if (requestSequence !== chargeLimitRequestSequence) return;
          store.dispatch(
            uiSlice.actions.syncChargeLimitState({
              enabled: previousChargeLimitEnabled,
              limit: previousChargeLimitPercent
            })
          );
          store.dispatch(
            uiSlice.actions.setChargeLimitError(
              error instanceof Error
                ? error.message
                : 'Failed to update the charge limit'
            )
          );
        })
        .finally(() => {
          if (requestSequence === chargeLimitRequestSequence) {
            store.dispatch(uiSlice.actions.setChargeLimitBusy(false));
          }
        });
    }
    if (type === uiSlice.actions.setPowerLedEnabled.type) {
      setPowerLed(action.payload);
    }

    return result;
  };
