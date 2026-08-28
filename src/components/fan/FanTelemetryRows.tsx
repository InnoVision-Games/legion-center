import { PanelSectionRow } from '@decky/ui';
import type { FC, ReactNode } from 'react';
import { useFanApplyState, useFanTelemetry } from '../../hooks/fan';

const ageText = (seconds?: number) => {
  if (seconds === undefined || seconds < 3) return 'just now';
  if (seconds < 60) return `${seconds}s ago`;
  return `${Math.floor(seconds / 60)}m ago`;
};

type TelemetryRowProps = {
  label: string;
  description?: string;
  value: ReactNode;
  status?: boolean;
};

const TelemetryRow: FC<TelemetryRowProps> = ({
  label,
  description,
  value,
  status = false
}) => (
  <PanelSectionRow>
    <div
      role={status ? 'status' : undefined}
      aria-live={status ? 'polite' : undefined}
      style={{
        width: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '1rem'
      }}
    >
      <div style={{ minWidth: 0 }}>
        <div>{label}</div>
        {description && (
          <div style={{ marginTop: '0.25rem', fontSize: '0.75rem', opacity: 0.7 }}>
            {description}
          </div>
        )}
      </div>
      <div style={{ flexShrink: 0, fontVariantNumeric: 'tabular-nums' }}>
        {value}
      </div>
    </div>
  </PanelSectionRow>
);

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
      <TelemetryRow
        label="Curve status"
        description={fanApplyError}
        status
        value={
          <span
            style={{ color: fanApplyStatus === 'error' ? '#ff6b6b' : 'inherit' }}
          >
            {applyText}
          </span>
        }
      />
      <TelemetryRow
        label="Temperature"
        description={
          typeof telemetry?.temperatureC === 'number'
            ? `${telemetry.temperatureLabel || 'System sensor'} · Updated ${ageText(
                telemetryAgeSeconds
              )}`
            : telemetryError || 'No compatible temperature sensor was detected'
        }
        value={
          typeof telemetry?.temperatureC === 'number'
            ? `${telemetry.temperatureC.toFixed(1)} °C`
            : 'Unavailable'
        }
      />
    </>
  );
};

export default FanTelemetryRows;
