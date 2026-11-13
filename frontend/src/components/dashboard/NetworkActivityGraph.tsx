export interface NetworkActivityGraphProps {
  speedMbPerSec: number | null;
  size?: number;
}

export function NetworkActivityGraph({
  speedMbPerSec,
  size = 82,
}: NetworkActivityGraphProps) {
  const isAvailable = speedMbPerSec !== null && !isNaN(speedMbPerSec);
  const displaySpeed = isAvailable ? speedMbPerSec.toFixed(1) : "N/A";
  const percentage = isAvailable ? Math.min((speedMbPerSec / 10) * 100, 100) : 0;
  const strokeWidth = 4.5;
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div
      className={`hud-circular-metric metric-green ${!isAvailable ? "metric-na" : ""}`}
      style={{ width: size, minWidth: size }}
    >
      <div className="circular-meter-svg-wrap" style={{ width: size, height: size }}>
        <svg
          className="circular-meter-svg"
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          aria-hidden="true"
        >
          {/* Subtle Radar Pulse Rings */}
          {isAvailable && speedMbPerSec > 0.1 && (
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius - 8}
              fill="none"
              stroke="#00ffc4"
              strokeWidth="1"
              className="meter-radar-pulse"
            />
          )}

          {/* Decorative Outer Ticks */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius + 4}
            fill="none"
            className="meter-outer-track"
            strokeDasharray="2 5"
          />

          {/* Background Track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            className="meter-bg-track"
            strokeWidth={strokeWidth}
          />

          {/* Active Network Progress Arc */}
          {isAvailable && (
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              className="meter-progress-arc"
              strokeWidth={strokeWidth}
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              transform={`rotate(-90 ${size / 2} ${size / 2})`}
            />
          )}
        </svg>

        {/* Center Content */}
        <div className="meter-center-content">
          <span className="meter-label">NET</span>
          <div className="meter-value-row">
            <strong className="meter-val-num">{displaySpeed}</strong>
            {isAvailable && <small className="meter-unit">MB/s</small>}
          </div>
        </div>
      </div>
      <span className="meter-subtext">{isAvailable ? "TX/RX LINK ACTIVE" : "OFFLINE"}</span>
    </div>
  );
}

