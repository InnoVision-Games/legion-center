import { useEffect, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  selectAcpiCallDkmsBusy,
  selectAcpiCallDkmsDetail,
  selectAcpiCallDkmsEnabled,
  selectAcpiCallDkmsElapsedSeconds,
  selectAcpiCallDkmsError,
  selectAcpiCallDkmsInstalled,
  selectAcpiCallDkmsProgress,
  selectAcpiCallDkmsStage,
  selectChargeLimitBackend,
  selectChargeLimitBusy,
  selectChargeLimitConfigurable,
  selectChargeLimitEnabled,
  selectChargeLimitError,
  selectChargeLimitMaxPercent,
  selectChargeLimitMinPercent,
  selectChargeLimitPercent,
  selectPowerLedEnabled,
  selectSupportsChargeLimit,
  uiSlice
} from '../redux-modules/uiSlice';
import {
  getAcpiCallDkmsStatus,
  setAcpiCallDkmsEnabled as callSetAcpiCallDkmsEnabled
} from '../backend/utils';

// How often to poll the backend's real acpi_call dkms status while this
// panel is mounted. This exists to self-heal a specific failure mode: if
// a user manages to fire a second enable/disable call while the first is
// still running (see the in-flight guard below -- this is meant to be a
// backstop, not the primary defense), the backend correctly rejects the
// second call with "already in progress", but that response looks
// exactly like a terminal error to the tab that sent it even though the
// FIRST call just keeps running server-side to completion. Without this
// poll, that tab's local busy/enabled state would stay stuck on the
// stale "already in progress" error indefinitely -- confirmed on real
// hardware to require restarting Decky to clear. Polling the real status
// means the UI catches up to whatever actually happened within one poll
// interval instead of staying wrong until a reload.
const ACPI_CALL_DKMS_IDLE_POLL_INTERVAL_MS = 5000;
const ACPI_CALL_DKMS_BUSY_POLL_INTERVAL_MS = 1000;

export const useChargeLimit = () => {
  const chargeLimitEnabled = useSelector(selectChargeLimitEnabled);
  const chargeLimitPercent = useSelector(selectChargeLimitPercent);
  const chargeLimitConfigurable = useSelector(selectChargeLimitConfigurable);
  const chargeLimitMinPercent = useSelector(selectChargeLimitMinPercent);
  const chargeLimitMaxPercent = useSelector(selectChargeLimitMaxPercent);
  const supportsChargeLimit = useSelector(selectSupportsChargeLimit);
  const chargeLimitBackend = useSelector(selectChargeLimitBackend);
  const chargeLimitBusy = useSelector(selectChargeLimitBusy);
  const chargeLimitError = useSelector(selectChargeLimitError);
  const dispatch = useDispatch();

  const setChargeLimitPercent = (limit: number) => {
    return dispatch(uiSlice.actions.setChargeLimitPercent(limit));
  };

  return {
    chargeLimitEnabled,
    chargeLimitPercent,
    chargeLimitConfigurable,
    chargeLimitMinPercent,
    chargeLimitMaxPercent,
    supportsChargeLimit,
    chargeLimitBackend,
    chargeLimitBusy,
    chargeLimitError,
    setChargeLimitPercent
  };
};

export const usePowerLed = () => {
  const powerLedEnabled = useSelector(selectPowerLedEnabled);
  const dispatch = useDispatch();

  const setPowerLed = (enabled: boolean) => {
    return dispatch(uiSlice.actions.setPowerLedEnabled(enabled));
  };

  return { powerLedEnabled, setPowerLed };
};

// The backend enable/disable acpi_call dkms operation can legitimately take
// several minutes (downloading kernel packages, building/registering a DKMS
// module). Unlike the other toggles above, this one is NOT wired through
// uiSliceMiddleware's fire-and-forget pattern -- the hook awaits the backend
// call itself so it can drive busy/error/progress state while the operation
// is in flight.
export const useAcpiCallDkms = () => {
  const acpiCallDkmsEnabled = useSelector(selectAcpiCallDkmsEnabled);
  const acpiCallDkmsInstalled = useSelector(selectAcpiCallDkmsInstalled);
  const acpiCallDkmsBusy = useSelector(selectAcpiCallDkmsBusy);
  const acpiCallDkmsProgress = useSelector(selectAcpiCallDkmsProgress);
  const acpiCallDkmsStage = useSelector(selectAcpiCallDkmsStage);
  const acpiCallDkmsDetail = useSelector(selectAcpiCallDkmsDetail);
  const acpiCallDkmsElapsedSeconds = useSelector(
    selectAcpiCallDkmsElapsedSeconds
  );
  const acpiCallDkmsError = useSelector(selectAcpiCallDkmsError);
  const dispatch = useDispatch();

  // Redux state updates (and therefore ToggleField's disabled prop) only
  // take effect on the next render, which leaves a brief window where a
  // fast double-click/double-confirm could fire this twice before React
  // catches up. A ref is synchronous and immediate, so it closes that
  // window completely -- this is the PRIMARY defense against a second
  // concurrent call, the backend's own busy check is just a backstop.
  const inFlightRef = useRef(false);

  const setAcpiCallDkmsEnabled = async (enabled: boolean) => {
    if (inFlightRef.current) {
      return;
    }
    inFlightRef.current = true;

    dispatch(uiSlice.actions.setAcpiCallDkmsBusy(true));
    dispatch(
      uiSlice.actions.setAcpiCallDkmsProgress({
        progress: 0,
        stage: 'Starting',
        detail: 'Launching the fan-support installer',
        elapsedSeconds: 0
      })
    );
    dispatch(uiSlice.actions.setAcpiCallDkmsError(undefined));

    try {
      const result = await callSetAcpiCallDkmsEnabled(enabled);

      if (result?.success) {
        dispatch(
          uiSlice.actions.setAcpiCallDkmsEnabled(
            typeof result.enabled === 'boolean' ? result.enabled : enabled
          )
        );
        if (typeof result.installed === 'boolean') {
          dispatch(uiSlice.actions.setAcpiCallDkmsInstalled(result.installed));
        }
        dispatch(
          uiSlice.actions.setAcpiCallDkmsProgress({
            progress: result.progress,
            stage: result.stage,
            detail: result.detail,
            elapsedSeconds: result.elapsedSeconds
          })
        );
      } else {
        dispatch(
          uiSlice.actions.setAcpiCallDkmsProgress({
            progress: result?.progress,
            stage: result?.stage || 'Failed',
            detail: result?.detail,
            elapsedSeconds: result?.elapsedSeconds
          })
        );
        dispatch(
          uiSlice.actions.setAcpiCallDkmsError(
            result?.error || 'Failed to update acpi_call dkms status'
          )
        );
      }
    } catch (e) {
      dispatch(
        uiSlice.actions.setAcpiCallDkmsError(
          e instanceof Error
            ? e.message
            : 'Failed to update acpi_call dkms status'
        )
      );
    } finally {
      dispatch(uiSlice.actions.setAcpiCallDkmsBusy(false));
      inFlightRef.current = false;
    }
  };

  // Background poll of the backend's real status -- see
  // ACPI_CALL_DKMS_IDLE_POLL_INTERVAL_MS above for why this exists. It polls
  // more frequently during an operation so phase and elapsed-time updates feel
  // live. prevBusyRef
  // tracks the last-seen busy value so we only clear a possibly-stale
  // error message on the specific moment a server-side operation this tab
  // may have lost track of actually finishes, rather than on every idle
  // poll tick (which would otherwise wipe out a freshly-shown, still
  //-relevant error from this tab's own most recent attempt).
  const prevBusyRef = useRef(acpiCallDkmsBusy);

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      try {
        const status = await getAcpiCallDkmsStatus();
        if (cancelled || !status) {
          return;
        }
        // A just-started local RPC can briefly win the race against the
        // backend setting its busy flag. Don't let that one stale idle poll
        // hide the progress UI while the request itself is still in flight.
        if (inFlightRef.current && !status.busy) {
          return;
        }
        dispatch(uiSlice.actions.setAcpiCallDkmsEnabled(status.enabled));
        dispatch(uiSlice.actions.setAcpiCallDkmsInstalled(status.installed));
        dispatch(uiSlice.actions.setAcpiCallDkmsBusy(status.busy));
        dispatch(
          uiSlice.actions.setAcpiCallDkmsProgress({
            progress: status.progress,
            stage: status.stage,
            detail: status.detail,
            elapsedSeconds: status.elapsedSeconds
          })
        );
        if (prevBusyRef.current && !status.busy) {
          dispatch(uiSlice.actions.setAcpiCallDkmsError(undefined));
        }
        prevBusyRef.current = status.busy;
      } catch {
        // Best-effort background sync -- a failed poll just tries again
        // next interval, it shouldn't surface as a user-facing error.
      }
    };

    void poll();
    const interval = setInterval(
      poll,
      acpiCallDkmsBusy
        ? ACPI_CALL_DKMS_BUSY_POLL_INTERVAL_MS
        : ACPI_CALL_DKMS_IDLE_POLL_INTERVAL_MS
    );
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [acpiCallDkmsBusy, dispatch]);

  return {
    acpiCallDkmsEnabled,
    acpiCallDkmsInstalled,
    acpiCallDkmsBusy,
    acpiCallDkmsProgress,
    acpiCallDkmsStage,
    acpiCallDkmsDetail,
    acpiCallDkmsElapsedSeconds,
    acpiCallDkmsError,
    setAcpiCallDkmsEnabled
  };
};
