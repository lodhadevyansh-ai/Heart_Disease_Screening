export default function ProbabilityChart({
  probability,
  rawScore,
  isCalibrated,
  decisionThreshold = 0.5,
  scoreType = 'calibrated_probability',
}) {
  const value = probability !== null && probability !== undefined ? probability : rawScore ?? 0;
  const percentage = Math.min(Math.max(value * 100, 0), 100);
  const thresholdPercentage = decisionThreshold * 100;
  const isElevated = value >= decisionThreshold;

  return (
    <div style={{ margin: '1.25rem 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.4rem' }}>
        <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>
          {isCalibrated ? 'Calibrated Probability Estimate' : 'Classifier Score'}
        </span>
        <span style={{
          fontFamily: 'var(--font-heading)',
          fontSize: '1.8rem',
          fontWeight: 800,
          color: isElevated ? 'var(--primary-red)' : 'var(--accent-green)',
        }}>
          {isCalibrated ? `${percentage.toFixed(1)}%` : value.toFixed(3)}
        </span>
      </div>

      {/* Probability Gauge Bar */}
      <div style={{
        position: 'relative',
        height: '14px',
        backgroundColor: '#e5e7eb',
        borderRadius: 'var(--radius-pill)',
        overflow: 'hidden',
      }}>
        <div style={{
          height: '100%',
          width: `${percentage}%`,
          backgroundColor: isElevated ? 'var(--primary-red)' : 'var(--accent-green)',
          borderRadius: 'var(--radius-pill)',
          transition: 'width 0.8s cubic-bezier(0.16, 1, 0.3, 1)',
        }} />
      </div>

      {/* Threshold Marker Indicator */}
      <div style={{
        position: 'relative',
        height: '24px',
        marginTop: '0.25rem',
      }}>
        <div style={{
          position: 'absolute',
          left: `${thresholdPercentage}%`,
          transform: 'translateX(-50%)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}>
          <div style={{ width: '2px', height: '8px', backgroundColor: '#6b7280' }} />
          <span style={{ fontSize: '0.7rem', color: '#6b7280', fontWeight: 600, whiteSpace: 'nowrap' }}>
            Decision Threshold ({(thresholdPercentage).toFixed(0)}%)
          </span>
        </div>
      </div>

      {/* Calibration status pill */}
      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem', flexWrap: 'wrap' }}>
        {isCalibrated ? (
          <span className="pill-badge pill-badge-green" style={{ fontSize: '0.72rem', padding: '0.2rem 0.6rem' }}>
            &bull; Brier-Calibrated Probability
          </span>
        ) : (
          <span style={{
            fontSize: '0.72rem',
            padding: '0.2rem 0.6rem',
            borderRadius: 'var(--radius-pill)',
            backgroundColor: '#fef3c7',
            color: '#92400e',
            border: '1px solid #fde68a',
            fontWeight: 700,
          }}>
            &bull; Uncalibrated Confidence Score
          </span>
        )}
        <span style={{ fontSize: '0.75rem', color: 'var(--text-light)', alignSelf: 'center' }}>
          Metric type: {scoreType}
        </span>
      </div>
    </div>
  );
}
