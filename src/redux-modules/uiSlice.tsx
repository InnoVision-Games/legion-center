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
  supportsChargeLimit: boolean;
  chargeLimitBackend?: string;
  chargeLimitBusy: boolean;
  chargeLimitError?: string;
  powerLedEnabled: boolean;
  pluginVersionNum?: string;
  acpiCallDkmsEnabled: boolean;
  acpiCallDkmsInstalled: boolean;
  acpiCallDkmsBusy: boolean;
  acpiCallDkmsError?: string;
};

// Define the initial state using that type
const initialState: UiStateType = {
  initialLoading: true,
  currentGameId: undefined,
  currentDisplayName: undefined,
  pluginVersionNum: '',
  supportsChargeLimit: false,
  chargeLimitBusy: false,
  powerLedEnabled: true,
  acpiCallDkmsEnabled: false,
  acpiCallDkmsInstalled: false,
  acpiCallDkmsBusy: false,
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
    setChargeLimit(state, action: PayloadAction<boolean>) {
      state.chargeLimitEnabled = action.payload;
    },
    syncChargeLimitState(state, action: PayloadAction<boolean>) {
      state.chargeLimitEnabled = action.payload;
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

export const selectAcpiCallDkmsError = (state: RootState) =>
  state.ui?.acpiCallDkmsError;

let chargeLimitRequestSequence = 0;

export const uiSliceMiddleware =
  (store: any) => (next: any) => (action: any) => {
    const { type } = action;
    const previousChargeLimitEnabled = selectChargeLimitEnabled(
      store.getState()
    );

    const result = next(action);

    if (type === uiSlice.actions.setChargeLimit.type) {
      const requestSequence = ++chargeLimitRequestSequence;
      store.dispatch(uiSlice.actions.setChargeLimitBusy(true));
      store.dispatch(uiSlice.actions.setChargeLimitError(undefined));
      setChargeLimit(action.payload)
        .then((response) => {
          if (requestSequence !== chargeLimitRequestSequence) return;
          if (response?.success) {
            store.dispatch(
              uiSlice.actions.syncChargeLimitState(Boolean(response.enabled))
            );
          } else {
            store.dispatch(
              uiSlice.actions.syncChargeLimitState(previousChargeLimitEnabled)
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
            uiSlice.actions.syncChargeLimitState(previousChargeLimitEnabled)
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
