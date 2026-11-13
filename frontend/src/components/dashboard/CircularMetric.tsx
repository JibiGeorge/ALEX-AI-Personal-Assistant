import { useId } from "react";

export interface CircularMetricProps {
  label: string;
  value: number | null;
  max?: number;
  unit?: string;
  subText?: string;
  warningThreshold?: number;
  criticalThreshold?: number;
  size?: number;
  strokeWidth?: number;
  color?: "cyan" | "pink" | "green" | "orange";
}

export function CircularMetric({
  label,
  value,
  max = 100,
  unit = "%",
  subText,
  warningThreshold = 75,
  criticalThreshold = 90,
  size = 82,
  strokeWidth = 4.5,
  color,
}: CircularMetricProps) {
  const filterId = useId();
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;

  const isAvailable = value !== null && !isNaN(value);
  const clampedValue = isAvailable ? Math.min(Math.max(value, 0), max) : 0;
  const percentage = (clampedValue / max) * 100;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  // Determine dynamic status color
  let themeColor = color;
  if (!themeColor) {
    if (!isAvailable) {
      themeColor = "cyan";
    } else if (clampedValue >= criticalThreshold) {
      themeColor = "pink"; // critical alert
    } else if (clampedValue >= warningThreshold) {
      themeColor = "orange"; // warning
    } else {
      themeColor = "cyan"; // normal nominal
    }
  }

  // Calculate endpoint angle for glow marker
  const angleRad = ((percentage / 100) * 360 - 90) * (Math.PI / 180);
  const endX = size / 2 + radius * Math.cos(angleRad);
  const endY = size / 2 + radius * Math.sin(angleRad);

  return (
    <div
      className={`hud-circular-metric metric-${themeColor} ${!isAvailable ? "metric-na" : ""}`}
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
          <defs>
            <filter id={`glow-${filterId}`} x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="2.5" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Decorative Outer Dashed Ring */}
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

          {/* Active Animated Progress Arc */}
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
              filter={`url(#glow-${filterId})`}
              transform={`rotate(-90 ${size / 2} ${size / 2})`}
            />
          )}

          {/* Glowing Endpoint Pip */}
          {isAvailable && percentage > 3 && (
            <circle
              cx={endX}
              cy={endY}
              r={strokeWidth * 0.7}
              className="meter-endpoint-glow"
              filter={`url(#glow-${filterId})`}
            />
          )}
        </svg>

        {/* Center Metric Display */}
        <div className="meter-center-content">
          <span className="meter-label">{label}</span>
          <div className="meter-value-row">
            <strong className="meter-val-num">
              {isAvailable
                ? `${unit === "%" ? Math.round(value) : value.toFixed(1)}${unit || ""}`
                : "N/A"}
            </strong>
          </div>
        </div>
      </div>

      {subText && <span className="meter-subtext">{subText}</span>}
    </div>
  );
}
