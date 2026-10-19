import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import InputField from '../components/forms/InputField';
import FormError from '../components/forms/FormError';

export default function Register() {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [role, setRole] = useState('patient');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const { register } = useAuth();
  const navigate = useNavigate();

  const validateClientSide = () => {
    if (!fullName.trim()) {
      return 'Please provide your full name.';
    }
    if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      return 'Please enter a valid email address.';
    }
    if (password.length < 8) {
      return 'Password must be at least 8 characters long.';
    }
    if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) {
      return 'Password must contain at least one letter and one number.';
    }
    if (password !== confirmPassword) {
      return 'Passwords do not match. Please verify your password confirmation.';
    }
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const clientError = validateClientSide();
    if (clientError) {
      setError(clientError);
      return;
    }

    setLoading(true);
    try {
      await register({
        full_name: fullName.trim(),
        email: email.trim().toLowerCase(),
        password,
        confirm_password: confirmPassword,
        role,
      });
      // Redirect to dashboard upon successful registration and auto-login
      navigate('/dashboard', { replace: true });
    } catch (err) {
      if (err.status === 409 || err.message?.toLowerCase().includes('already exists')) {
        setError('An account with this email already exists. Please log in.');
      } else {
        setError(err.message || 'Failed to create account. Please check your information and try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="clean-card" style={{ padding: '2.5rem 2rem' }}>
      <div style={{ textAlign: 'center', marginBottom: '1.75rem' }}>
        <h2 style={{ fontSize: '1.75rem', marginBottom: '0.4rem' }}>Create Account</h2>
        <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)' }}>
          Register for secure cardiovascular screening, risk assessments, and health records.
        </p>
      </div>

      {error && <FormError message={error} onRetry={() => setError(null)} />}

      <form onSubmit={handleSubmit}>
        <InputField
          id="full_name"
          label="Full Name"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          placeholder="e.g. Dr. Eleanor Vance or John Doe"
          required
        />

        <InputField
          id="email"
          label="Email Address"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="name@example.com"
          required
        />

        <div style={{ marginBottom: '1.25rem' }}>
          <label
            htmlFor="account_role"
            style={{
              display: 'block',
              fontSize: '0.85rem',
              fontWeight: 600,
              marginBottom: '0.4rem',
              color: 'var(--text-main)',
            }}
          >
            Account Type
          </label>
          <select
            id="account_role"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            style={{
              width: '100%',
              padding: '0.65rem 0.85rem',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-medium)',
              fontSize: '0.9rem',
              backgroundColor: '#ffffff',
              color: 'var(--text-main)',
            }}
          >
            <option value="patient">Patient Account (Personal health portal & history)</option>
            <option value="clinician">Clinician Account (Clinical intake, triage, & AI models)</option>
          </select>
        </div>

        <InputField
          id="password"
          label="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="At least 8 characters with letters & numbers"
          required
        />

        <InputField
          id="confirm_password"
          label="Confirm Password"
          type="password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          placeholder="Re-enter your password"
          required
        />

        <div style={{
          fontSize: '0.78rem',
          color: 'var(--text-muted)',
          lineHeight: 1.4,
          marginBottom: '1rem',
          backgroundColor: '#f9fafb',
          padding: '0.65rem 0.85rem',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid #e5e7eb',
        }}>
          Password requirement: Minimum 8 characters including at least one letter and one number. Passwords are cryptographically hashed and never stored in plaintext.
        </div>

        <button
          type="submit"
          disabled={loading}
          className="btn btn-primary"
          style={{ width: '100%', padding: '0.85rem' }}
        >
          {loading ? 'Creating Account...' : 'Create Account & Sign In'}
        </button>

        <div style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.88rem' }}>
          <span style={{ color: 'var(--text-muted)' }}>Already have an account? </span>
          <Link to="/login" style={{ color: 'var(--primary-red)', fontWeight: 600 }}>
            Sign In &rarr;
          </Link>
        </div>
      </form>
    </div>
  );
}
