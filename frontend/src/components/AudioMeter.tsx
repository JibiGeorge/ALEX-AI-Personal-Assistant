/**
 * AudioMeter Component (TASK-P4-04 / CAT-11)
 *
 * Real-time VU meter with RMS and peak level displays, visual clipping alerts,
 * and accessible meter semantics.
 */

export interface AudioMeterProps {
  rmsDb: number;
  peakDb: number;
  active: boolean;
  label?: string;
  onToggleActive?: () => void;
}

export function dbToPercent(db: number): number {
  if (db <= -60) return 0;
  if (db >= 0) return 100;
  return Math.max(0, Math.min(100, ((db + 60) / 60) * 100));
}

export function formatDb(db: number): string {
  if (db <= -60) return "-∞ dB";
  return `${db.toFixed(1)} dB`;
}

export function AudioMeter({
  rmsDb,
  peakDb,
  active,
  label = "Microphone input level",
  onToggleActive,
}: AudioMeterProps) {
  const rmsPercent = active ? dbToPercent(rmsDb) : 0;
  const peakPercent = active ? dbToPercent(peakDb) : 0;

  // Determine meter fill color based on RMS amplitude
  let barColor = "#55d5a2"; // Green / safe
  if (rmsDb > -3) {
    barColor = "#fc8181"; // Red / clipping
  } else if (rmsDb > -12) {
    barColor = "#f6ad55"; // Amber / caution
  }

  return (
    <div className="audio-meter-container" data-testid="audio-meter-container">
      <div className="audio-meter-header">
        <div className="audio-meter-label-group">
          <span className={`audio-meter-pip ${active ? "active" : ""}`} />
          <span className="audio-meter-title">{label}</span>
          <span className="audio-meter-state-badge">
            {active ? "LIVE" : "STANDBY"}
          </span>
        </div>

        <div className="audio-meter-readout">
          <span>RMS: {active ? formatDb(rmsDb) : "-∞ dB"}</span>
          <span className="audio-meter-divider">|</span>
          <span>Peak: {active ? formatDb(peakDb) : "-∞ dB"}</span>
        </div>
      </div>

      <div
        className="audio-meter-track"
        role="meter"
        aria-label={label}
        aria-valuenow={active ? Math.round(rmsDb) : -60}
        aria-valuemin={-60}
        aria-valuemax={0}
        aria-valuetext={active ? `${formatDb(rmsDb)} RMS` : "Inactive"}
      >
        {/* Background gradient track */}
        <div className="audio-meter-scale-backdrop" />

        {/* Dynamic RMS Level Fill */}
        <div
          className="audio-meter-fill"
          data-testid="audio-meter-fill"
          style={{
            width: `${rmsPercent}%`,
            backgroundColor: barColor,
          }}
        />

        {/* Peak Hold Tick */}
        {active && peakPercent > 0 && (
          <div
            className="audio-meter-peak"
            data-testid="audio-meter-peak"
            style={{
              left: `${Math.min(peakPercent, 99.5)}%`,
              backgroundColor: peakDb > -3 ? "#fc8181" : "#e2e8f0",
            }}
          />
        )}
      </div>

      {/* Scale Legend */}
      <div className="audio-meter-scale-labels" aria-hidden="true">
        <span>-60</span>
        <span>-48</span>
        <span>-36</span>
        <span>-24</span>
        <span>-12</span>
        <span>-6</span>
        <span>0 dB</span>
      </div>

      {onToggleActive && (
        <div className="audio-meter-actions">
          <button
            type="button"
            className="button button-secondary button-small"
            onClick={onToggleActive}
          >
            {active ? "Stop live monitor" : "Start live monitor"}
          </button>
        </div>
      )}
    </div>
  );
}
