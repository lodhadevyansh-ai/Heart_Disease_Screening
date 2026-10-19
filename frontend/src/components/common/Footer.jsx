import { Link } from 'react-router-dom';
import { CLINICAL_SAFETY_DISCLAIMER } from '../../utils/constants';

export default function Footer() {
  return (
    <footer style={{
      backgroundColor: '#ffffff',
      borderTop: '1px solid var(--border-light)',
      padding: '3.5rem 0 2rem',
      marginTop: 'auto',
    }}>
      <div className="app-container">
        {/* Mandatory Clinical Disclaimer Banner */}
        <div style={{
          backgroundColor: '#fafafa',
          border: '1px solid #e5e7eb',
          borderRadius: 'var(--radius-lg)',
          padding: '1.25rem 1.5rem',
          marginBottom: '2.5rem',
          display: 'flex',
          gap: '1rem',
          alignItems: 'flex-start',
        }}>
          <div style={{
            color: 'var(--primary-red)',
            paddingTop: '2px',
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <div style={{ fontSize: '0.85rem', color: '#4b5563', lineHeight: '1.55' }}>
            <strong style={{ color: '#111827' }}>Clinical Decision Support Notice: </strong>
            {CLINICAL_SAFETY_DISCLAIMER}
          </div>
        </div>

        {/* Footer Navigation Columns */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '2.5rem',
          marginBottom: '2.5rem',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.9rem' }}>
              <div style={{
                width: '28px',
                height: '28px',
                borderRadius: '8px',
                backgroundColor: 'var(--primary-red)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#ffffff',
              }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />
                </svg>
              </div>
              <span style={{ fontFamily: 'var(--font-heading)', fontWeight: 800, fontSize: '1.2rem' }}>
                CardioCare <span style={{ color: 'var(--primary-red)' }}>AI</span>
              </span>
            </div>
            <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)' }}>
              Guided cardiovascular symptom triage, evidence-based test recommendations, and auditable condition-risk estimation.
            </p>
          </div>

          <div>
            <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.85rem' }}>Screening Modules</h4>
            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.88rem', color: 'var(--text-muted)' }}>
              <li><Link to="/symptom-assessment">Symptom Check-in</Link></li>
              <li><Link to="/test-recommendations">Clinical Recommendations</Link></li>
              <li><Link to="/report-management">Lab &amp; Report Management</Link></li>
              <li><Link to="/prediction-results">Condition-Risk Predictions</Link></li>
            </ul>
          </div>

          <div>
            <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.85rem' }}>Clinical Guidelines</h4>
            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.88rem', color: 'var(--text-muted)' }}>
              <li>AHA/ACC 2021 Chest Pain Guidelines</li>
              <li>ESC 2021 Heart Failure Guidelines</li>
              <li>ACC/AHA/HRS 2017 Syncope Evaluation</li>
              <li>HIPAA Safe Harbor De-identification</li>
            </ul>
          </div>

          <div>
            <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.85rem' }}>Emergency Primacy</h4>
            <p style={{ fontSize: '0.85rem', color: '#b91c1c', lineHeight: 1.5 }}>
              If experiencing crushing chest pain, radiating pain, severe dyspnea, or syncope, immediately call <strong>911 / EMS</strong>. Do not delay care for online tools.
            </p>
          </div>
        </div>

        {/* Bottom copyright */}
        <div style={{
          borderTop: '1px solid #f3f4f6',
          paddingTop: '1.5rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          fontSize: '0.82rem',
          color: 'var(--text-light)',
        }}>
          <div>&copy; {new Date().getFullYear()} CardioCare AI Research Prototype. Educational &amp; Clinical Decision Support.</div>
          <div style={{ display: 'flex', gap: '1.25rem' }}>
            <span>Model Version: 1.0.0</span>
            <span>API: /api/v1</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
