import { Field, PanelSectionRow } from '@decky/ui';
import { useFanApplyState, useFanTelemetry } from '../../hooks/fan';

const ageText = (seconds?: number) => {
  if (seconds === undefined || seconds < 3) return 'just now';
  if (seconds < 60) return `${seconds}s ago`;
  return `${Math.floor(seconds / 60)}m ago`;
};

const FanTelemetryRows = () => {
  const { telemetry, telemetryError, telemetryAgeSeconds } = useFanTelemetry();
  const { fanApplyStatus, fanApplyError, fanAppliedAt } = useFanApplyState();
  const appliedAge = fanAppliedAt
    ? Math.max(0, Math.floor((Date.now() - fanAppliedAt) / 1000))
    : undefined;

  const applyText =
    fanApplyStatus === 'applying'
      ? 'Applying…'
      : fanApplyStatus === 'error'
        ? 'Apply failed'
        : fanApplyStatus === 'applied'
          ? `Applied ${ageText(appliedAge)}`
          : 'Ready';

  return (
    <>
      <PanelSectionRow>
        <Field label="Curve status" description={fanApplyError}>
          <span
            style={{
              color: fanApplyStatus === 'error' ? '#ff6b6b' : undefined,
              fontVariantNumeric: 'tabular-nums'
            }}
          >
            {applyText}
          </span>
        </Field>
      </PanelSectionRow>
      <PanelSectionRow>
        <Field
          label="Temperature"
          description={
            typeof telemetry?.temperatureC === 'number'
              ? `${telemetry.temperatureLabel || 'System sensor'} · Updated ${ageText(
                  telemetryAgeSeconds
                )}`
              : telemetryError ||
                'No compatible temperature sensor was detected'
          }
        >
          <span style={{ fontVariantNumeric: 'tabular-nums' }}>
            {typeof telemetry?.temperatureC === 'number'
              ? `${telemetry.temperatureC.toFixed(1)} °C`
              : 'Unavailable'}
          </span>
        </Field>
      </PanelSectionRow>
    </>
  );
};

export default FanTelemetryRows;
