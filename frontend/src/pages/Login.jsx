import { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import InputField from '../components/forms/InputField';
import FormError from '../components/forms/FormError';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || '/dashboard';
  const infoMessage = location.state?.message;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!username.trim() || !password) {
      setError('Please provide both username/email and password.');
      return;
    }

    setLoading(true);
    try {
      await login(username.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message || 'Invalid username or password.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickFill = (u, p) => {
    setUsername(u);
    setPassword(p);
    setError(null);
  };

  return (
    <div className="clean-card" style={{ padding: '2.5rem 2rem' }}>
      <div style={{ textAlign: 'center', marginBottom: '1.75rem' }}>
        <h2 style={{ fontSize: '1.75rem', marginBottom: '0.4rem' }}>Clinical Sign In</h2>
        <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)' }}>
          Access cardiovascular screening records, reports, and AI models.
        </p>
      </div>

      {infoMessage && (
        <div style={{
          backgroundColor: '#eff6ff',
          border: '1px solid #bfdbfe',
          borderRadius: 'var(--radius-md)',
          padding: '0.85rem 1rem',
          marginBottom: '1.25rem',
          fontSize: '0.88rem',
          color: '#1e40af',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <path d="m9 12 2 2 4-4" />
          </svg>
          <span>{infoMessage}</span>
        </div>
      )}

      {error && <FormError message={error} onRetry={() => setError(null)} />}

      <form onSubmit={handleSubmit}>
        <InputField
          id="username"
          label="Username or Email"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="e.g. clinician_demo or name@hospital.demo"
          required
        />

        <InputField
          id="password"
          label="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••••••"
          required
        />

        <button
          type="submit"
          disabled={loading}
          className="btn btn-primary"
          style={{ width: '100%', marginTop: '1rem', padding: '0.85rem' }}
        >
          {loading ? 'Authenticating...' : 'Sign In to CardioCare'}
        </button>

        <div style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.88rem' }}>
          <span style={{ color: 'var(--text-muted)' }}>Don't have an account? </span>
          <Link to="/register" style={{ color: 'var(--primary-red)', fontWeight: 600 }}>
            Create one &rarr;
          </Link>
        </div>
      </form>

      {/* Quick Fill Demo Roles Box */}
      <div style={{
        marginTop: '2rem',
        paddingTop: '1.5rem',
        borderTop: '1px solid var(--border-light)',
      }}>
        <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.75rem', textAlign: 'center' }}>
          Quick Demo Accounts
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <button
            type="button"
            onClick={() => handleQuickFill('clinician_demo', 'ClinicianPass123!')}
            className="btn btn-secondary btn-sm"
            style={{ justifyContent: 'space-between', padding: '0.5rem 0.85rem' }}
          >
            <span><strong>Clinician:</strong> Dr. Sarah Chen, MD</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--primary-red)' }}>Autofill &rarr;</span>
          </button>
          <button
            type="button"
            onClick={() => handleQuickFill('patient_demo', 'PatientPass123!')}
            className="btn btn-secondary btn-sm"
            style={{ justifyContent: 'space-between', padding: '0.5rem 0.85rem' }}
          >
            <span><strong>Patient:</strong> Demo Patient (Self only)</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--primary-red)' }}>Autofill &rarr;</span>
          </button>
          <button
            type="button"
            onClick={() => handleQuickFill('admin_demo', 'AdminPass123!')}
            className="btn btn-secondary btn-sm"
            style={{ justifyContent: 'space-between', padding: '0.5rem 0.85rem' }}
          >
            <span><strong>Admin:</strong> System Administrator</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--primary-red)' }}>Autofill &rarr;</span>
          </button>
        </div>
      </div>
    </div>
  );
}
