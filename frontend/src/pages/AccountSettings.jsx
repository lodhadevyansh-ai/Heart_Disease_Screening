import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import Sidebar from '../components/common/Sidebar';
import InputField from '../components/forms/InputField';
import FormError from '../components/forms/FormError';

export default function AccountSettings() {
  const { user, deleteAccount } = useAuth();
  const navigate = useNavigate();

  const [showModal, setShowModal] = useState(false);
  const [password, setPassword] = useState('');
  const [modalError, setModalError] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDeleteConfirm = async (e) => {
    e.preventDefault();
    setModalError(null);

    if (!password) {
      setModalError('Please enter your current password to confirm deletion.');
      return;
    }

    setIsDeleting(true);
    try {
      await deleteAccount(password);
      setShowModal(false);
      // Redirect to login with confirmation notice
      navigate('/login', {
        replace: true,
        state: { message: 'Your account has been deleted.' },
      });
    } catch (err) {
      setModalError(err.message || 'Failed to delete account. Please verify your password and retry.');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="app-container" style={{ padding: '2rem 1rem' }}>
      <div style={{ display: 'flex', gap: '2rem', alignItems: 'flex-start' }}>
        <Sidebar />

        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Header */}
          <div style={{ marginBottom: '2rem' }}>
            <h1 style={{ fontSize: '2rem', marginBottom: '0.4rem', color: 'var(--text-main)' }}>
              Account Settings
            </h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem' }}>
              Manage your personal credentials, identity roles, and account security.
            </p>
          </div>

          {/* Profile Overview Card */}
          <div className="clean-card" style={{ padding: '2rem', marginBottom: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
              <div>
                <h2 style={{ fontSize: '1.35rem', marginBottom: '0.25rem' }}>Profile Information</h2>
                <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)' }}>
                  Active authentication claims verified by the CardioCare server.
                </p>
              </div>
              <span style={{
                padding: '0.35rem 0.85rem',
                borderRadius: '999px',
                fontSize: '0.8rem',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                backgroundColor: 'var(--primary-red-subtle)',
                color: 'var(--primary-red)',
                border: '1px solid rgba(230, 46, 61, 0.2)',
              }}>
                {user?.role || 'User'}
              </span>
            </div>

            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '1.25rem',
              backgroundColor: '#f9fafb',
              padding: '1.25rem',
              borderRadius: 'var(--radius-md)',
              border: '1px solid #e5e7eb',
            }}>
              <div>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Full Name
                </div>
                <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '0.2rem' }}>
                  {user?.full_name || user?.name || user?.username || '—'}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Email Address
                </div>
                <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-main)', marginTop: '0.2rem' }}>
                  {user?.email || '—'}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Username
                </div>
                <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-main)', marginTop: '0.2rem' }}>
                  {user?.username || '—'}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Account Identifier
                </div>
                <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-main)', marginTop: '0.2rem' }}>
                  UID #{user?.id || user?.sub || '—'}
                </div>
              </div>
            </div>
          </div>

          {/* Danger Zone: Account Deletion */}
          <div className="clean-card" style={{
            padding: '2rem',
            border: '1px solid #fecaca',
            backgroundColor: '#fffdfd',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
              <div style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                backgroundColor: '#fee2e2',
                color: '#dc2626',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
                  <path d="M12 9v4" />
                  <path d="M12 17h.01" />
                </svg>
              </div>
              <div>
                <h2 style={{ fontSize: '1.25rem', color: '#991b1b', margin: 0 }}>
                  Danger Zone: Permanent Account Deletion
                </h2>
                <p style={{ fontSize: '0.85rem', color: '#b91c1c', margin: '0.2rem 0 0' }}>
                  Irreversible account removal and credential revocation.
                </p>
              </div>
            </div>

            <p style={{ fontSize: '0.92rem', color: '#4b5563', lineHeight: 1.6, marginBottom: '1.5rem' }}>
              Deleting your account will permanently remove your login credentials, revoke your active session tokens, and prevent any future sign-in with this account. Any associated medical retention records are handled strictly according to institutional compliance policies.
            </p>

            <button
              type="button"
              onClick={() => {
                setShowModal(true);
                setPassword('');
                setModalError(null);
              }}
              className="btn btn-secondary"
              style={{
                color: '#dc2626',
                borderColor: '#fca5a5',
                backgroundColor: '#ffffff',
                fontWeight: 600,
              }}
            >
              Delete Account Permanently
            </button>
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      {showModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.55)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '1rem',
        }}>
          <div className="clean-card" style={{
            maxWidth: '480px',
            width: '100%',
            padding: '2rem',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2), 0 10px 10px -5px rgba(0, 0, 0, 0.1)',
            border: '1px solid #fecaca',
          }}>
            <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
              <div style={{
                width: '48px',
                height: '48px',
                borderRadius: '50%',
                backgroundColor: '#fee2e2',
                color: '#dc2626',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '0.75rem',
              }}>
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18 6 6 18" />
                  <path d="m6 6 12 12" />
                </svg>
              </div>
              <h3 style={{ fontSize: '1.35rem', color: 'var(--text-main)', marginBottom: '0.4rem' }}>
                Confirm Account Deletion
              </h3>
              <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                This action is permanent and cannot be reversed. Please enter your current password to authenticate and delete your account.
              </p>
            </div>

            {modalError && <FormError message={modalError} onRetry={() => setModalError(null)} />}

            <form onSubmit={handleDeleteConfirm}>
              <InputField
                id="reauth_password"
                label="Confirm Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your current password"
                required
              />

              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.5rem' }}>
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  disabled={isDeleting}
                  className="btn btn-secondary"
                  style={{ flex: 1 }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isDeleting}
                  className="btn"
                  style={{
                    flex: 1,
                    backgroundColor: '#dc2626',
                    color: '#ffffff',
                    borderColor: '#b91c1c',
                    fontWeight: 700,
                  }}
                >
                  {isDeleting ? 'Deleting...' : 'Delete Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
