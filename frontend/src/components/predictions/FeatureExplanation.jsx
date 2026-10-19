export default function FeatureExplanation({ explanation }) {
  if (!explanation) return null;

  const riskIncreasing = explanation.risk_increasing_factors || [];
  const riskDecreasing = explanation.risk_decreasing_factors || [];
  const disclaimer = explanation.disclaimer || 'Feature attributions reflect statistical pipeline associations within training cohort distributions and do NOT establish biological causation.';

  return (
    <div style={{
      backgroundColor: '#ffffff',
      borderRadius: 'var(--radius-lg)',
      border: '1px solid var(--border-light)',
      padding: '1.25rem',
      marginTop: '1.25rem',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
        <h4 style={{ fontSize: '1rem', fontWeight: 700 }}>
          Local Feature Attributions ({explanation.method === 'tree_shap' ? 'Tree SHAP' : 'Perturbation Sensitivity'})
        </h4>
        <span className="modality-tag modality-ai">Model Explainability</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
        {/* Risk Increasing Factors */}
        <div style={{
          backgroundColor: '#fef2f2',
          border: '1px solid #fee2e2',
          borderRadius: 'var(--radius-md)',
          padding: '1rem',
        }}>
          <h5 style={{ fontSize: '0.85rem', color: '#991b1b', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span>&uarr;</span> Risk-Increasing Parameters
          </h5>
          {riskIncreasing.length === 0 ? (
            <p style={{ fontSize: '0.8rem', color: '#7f1d1d' }}>None identified</p>
          ) : (
            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.82rem' }}>
              {riskIncreasing.map((item, idx) => (
                <li key={idx} style={{ display: 'flex', justifyContent: 'space-between', color: '#7f1d1d' }}>
                  <span style={{ fontWeight: 600 }}>{item.feature}</span>
                  <span style={{ textTransform: 'capitalize' }}>{item.impact} impact</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Risk Decreasing Factors */}
        <div style={{
          backgroundColor: '#f0fdf4',
          border: '1px solid #dcfce7',
          borderRadius: 'var(--radius-md)',
          padding: '1rem',
        }}>
          <h5 style={{ fontSize: '0.85rem', color: '#166534', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span>&darr;</span> Risk-Decreasing / Protective Factors
          </h5>
          {riskDecreasing.length === 0 ? (
            <p style={{ fontSize: '0.8rem', color: '#14532d' }}>None identified</p>
          ) : (
            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.82rem' }}>
              {riskDecreasing.map((item, idx) => (
                <li key={idx} style={{ display: 'flex', justifyContent: 'space-between', color: '#14532d' }}>
                  <span style={{ fontWeight: 600 }}>{item.feature}</span>
                  <span style={{ textTransform: 'capitalize' }}>{item.impact} impact</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Non-causal disclaimer */}
      <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontStyle: 'italic', lineHeight: 1.4 }}>
        <strong>Non-Causal Notice: </strong>{disclaimer}
      </p>
    </div>
  );
}
