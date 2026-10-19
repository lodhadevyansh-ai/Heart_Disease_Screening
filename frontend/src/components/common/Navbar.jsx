import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import './Navbar.css';

export default function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const location = useLocation();

  // Track location changes during render to reset mobile drawer without cascading effects
  const [prevPath, setPrevPath] = useState(location.pathname + location.hash);
  const currentPath = location.pathname + location.hash;

  if (prevPath !== currentPath) {
    setPrevPath(currentPath);
    if (isMobileOpen) {
      setIsMobileOpen(false);
    }
  }

  // Close mobile drawer on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') setIsMobileOpen(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Compute clinician initials (e.g. "Dr. Sarah Jenkins" -> "SJ", "clinician" -> "CL")
  const getInitials = (name) => {
    if (!name) return 'MD';
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  };

  const clinicianName = user?.name || user?.username || 'Clinician';
  const clinicianRole = user?.role || 'Clinician';
  const initials = getInitials(clinicianName);

  const closeMobile = () => setIsMobileOpen(false);

  const isActive = (path) => {
    if (path === '/') {
      return location.pathname === '/' && !location.hash;
    }
    return location.pathname === path;
  };

  return (
    <header className="navbar-header" role="banner">
      <div className="navbar-container">
        <div className="navbar-inner">
          {/* 1. Brand Logo & Heart Icon */}
          <Link
            to="/"
            className="navbar-brand"
            aria-label="CardioCare AI Home"
            onClick={() => setIsMobileOpen(false)}
          >
            <div className="navbar-brand-badge" aria-hidden="true">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />
                <path d="M12 5v14" opacity="0.4" />
              </svg>
            </div>
            <span className="navbar-brand-text">
              CardioCare<span className="navbar-brand-ai">AI</span>
            </span>
          </Link>

          {/* 2. Desktop Navigation Links */}
          <nav className="navbar-nav" aria-label="Main Navigation">
            <Link
              to="/"
              className={`nav-link ${isActive('/') ? 'active' : ''}`}
              aria-current={isActive('/') ? 'page' : undefined}
            >
              Home
            </Link>
            <a
              href="/#how-it-works"
              className="nav-link"
            >
              How It Works
            </a>
            <a
              href="/#features"
              className="nav-link"
            >
              Features
            </a>

            {isAuthenticated && (
              <>
                <Link
                  to="/dashboard"
                  className={`nav-link ${isActive('/dashboard') ? 'active' : ''}`}
                  aria-current={isActive('/dashboard') ? 'page' : undefined}
                >
                  Dashboard
                </Link>
                <Link
                  to="/patient-profile"
                  className={`nav-link ${isActive('/patient-profile') ? 'active' : ''}`}
                  aria-current={isActive('/patient-profile') ? 'page' : undefined}
                >
                  Patients
                </Link>
                <Link
                  to="/assessment-history"
                  className={`nav-link ${isActive('/assessment-history') ? 'active' : ''}`}
                  aria-current={isActive('/assessment-history') ? 'page' : undefined}
                >
                  History
                </Link>
              </>
            )}
          </nav>

          {/* 3. Right Actions Cluster */}
          <div className="navbar-actions">
            {isAuthenticated ? (
              <>
                {/* Clinician Identity Card */}
                <div
                  className="clinician-badge"
                  title={`Signed in as ${clinicianName} (${clinicianRole})`}
                  aria-label={`Clinician: ${clinicianName}`}
                >
                  <div className="clinician-avatar" aria-hidden="true">
                    {initials}
                  </div>
                  <div className="clinician-details">
                    <span className="clinician-name">{clinicianName}</span>
                    <span className="clinician-role">{clinicianRole}</span>
                  </div>
                </div>

                {/* Settings Button */}
                <Link
                  to="/account-settings"
                  className="btn-nav-secondary"
                  title="Account Settings & Security"
                  aria-label="Account Settings"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                  <span>Settings</span>
                </Link>

                {/* Sign Out Button */}
                <button
                  type="button"
                  onClick={logout}
                  className="btn-nav-secondary"
                  title="Sign Out of Session"
                  aria-label="Sign Out"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                    <polyline points="16 17 21 12 16 7" />
                    <line x1="21" y1="12" x2="9" y2="12" />
                  </svg>
                  <span>Sign Out</span>
                </button>
              </>
            ) : (
              <Link to="/login" className="btn-nav-signin">
                Sign In
              </Link>
            )}

            {/* Primary Action Button: Start Screening */}
            <Link
              to="/symptom-assessment"
              className="btn-nav-primary"
              aria-label="Start Cardiovascular Screening"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
              </svg>
              <span>Start Screening</span>
            </Link>

            {/* Mobile Menu Hamburger Toggle */}
            <button
              type="button"
              className={`navbar-hamburger ${isMobileOpen ? 'active' : ''}`}
              onClick={() => setIsMobileOpen(!isMobileOpen)}
              aria-label={isMobileOpen ? "Close navigation menu" : "Open navigation menu"}
              aria-expanded={isMobileOpen}
            >
              {isMobileOpen ? (
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              ) : (
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="3" y1="12" x2="21" y2="12" />
                  <line x1="3" y1="6" x2="21" y2="6" />
                  <line x1="3" y1="18" x2="21" y2="18" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* 4. Responsive Mobile Drawer */}
      <div className={`navbar-mobile-drawer ${isMobileOpen ? 'open' : ''}`} role="dialog" aria-modal="true" aria-label="Mobile Navigation">
        {/* Clinician Card in Mobile Drawer */}
        {isAuthenticated && (
          <div className="mobile-user-card" style={{ marginBottom: '1.25rem' }}>
            <div className="clinician-avatar" style={{ width: '36px', height: '36px', fontSize: '0.85rem' }}>
              {initials}
            </div>
            <div className="clinician-details">
              <span className="clinician-name" style={{ fontSize: '0.92rem', maxWidth: 'none' }}>
                {clinicianName}
              </span>
              <span className="clinician-role" style={{ fontSize: '0.7rem' }}>
                {clinicianRole}
              </span>
            </div>
          </div>
        )}

        {/* Mobile Navigation Links */}
        <nav className="mobile-nav-links" aria-label="Mobile Navigation Links">
          <Link
            to="/"
            className={`mobile-nav-link ${isActive('/') ? 'active' : ''}`}
            onClick={closeMobile}
          >
            Home
          </Link>
          <a
            href="/#how-it-works"
            className="mobile-nav-link"
            onClick={closeMobile}
          >
            How It Works
          </a>
          <a
            href="/#features"
            className="mobile-nav-link"
            onClick={closeMobile}
          >
            Features
          </a>

          {isAuthenticated && (
            <>
              <Link
                to="/dashboard"
                className={`mobile-nav-link ${isActive('/dashboard') ? 'active' : ''}`}
                onClick={closeMobile}
              >
                Dashboard
              </Link>
              <Link
                to="/patient-profile"
                className={`mobile-nav-link ${isActive('/patient-profile') ? 'active' : ''}`}
                onClick={closeMobile}
              >
                Patients
              </Link>
              <Link
                to="/assessment-history"
                className={`mobile-nav-link ${isActive('/assessment-history') ? 'active' : ''}`}
                onClick={closeMobile}
              >
                History
              </Link>
            </>
          )}
        </nav>

        {/* Mobile Action Controls */}
        <div className="mobile-user-section">
          {isAuthenticated ? (
            <div className="mobile-actions-row">
              <Link
                to="/account-settings"
                className="btn-nav-secondary"
                style={{ height: '42px', fontSize: '0.9rem' }}
                onClick={closeMobile}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                <span>Settings</span>
              </Link>
              <button
                type="button"
                onClick={() => {
                  closeMobile();
                  logout();
                }}
                className="btn-nav-secondary"
                style={{ height: '42px', fontSize: '0.9rem' }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                  <polyline points="16 17 21 12 16 7" />
                  <line x1="21" y1="12" x2="9" y2="12" />
                </svg>
                <span>Sign Out</span>
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="btn-nav-secondary"
              style={{ height: '42px', width: '100%', fontSize: '0.95rem' }}
              onClick={closeMobile}
            >
              Sign In
            </Link>
          )}

          <Link
            to="/symptom-assessment"
            className="mobile-screening-btn"
            onClick={closeMobile}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
            <span>Start Screening</span>
          </Link>
        </div>
      </div>
    </header>
  );
}
