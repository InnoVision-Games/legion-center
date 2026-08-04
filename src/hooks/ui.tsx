import { useEffect, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  selectAcpiCallDkmsBusy,
  selectAcpiCallDkmsEnabled,
  selectAcpiCallDkmsError,
  selectChargeLimitEnabled,
  selectPowerLedEnabled,
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
const ACPI_CALL_DKMS_POLL_INTERVAL_MS = 5000;

export const useChargeLimitEnabled = () => {
  const chargeLimitEnabled = useSelector(selectChargeLimitEnabled);
  const dispatch = useDispatch();

  const setChargeLimit = (enabled: boolean) => {
    return dispatch(uiSlice.actions.setChargeLimit(enabled));
  };

  return { chargeLimitEnabled, setChargeLimit };
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
// call itself so it can drive a busy/error state the UI can show a spinner
// and error message for while the operation is in flight.
export const useAcpiCallDkms = () => {
  const acpiCallDkmsEnabled = useSelector(selectAcpiCallDkmsEnabled);
  const acpiCallDkmsBusy = useSelector(selectAcpiCallDkmsBusy);
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
    dispatch(uiSlice.actions.setAcpiCallDkmsError(undefined));

    try {
      const result = await callSetAcpiCallDkmsEnabled(enabled);

      if (result?.success) {
        dispatch(
          uiSlice.actions.setAcpiCallDkmsEnabled(
            typeof result.enabled === 'boolean' ? result.enabled : enabled
          )
        );
      } else {
        dispatch(
          uiSlice.actions.setAcpiCallDkmsError(
            result?.error || 'Failed to update acpi_call dkms status'
          )
        );
      }
    } catch (e) {
      dispatch(
        uiSlice.actions.setAcpiCallDkmsError(
          e instanceof Error ? e.message : 'Failed to update acpi_call dkms status'
        )
      );
    } finally {
      dispatch(uiSlice.actions.setAcpiCallDkmsBusy(false));
      inFlightRef.current = false;
    }
  };

  // Background poll of the backend's real status -- see
  // ACPI_CALL_DKMS_POLL_INTERVAL_MS above for why this exists. prevBusyRef
  // tracks the last-seen busy value so we only clear a possibly-stale
  // error message on the specific moment a server-side operation this tab
  // may have lost track of actually finishes, rather than on every idle
  // poll tick (which would otherwise wipe out a freshly-shown, still
  //-relevant error from this tab's own most recent attempt).
  const prevBusyRef = useRef(acpiCallDkmsBusy);

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      // Don't fight with our own in-flight call's state updates -- let
      // its own try/finally be the source of truth while it's running.
      if (inFlightRef.current) {
        return;
      }
      try {
        const status = await getAcpiCallDkmsStatus();
        if (cancelled || !status) {
          return;
        }
        dispatch(uiSlice.actions.setAcpiCallDkmsEnabled(status.enabled));
        dispatch(uiSlice.actions.setAcpiCallDkmsBusy(status.busy));
        if (prevBusyRef.current && !status.busy) {
          dispatch(uiSlice.actions.setAcpiCallDkmsError(undefined));
        }
        prevBusyRef.current = status.busy;
      } catch {
        // Best-effort background sync -- a failed poll just tries again
        // next interval, it shouldn't surface as a user-facing error.
      }
    };

    const interval = setInterval(poll, ACPI_CALL_DKMS_POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [dispatch]);

  return { acpiCallDkmsEnabled, acpiCallDkmsBusy, acpiCallDkmsError, setAcpiCallDkmsEnabled };
};
