import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import Loader from './Loader';

export default function ProtectedRoute({ children, allowedRoles = [] }) {
  const { isAuthenticated, loading, user } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div style={{ minHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Loader message="Verifying clinical credentials..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles.length > 0 && user?.role && !allowedRoles.includes(user.role)) {
    return (
      <div className="content-container" style={{ padding: '4rem 1rem', textAlign: 'center' }}>
        <div className="clean-card" style={{ maxWidth: '500px', margin: '0 auto', borderColor: '#fca5a5' }}>
          <h2 style={{ color: '#b91c1c', marginBottom: '0.75rem' }}>Access Restricted</h2>
          <p style={{ color: '#4b5563', marginBottom: '1.5rem' }}>
            Your account role (<strong>{user.role}</strong>) does not have permission to access this clinical module.
          </p>
          <a href="/dashboard" className="btn btn-secondary">
            Return to Dashboard
          </a>
        </div>
      </div>
    );
  }

  return children;
}
