import {
  Focusable,
  PanelSection,
  PanelSectionRow,
  ToggleField
} from '@decky/ui';
import {
  useCustomFanCurvesEnabled,
  useEnableFullFanSpeedMode,
  useFanPerGameProfilesEnabled
} from '../../hooks/fan';
import { useAcpiCallDkms } from '../../hooks/ui';
import { capitalize } from 'lodash';
import { useSelector } from 'react-redux';
import { useState } from 'react';
import { selectCurrentGameDisplayName } from '../../redux-modules/uiSlice';
import FanCurveSliders from './FanCurveSliders';
import { IoMdArrowDropdown, IoMdArrowDropup } from 'react-icons/io';

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
  const { fanPerGameProfilesEnabled, setFanPerGameProfilesEnabled } =
    useFanPerGameProfilesEnabled();
  const title = useTitle(fanPerGameProfilesEnabled);

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
          </>
        )}
      </PanelSection>
      {customFanCurvesEnabled && !enableFullFanSpeedMode && showSliders && (
        <FanCurveSliders />
      )}
    </>
  );
};

export default FanPanel;
