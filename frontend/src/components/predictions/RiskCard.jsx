import ProbabilityChart from './ProbabilityChart';
import FeatureExplanation from './FeatureExplanation';
import { formatDateTime } from '../../utils/formatters';

export default function RiskCard({ prediction }) {
  if (!prediction) return null;

  const isElevated =
    prediction.predicted_class_id === 1 ||
    (prediction.calibrated_probability !== null &&
      prediction.calibrated_probability >= (prediction.decision_threshold || 0.5));

  return (
    <div className="clean-card" style={{
      border: `1px solid ${isElevated ? '#fca5a5' : '#86efac'}`,
      backgroundColor: '#ffffff',
      marginBottom: '1.5rem',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Top Accent Strip */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        height: '4px',
        backgroundColor: isElevated ? 'var(--primary-red)' : 'var(--accent-green)',
      }} />

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
            <span className="pill-badge">
              <span className="pill-dot" /> {prediction.task_name?.replace(/_/g, ' ')}
            </span>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-light)', fontWeight: 600 }}>
              Model v{prediction.model_version} &bull; {prediction.model_name}
            </span>
          </div>
          <h3 style={{ fontSize: '1.45rem', color: 'var(--text-main)', letterSpacing: '-0.02em' }}>
            {prediction.predicted_class_label}
          </h3>
        </div>

        <span style={{ fontSize: '0.78rem', color: 'var(--text-light)' }}>
          {formatDateTime(prediction.created_at)}
        </span>
      </div>

      {/* Target Definition Box */}
      <div style={{
        backgroundColor: '#f8fafc',
        borderRadius: 'var(--radius-sm)',
        padding: '0.75rem 1rem',
        fontSize: '0.84rem',
        color: '#334155',
        marginBottom: '1rem',
      }}>
        <strong style={{ color: '#0f172a' }}>Audited Target Definition: </strong>
        {prediction.target_definition}
      </div>

      {/* Probability / Score Gauge */}
      <ProbabilityChart
        probability={prediction.calibrated_probability}
        rawScore={prediction.raw_score}
        isCalibrated={prediction.is_probability_calibrated}
        decisionThreshold={prediction.decision_threshold || 0.5}
        scoreType={prediction.score_type}
      />

      {/* Feature Explanations (SHAP / Perturbation) */}
      {prediction.explanation_snapshot && (
        <FeatureExplanation explanation={prediction.explanation_snapshot} />
      )}

      {/* Clinical Disclaimer from Record */}
      <div style={{
        marginTop: '1.25rem',
        paddingTop: '0.75rem',
        borderTop: '1px solid #f3f4f6',
        fontSize: '0.76rem',
        color: 'var(--text-light)',
      }}>
        <strong>Regulatory Notice: </strong>{prediction.clinical_prototype_disclaimer}
      </div>
    </div>
  );
}
