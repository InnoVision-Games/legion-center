import {
  ButtonItem,
  ConfirmModal,
  DropdownItem,
  Focusable,
  PanelSection,
  PanelSectionRow,
  showModal,
  ToggleField
} from '@decky/ui';
import {
  useCopyGlobalFanProfile,
  useCustomFanCurvesEnabled,
  useEnableFullFanSpeedMode,
  useFanPreset,
  useFanPerGameProfilesEnabled
} from '../../hooks/fan';
import type { FanPresetId } from '../../redux-modules/fanSlice';
import { useAcpiCallDkms } from '../../hooks/ui';
import { capitalize } from 'lodash';
import { useSelector } from 'react-redux';
import { useState } from 'react';
import {
  selectCurrentGameDisplayName,
  selectCurrentGameId
} from '../../redux-modules/uiSlice';
import FanCurveSliders from './FanCurveSliders';
import FanProfileTools from './FanProfileTools';
import FanTelemetryRows from './FanTelemetryRows';
import { IoMdArrowDropdown, IoMdArrowDropup } from 'react-icons/io';

const FAN_PRESET_OPTIONS: { data: FanPresetId; label: string }[] = [
  { data: 'quiet', label: 'Quiet' },
  { data: 'balanced', label: 'Balanced' },
  { data: 'aggressive', label: 'Aggressive cooling' },
  { data: 'custom', label: 'Custom' }
];

const useTitle = (fanPerGameProfilesEnabled: boolean) => {
  const currentDisplayName = useSelector(selectCurrentGameDisplayName);

  if (!fanPerGameProfilesEnabled) {
    return 'Fan Control';
  }

  const title = `Fan Control - ${capitalize(currentDisplayName)}`;

  return title;
};

const FanPanel = () => {
  const { acpiCallDkmsEnabled } = useAcpiCallDkms();
  const [showSliders, setShowSliders] = useState(false);

  const { enableFullFanSpeedMode, setEnableFullFanSpeedMode } =
    useEnableFullFanSpeedMode();

  const { customFanCurvesEnabled, setCustomFanCurvesEnabled } =
    useCustomFanCurvesEnabled();
  const { fanPreset, setFanPreset } = useFanPreset();
  const copyGlobalFanProfile = useCopyGlobalFanProfile();
  const { fanPerGameProfilesEnabled, setFanPerGameProfilesEnabled } =
    useFanPerGameProfilesEnabled();
  const title = useTitle(fanPerGameProfilesEnabled);
  const currentGameId = useSelector(selectCurrentGameId);
  const currentDisplayName = useSelector(selectCurrentGameDisplayName);

  const confirmCopyGlobalProfile = () => {
    showModal(
      <ConfirmModal
        strTitle="Replace this game's fan curve?"
        strDescription={`The fan curve for ${capitalize(
          currentDisplayName
        )} will be replaced with your global curve.`}
        strOKButtonText="Copy Global Curve"
        onOK={() => {
          copyGlobalFanProfile();
        }}
      />
    );
  };

  return (
    <>
      <PanelSection title={title}>
        {/* {!acknowledgeWarning && (
          <PanelSectionRow>
            ⚠️ Warning ⚠️ - recently reported bugs indicate that custom fan
            curves sometimes stop working for unknown reasons. Use this feature
            with caution!
          </PanelSectionRow>
        )}
        <PanelSectionRow>
          <ToggleField
            label={'Hide Warning'}
            checked={acknowledgeWarning}
            onChange={setWarning}
          />
        </PanelSectionRow> */}
        <PanelSectionRow>
          <ToggleField
            label={'Enable Custom Fan Curves'}
            description={
              acpiCallDkmsEnabled
                ? undefined
                : 'Install Fan Support in System below'
            }
            checked={customFanCurvesEnabled}
            disabled={!acpiCallDkmsEnabled}
            onChange={setCustomFanCurvesEnabled}
          />
        </PanelSectionRow>
        {customFanCurvesEnabled && (
          <>
            <PanelSectionRow>
              <ToggleField
                label={'Enable Per Game Fan Curves'}
                checked={fanPerGameProfilesEnabled}
                onChange={setFanPerGameProfilesEnabled}
              />
            </PanelSectionRow>
            {fanPerGameProfilesEnabled && currentGameId !== 'default' && (
              <PanelSectionRow>
                <ButtonItem
                  label="Copy Global Curve to This Game"
                  description={`Replace ${capitalize(
                    currentDisplayName
                  )}'s curve with the global profile`}
                  onClick={confirmCopyGlobalProfile}
                >
                  Copy
                </ButtonItem>
              </PanelSectionRow>
            )}
            <PanelSectionRow>
              <DropdownItem
                label="Fan curve preset"
                description="Choose a starting curve or fine-tune it below"
                rgOptions={FAN_PRESET_OPTIONS}
                selectedOption={fanPreset}
                onChange={(option) => {
                  if (option.data !== 'custom') {
                    setFanPreset(option.data);
                  }
                }}
              />
            </PanelSectionRow>
            <FanTelemetryRows />
            <PanelSectionRow>
              {/* ButtonItem's own internal padding can't be overridden via
                  props (no style prop), so constraining ITS wrapper to a
                  short height just let the button overflow it and collide
                  with the rows around it -- that was the earlier "odd
                  before you click it" look. Focusable gives us a plain,
                  still gamepad/keyboard-navigable clickable row with
                  padding we fully control, so it can actually be made
                  thin without that overflow problem. */}
              <Focusable
                style={{
                  width: '100%',
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  height: '24px',
                  borderBottom: showSliders
                    ? 'none'
                    : '1px solid rgba(255, 255, 255, 0.1)',
                  cursor: 'pointer'
                }}
                aria-label={
                  showSliders
                    ? 'Hide custom fan curve controls'
                    : 'Show custom fan curve controls'
                }
                onClick={() => setShowSliders(!showSliders)}
                onOKActionDescription={showSliders ? 'Hide' : 'Show'}
              >
                {showSliders ? <IoMdArrowDropup /> : <IoMdArrowDropdown />}
              </Focusable>
            </PanelSectionRow>
            {showSliders && (
              <PanelSectionRow>
                <ToggleField
                  label={'Enable Full Fan Speed Mode'}
                  checked={enableFullFanSpeedMode}
                  onChange={setEnableFullFanSpeedMode}
                />
              </PanelSectionRow>
            )}
            {showSliders && !enableFullFanSpeedMode && <FanCurveSliders />}
            <FanProfileTools />
          </>
        )}
      </PanelSection>
    </>
  );
};

export default FanPanel;
