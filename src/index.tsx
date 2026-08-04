import {
  PanelSection,
  PanelSectionRow,
  staticClasses,
  ToggleField
} from '@decky/ui';
import { definePlugin } from '@decky/api';
import { FC, memo } from 'react';

import RemapButtons from './components/controller/RemapButtons';
import PowerLedPanel from './components/PowerLedPanel';
import AcpiCallPanel from './components/AcpiCallPanel';
import { getSettings } from './backend/utils';
import { store } from './redux-modules/store';
import { getInitialLoading } from './redux-modules/uiSlice';
import { setInitialState } from './redux-modules/extraActions';
import { Provider, useSelector } from 'react-redux';
import { currentGameIdListener } from './backend/currentGameIdListener';
import logo from '../assets/Icon.png';
import FanPanel from './components/fan/FanPanel';
import ErrorBoundary from './components/ErrorBoundary';
import OtaUpdates from './components/OtaUpdates';
import { useAcpiCallDkms, useChargeLimitEnabled } from './hooks/ui';

const Content: FC = memo(() => {
  const loading = useSelector(getInitialLoading);
  const { chargeLimitEnabled, setChargeLimit } = useChargeLimitEnabled();
  const { acpiCallDkmsEnabled } = useAcpiCallDkms();
  if (loading) {
    return null;
  }
  return (
    <>
      <PanelSection>
        <PanelSectionRow>
          <ToggleField
            label="Enable Charge Limit (80%)"
            description={
              acpiCallDkmsEnabled
                ? undefined
                : 'Requires ACPI Call (DKMS) to be enabled below'
            }
            checked={chargeLimitEnabled}
            disabled={!acpiCallDkmsEnabled}
            onChange={setChargeLimit}
          />
        </PanelSectionRow>
      </PanelSection>
      <ErrorBoundary title="Lighting Panel">
        <PowerLedPanel />
      </ErrorBoundary>
      <ErrorBoundary title="Fan Panel">
        <FanPanel />
      </ErrorBoundary>
      <ErrorBoundary title="Remap Buttons">
        <RemapButtons />
      </ErrorBoundary>
      <ErrorBoundary title="ACPI Call Panel">
        <AcpiCallPanel />
      </ErrorBoundary>
      <ErrorBoundary>
        <OtaUpdates />
      </ErrorBoundary>
    </>
  );
});

const AppContainer: FC = () => {
  return (
    <Provider store={store}>
      <Content />
    </Provider>
  );
};

export default definePlugin(() => {
  getSettings()
    .then((results) => {
      store.dispatch(setInitialState(results || {}));
    })
    .catch((e) => {
      console.error('Legion Center: failed to load settings', e);
    });

  const clearListener = currentGameIdListener();

  return {
    name: 'Legion Center',
    titleView: <div className={staticClasses.Title}>Legion Center</div>,
    content: <AppContainer />,
    icon: (
      <img
        src={logo}
        style={{
          width: '1rem',
          filter:
            'invert(100%) sepia(0%) saturate(2%) hue-rotate(157deg) brightness(107%) contrast(101%)'
        }}
      />
    ),
    onDismount() {
      clearListener();
    }
  };
});
