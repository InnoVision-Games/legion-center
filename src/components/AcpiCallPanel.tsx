import {
  ConfirmModal,
  Field,
  PanelSection,
  PanelSectionRow,
  showModal,
  Spinner,
  ToggleField
} from '@decky/ui';
import { FC } from 'react';
import { useAcpiCallDkms } from '../hooks/ui';

const AcpiCallPanel: FC = () => {
  const {
    acpiCallDkmsEnabled,
    acpiCallDkmsBusy,
    acpiCallDkmsError,
    setAcpiCallDkmsEnabled
  } = useAcpiCallDkms();

  const confirmAndSet = (enabled: boolean) => {
    // Defensive: ToggleField is already disabled while busy, but that
    // only takes effect once React re-renders, which isn't quite
    // synchronous with a click -- bail out here too rather than opening a
    // second confirm dialog on top of an operation that's already running.
    if (acpiCallDkmsBusy) {
      return;
    }

    showModal(
      <ConfirmModal
        strTitle={enabled ? 'Enable ACPI Call (DKMS)?' : 'Disable ACPI Call (DKMS)?'}
        strDescription={
          enabled
            ? 'This downloads a matching kernel modules/headers package and builds the ' +
              'acpi_call kernel module via DKMS so it survives SteamOS updates. This can ' +
              'take several minutes and needs an internet connection. Do not put the ' +
              'Steam Deck to sleep or power it off while this is running. The dialog will ' +
              'close immediately -- watch the Status field below for progress.'
            : 'This removes the acpi_call DKMS module and its self-heal configuration from ' +
              'this device. This can take a minute or two. The dialog will close ' +
              'immediately -- watch the Status field below for progress.'
        }
        strOKButtonText={enabled ? 'Enable' : 'Disable'}
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
          setAcpiCallDkmsEnabled(enabled);
        }}
      />
    );
  };

  let statusText = acpiCallDkmsEnabled ? 'Enabled' : 'Disabled';
  let statusColor = acpiCallDkmsEnabled ? '#4CAF50' : '#8B929A';

  if (acpiCallDkmsBusy) {
    statusText = 'Updating...';
    statusColor = '#E0A030';
  } else if (acpiCallDkmsError) {
    statusText = 'Error';
    statusColor = 'red';
  }

  return (
    <PanelSection title="System">
      <PanelSectionRow>
        <ToggleField
          label="Enable ACPI Call (DKMS)"
          description="Builds and registers the acpi_call kernel module (survives OS updates)"
          checked={acpiCallDkmsEnabled}
          disabled={acpiCallDkmsBusy}
          onChange={confirmAndSet}
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <Field label="Status">
          <span style={{ color: statusColor, fontWeight: 600 }}>{statusText}</span>
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
                  {acpiCallDkmsEnabled
                    ? 'Disabling acpi_call...'
                    : 'Installing acpi_call, this can take several minutes...'}
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
