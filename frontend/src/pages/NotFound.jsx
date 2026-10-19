import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <div className="app-container" style={{
      minHeight: '70vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '3rem 1rem',
      textAlign: 'center',
    }}>
      <div className="clean-card" style={{ maxWidth: '520px', padding: '3rem 2rem' }}>
        <div style={{
          width: '64px',
          height: '64px',
          borderRadius: '50%',
          backgroundColor: '#fee2e2',
          color: 'var(--primary-red)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 1.5rem',
        }}>
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>

        <span className="pill-badge" style={{ marginBottom: '0.75rem' }}>
          404 &bull; Resource Missing
        </span>

        <h2 style={{ fontSize: '2rem', marginBottom: '0.5rem', color: 'var(--text-main)', letterSpacing: '-0.02em' }}>
          Page Not Found
        </h2>

        <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', lineHeight: 1.5, marginBottom: '2rem' }}>
          The requested clinical screening module, patient encounter record, or URL path could not be located.
        </p>

        <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          <Link to="/dashboard" className="btn btn-primary">
            Return to Dashboard
          </Link>
          <Link to="/" className="btn btn-secondary">
            Visit Home
          </Link>
        </div>
      </div>
    </div>
  );
}
