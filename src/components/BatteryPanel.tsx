import {
  DropdownItem,
  Field,
  PanelSection,
  PanelSectionRow,
  ToggleField
} from '@decky/ui';

import { useChargeLimit } from '../hooks/ui';

const FIXED_LIMIT_PERCENT = 80;
const DEFAULT_LIMIT_PERCENT = 100;
const LIMIT_STEP = 5;

const percentageOptions = (
  minimum: number,
  maximum: number,
  current: number
) => {
  const values = new Set<number>([current, maximum]);
  const firstStep = Math.ceil(minimum / LIMIT_STEP) * LIMIT_STEP;
  for (let value = firstStep; value <= maximum; value += LIMIT_STEP) {
    values.add(value);
  }

  return Array.from(values)
    .filter((value) => value >= minimum && value <= maximum)
    .sort((a, b) => a - b)
    .map((value) => ({
      data: value,
      label: value === DEFAULT_LIMIT_PERCENT ? 'Off (100%)' : `${value}%`
    }));
};

const BatteryPanel = () => {
  const {
    supportsChargeLimit,
    chargeLimitEnabled,
    chargeLimitPercent,
    chargeLimitConfigurable,
    chargeLimitMinPercent,
    chargeLimitMaxPercent,
    chargeLimitBackend,
    chargeLimitBusy,
    chargeLimitError,
    setChargeLimitPercent
  } = useChargeLimit();

  if (!supportsChargeLimit) {
    return null;
  }

  const backendDescription =
    chargeLimitBackend === 'acpi_call'
      ? 'Uses the Legion Go firmware battery-protection mode'
      : 'Uses the native Linux battery protection interface';

  return (
    <PanelSection title="Battery">
      <PanelSectionRow>
        {chargeLimitConfigurable ? (
          <DropdownItem
            label="Maximum charge"
            description="Charging stops near this level; firmware may round to a supported value"
            rgOptions={percentageOptions(
              chargeLimitMinPercent,
              chargeLimitMaxPercent,
              chargeLimitPercent
            )}
            selectedOption={chargeLimitPercent}
            disabled={chargeLimitBusy}
            onChange={(option) => setChargeLimitPercent(option.data)}
          />
        ) : (
          <ToggleField
            label={`Battery protection (${FIXED_LIMIT_PERCENT}%)`}
            description={backendDescription}
            checked={chargeLimitEnabled}
            disabled={chargeLimitBusy}
            onChange={(enabled) =>
              setChargeLimitPercent(
                enabled ? FIXED_LIMIT_PERCENT : DEFAULT_LIMIT_PERCENT
              )
            }
          />
        )}
      </PanelSectionRow>
      {Boolean(chargeLimitError) && (
        <PanelSectionRow>
          <Field label="Charge limit error">
            <span style={{ color: '#ff6b6b' }}>{chargeLimitError}</span>
          </Field>
        </PanelSectionRow>
      )}
    </PanelSection>
  );
};

export default BatteryPanel;
