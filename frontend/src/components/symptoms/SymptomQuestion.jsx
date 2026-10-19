export default function SymptomQuestion({
  id,
  label,
  description,
  iconType,
  selected,
  onToggle,
}) {
  const renderIcon = () => {
    switch (iconType) {
      case 'heart-crack':
        return (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />
            <path d="m12 13-1-1 2-2-3-3 2-2" />
          </svg>
        );
      case 'wind':
        return (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2" />
            <path d="M9.6 4.6A2 2 0 1 1 11 8H2" />
            <path d="M12.6 19.4A2 2 0 1 0 14 16H2" />
          </svg>
        );
      case 'pulse':
        return (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
          </svg>
        );
      case 'sparkle':
        return (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z" />
          </svg>
        );
      case 'battery-low':
        return (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <rect width="16" height="10" x="2" y="7" rx="2" ry="2" />
            <line x1="22" x2="22" y1="11" y2="13" />
            <line x1="6" x2="6" y1="11" y2="13" />
          </svg>
        );
      case 'footprint':
        return (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 16v-2.38C4 11.5 5.79 9.5 8 9.5s4 2 4 4.12V16a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2Z" />
            <path d="M12 20v-2.38c0-2.12 1.79-4.12 4-4.12s4 2 4 4.12V20a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2Z" />
          </svg>
        );
      default:
        return (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
          </svg>
        );
    }
  };

  return (
    <div
      role="checkbox"
      aria-checked={selected}
      tabIndex={0}
      onClick={() => onToggle(id)}
      onKeyDown={(e) => {
        if (e.key === ' ' || e.key === 'Enter') {
          e.preventDefault();
          onToggle(id);
        }
      }}
      className="clean-card"
      style={{
        cursor: 'pointer',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        minHeight: '140px',
        padding: '1.5rem',
        borderRadius: 'var(--radius-xl)',
        backgroundColor: '#ffffff',
        border: selected ? '2px solid var(--primary-red)' : '1px solid #f0efeb',
        boxShadow: selected ? '0 10px 30px rgba(230, 46, 61, 0.12)' : 'var(--shadow-card)',
        transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
        userSelect: 'none',
        outline: 'none',
      }}
    >
      {/* Top Header Row with Icon and Check Indicator */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div style={{
          width: '44px',
          height: '44px',
          borderRadius: '12px',
          backgroundColor: selected ? 'var(--primary-red)' : 'var(--primary-red-subtle)',
          color: selected ? '#ffffff' : 'var(--primary-red)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'all 0.2s ease',
        }}>
          {renderIcon()}
        </div>

        {/* Checkbox indicator circle */}
        <div style={{
          width: '24px',
          height: '24px',
          borderRadius: '50%',
          border: selected ? '2px solid var(--primary-red)' : '2px solid #e5e7eb',
          backgroundColor: selected ? 'var(--primary-red)' : '#ffffff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#ffffff',
          transition: 'all 0.2s ease',
        }}>
          {selected && (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          )}
        </div>
      </div>

      {/* Title */}
      <div style={{ marginTop: '1.25rem' }}>
        <h3 style={{
          fontSize: '1.25rem',
          fontWeight: 700,
          color: 'var(--text-main)',
          lineHeight: 1.25,
          letterSpacing: '-0.02em',
        }}>
          {label}
        </h3>
        {description && (
          <p style={{
            fontSize: '0.82rem',
            color: 'var(--text-muted)',
            marginTop: '0.35rem',
            lineHeight: 1.4,
          }}>
            {description}
          </p>
        )}
      </div>
    </div>
  );
}
