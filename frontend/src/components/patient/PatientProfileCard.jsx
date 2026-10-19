import { formatDateTime } from '../../utils/formatters';

export default function PatientProfileCard({ patient }) {
  if (!patient) return null;

  return (
    <div className="clean-card" style={{ marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.35rem' }}>
            <span className="pill-badge">
              <span className="pill-dot" /> De-identified Patient
            </span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-light)' }}>
              ID: #{patient.id}
            </span>
          </div>
          <h3 style={{ fontSize: '1.6rem', color: 'var(--text-main)', letterSpacing: '-0.02em' }}>
            {patient.patient_code}
          </h3>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.35rem',
            padding: '0.35rem 0.85rem',
            borderRadius: 'var(--radius-pill)',
            fontSize: '0.82rem',
            fontWeight: 700,
            backgroundColor: patient.is_active ? 'var(--accent-green-subtle)' : '#f3f4f6',
            color: patient.is_active ? 'var(--accent-green)' : '#6b7280',
            border: `1px solid ${patient.is_active ? 'var(--accent-green-border)' : '#e5e7eb'}`,
          }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'currentColor' }} />
            {patient.is_active ? 'Active Profile' : 'Archived'}
          </span>
        </div>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
        gap: '1rem',
        padding: '1.25rem',
        backgroundColor: '#fafafa',
        borderRadius: 'var(--radius-md)',
        border: '1px solid #f0f0f0',
      }}>
        <div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Age</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-main)' }}>{patient.age} years</div>
        </div>

        <div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Biological Sex</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-main)' }}>{patient.sex}</div>
        </div>

        <div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Encounter Count</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-main)' }}>{patient.assessments_count || 0} visits</div>
        </div>

        <div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Created Date</div>
          <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-body)' }}>{formatDateTime(patient.created_at)}</div>
        </div>
      </div>

      {patient.notes && (
        <div style={{ marginTop: '1.25rem', fontSize: '0.9rem', color: 'var(--text-body)', lineHeight: 1.5 }}>
          <strong style={{ color: 'var(--text-main)' }}>Intake Notes: </strong>
          {patient.notes}
        </div>
      )}
    </div>
  );
}
