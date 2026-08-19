import {
  ButtonItem,
  ConfirmModal,
  Field,
  PanelSection,
  PanelSectionRow,
  showModal,
  Spinner
} from '@decky/ui';
import { FC } from 'react';
import { useAcpiCallDkms } from '../hooks/ui';

const AcpiCallPanel: FC = () => {
  const {
    acpiCallDkmsEnabled,
    acpiCallDkmsInstalled,
    acpiCallDkmsBusy,
    acpiCallDkmsError,
    setAcpiCallDkmsEnabled
  } = useAcpiCallDkms();

  const confirmInstallOrRepair = () => {
    // Defensive: the button is already disabled while busy, but that
    // only takes effect once React re-renders, which isn't quite
    // synchronous with a click -- bail out here too rather than opening a
    // second confirm dialog on top of an operation that's already running.
    if (acpiCallDkmsBusy) {
      return;
    }

    showModal(
      <ConfirmModal
        strTitle="Install or repair fan support?"
        strDescription={
          'Legion Center will download the matching SteamOS kernel headers, build ' +
          'acpi_call with DKMS, and verify the running interface. This can take ' +
          'several minutes and needs an internet connection. Keep the device awake ' +
          'until the status below changes. After a SteamOS kernel update, return here ' +
          'and run Repair again. Desktop Mode is not required.'
        }
        strOKButtonText={acpiCallDkmsEnabled ? 'Repair' : 'Install'}
        onOK={() => {
          // Deliberately NOT returning the promise from
          // setAcpiCallDkmsEnabled() here. This call can run for several
          // minutes, and ConfirmModal awaits whatever onOK returns before
          // dismissing itself -- returning the promise directly left the
          // dialog sitting open with no feedback for the entire
          // operation, which is exactly what made users think their
          // click didn't register and click Enable again. Firing it
          // without awaiting lets the dialog close immediately; the
          // panel underneath already shows a spinner + Status field for
          // the actual progress.
          setAcpiCallDkmsEnabled(true);
        }}
      />
    );
  };

  let statusText = acpiCallDkmsEnabled
    ? 'Ready'
    : acpiCallDkmsInstalled
      ? 'Repair needed'
      : 'Not installed';
  let statusColor = acpiCallDkmsEnabled ? '#4CAF50' : '#8B929A';

  if (acpiCallDkmsBusy) {
    statusText = 'Updating…';
    statusColor = '#E0A030';
  } else if (acpiCallDkmsError) {
    statusText = 'Error';
    statusColor = 'red';
  }

  return (
    <PanelSection title="System">
      <PanelSectionRow>
        <ButtonItem
          label={
            acpiCallDkmsEnabled ? 'Repair Fan Support' : 'Install Fan Support'
          }
          description={
            acpiCallDkmsEnabled
              ? 'Rechecks the module for the current SteamOS kernel'
              : 'Installs everything fan curves need without Desktop Mode'
          }
          disabled={acpiCallDkmsBusy}
          onClick={confirmInstallOrRepair}
        >
          {acpiCallDkmsEnabled ? 'Repair' : 'Install'}
        </ButtonItem>
      </PanelSectionRow>
      <PanelSectionRow>
        <Field label="Status">
          <span style={{ color: statusColor, fontWeight: 600 }}>
            {statusText}
          </span>
        </Field>
      </PanelSectionRow>
      {acpiCallDkmsBusy && (
        <PanelSectionRow>
          <Field
            label={
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}
              >
                <Spinner style={{ width: '16px', height: '16px' }} />
                <span>
                  Installing fan support, this can take several minutes…
                </span>
              </div>
            }
          />
        </PanelSectionRow>
      )}
      {!acpiCallDkmsBusy && Boolean(acpiCallDkmsError) && (
        <PanelSectionRow>
          <Field label="Error">
            <span style={{ color: 'red' }}>{acpiCallDkmsError}</span>
          </Field>
        </PanelSectionRow>
      )}
    </PanelSection>
  );
};

export default AcpiCallPanel;
