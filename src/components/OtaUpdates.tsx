import { useEffect, useState } from 'react';
import { getLatestVersionNum, otaUpdate } from '../backend/utils';
import { useSelector } from 'react-redux';
import { getPluginVersionNumSelector } from '../redux-modules/uiSlice';
import {
  ButtonItem,
  Field,
  PanelSection,
  PanelSectionRow
} from '@decky/ui';

const OtaUpdates = () => {
  const [latestVersionNum, setLatestVersionNum] = useState('');
  const installedVersionNum = useSelector(getPluginVersionNumSelector);

  useEffect(() => {
    const fn = async () => {
      const fetchedVersionNum = await getLatestVersionNum();

      setLatestVersionNum(fetchedVersionNum);
    };

    fn();
  }, []);

  let buttonText = `Update to ${latestVersionNum}`;

  if (installedVersionNum === latestVersionNum && Boolean(latestVersionNum)) {
    buttonText = 'Reinstall Plugin';
  }

  return (
    <PanelSection title="Updates">
      <PanelSectionRow>
        <Field disabled label={'Installed Version'}>
          {installedVersionNum}
        </Field>
      </PanelSectionRow>

      {Boolean(latestVersionNum) && (
        <PanelSectionRow>
          <Field disabled label={'Latest Version'}>
            {latestVersionNum}
          </Field>
        </PanelSectionRow>
      )}
      {Boolean(latestVersionNum) && (
        <PanelSectionRow>
          <div
            style={{
              width: '100%',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center'
            }}
          >
            <ButtonItem
              onClick={() => {
                otaUpdate();
              }}
              layout={'below'}
            >
              {buttonText}
            </ButtonItem>
          </div>
        </PanelSectionRow>
      )}
    </PanelSection>
  );
};

export default OtaUpdates;
