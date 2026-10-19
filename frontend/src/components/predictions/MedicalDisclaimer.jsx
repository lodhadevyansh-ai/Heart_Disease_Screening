import { CLINICAL_SAFETY_DISCLAIMER } from '../../utils/constants';

export default function MedicalDisclaimer({ compact = false }) {
  if (compact) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        padding: '0.65rem 1rem',
        backgroundColor: '#f8fafc',
        border: '1px solid #e2e8f0',
        borderRadius: 'var(--radius-pill)',
        fontSize: '0.78rem',
        color: '#475569',
      }}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--accent-green)' }}>
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
        <span><strong>Decision Support Only: </strong>Estimates are limited to supported conditions and are not a diagnosis.</span>
      </div>
    );
  }

  return (
    <div style={{
      backgroundColor: '#f8fafc',
      border: '1px solid #e2e8f0',
      borderRadius: 'var(--radius-lg)',
      padding: '1.25rem 1.5rem',
      margin: '1.5rem 0',
      display: 'flex',
      gap: '0.85rem',
      alignItems: 'flex-start',
    }}>
      <div style={{ color: '#0284c7', paddingTop: '2px' }}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      </div>
      <div style={{ fontSize: '0.85rem', color: '#334155', lineHeight: 1.55 }}>
        <strong style={{ color: '#0f172a' }}>Clinical Prototype &bull; SaMD Disclaimer: </strong>
        {CLINICAL_SAFETY_DISCLAIMER}
      </div>
    </div>
  );
}
