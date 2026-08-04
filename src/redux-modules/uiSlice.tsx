import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import { setCurrentGameId, setInitialState } from './extraActions';
import { RootState } from './store';
import { extractDisplayName, setChargeLimit, setPowerLed } from '../backend/utils';
// import type { RootState } from './store';

type UiStateType = {
  initialLoading: boolean;
  currentGameId: undefined | string;
  currentDisplayName: undefined | string;
  chargeLimitEnabled?: boolean;
  powerLedEnabled: boolean;
  pluginVersionNum?: string;
  acpiCallDkmsEnabled: boolean;
  acpiCallDkmsBusy: boolean;
  acpiCallDkmsError?: string;
};

// Define the initial state using that type
const initialState: UiStateType = {
  initialLoading: true,
  currentGameId: undefined,
  currentDisplayName: undefined,
  pluginVersionNum: '',
  powerLedEnabled: true,
  acpiCallDkmsEnabled: false,
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
    setPowerLedEnabled(state, action: PayloadAction<boolean>) {
      state.powerLedEnabled = action.payload;
    },
    setAcpiCallDkmsEnabled(state, action: PayloadAction<boolean>) {
      state.acpiCallDkmsEnabled = action.payload;
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
      if (action.payload?.chargeLimitEnabled) {
        state.chargeLimitEnabled = Boolean(action.payload?.chargeLimitEnabled);
      }
      if (typeof action.payload?.powerLedEnabled === 'boolean') {
        state.powerLedEnabled = action.payload.powerLedEnabled;
      }
      if (typeof action.payload?.acpiCallDkmsEnabled === 'boolean') {
        state.acpiCallDkmsEnabled = action.payload.acpiCallDkmsEnabled;
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

export const selectPowerLedEnabled = (state: RootState) =>
  Boolean(state.ui?.powerLedEnabled);

export const selectAcpiCallDkmsEnabled = (state: RootState) =>
  Boolean(state.ui?.acpiCallDkmsEnabled);

export const selectAcpiCallDkmsBusy = (state: RootState) =>
  Boolean(state.ui?.acpiCallDkmsBusy);

export const selectAcpiCallDkmsError = (state: RootState) =>
  state.ui?.acpiCallDkmsError;

export const uiSliceMiddleware =
  (_store: any) => (next: any) => (action: any) => {
    const { type } = action;

    const result = next(action);

    if (type === uiSlice.actions.setChargeLimit.type) {
      setChargeLimit(action.payload);
    }
    if (type === uiSlice.actions.setPowerLedEnabled.type) {
      setPowerLed(action.payload);
    }

    return result;
  };
