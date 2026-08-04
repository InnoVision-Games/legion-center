import { PanelSection, PanelSectionRow, ToggleField } from '@decky/ui';
import { FC } from 'react';
import { usePowerLed } from '../hooks/ui';

const PowerLedPanel: FC = () => {
  const { powerLedEnabled, setPowerLed } = usePowerLed();

  return (
    <PanelSection title="Lighting">
      <PanelSectionRow>
        <ToggleField
          label="Enable Power LED"
          checked={powerLedEnabled}
          onChange={setPowerLed}
        />
      </PanelSectionRow>
    </PanelSection>
  );
};

export default PowerLedPanel;
