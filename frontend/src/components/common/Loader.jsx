export default function Loader({ message = 'Loading clinical data...', size = 'md' }) {
  const pixelSize = size === 'sm' ? 24 : size === 'lg' ? 48 : 36;

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2.5rem 1rem',
      gap: '1rem',
    }}>
      <div style={{
        position: 'relative',
        width: `${pixelSize}px`,
        height: `${pixelSize}px`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'var(--primary-red)',
      }}>
        {/* Pulsing ring */}
        <div style={{
          position: 'absolute',
          inset: '-6px',
          borderRadius: '50%',
          border: '2px solid var(--primary-red)',
          opacity: 0.25,
          animation: 'pulseGlow 1.4s ease-out infinite',
        }} />
        {/* Heart icon */}
        <svg
          width={pixelSize}
          height={pixelSize}
          viewBox="0 0 24 24"
          fill="currentColor"
          style={{ animation: 'pulseGlow 1s ease-in-out infinite' }}
        >
          <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
        </svg>
      </div>
      {message && (
        <p style={{
          fontSize: '0.9rem',
          fontWeight: 600,
          color: 'var(--text-muted)',
          letterSpacing: '-0.01em',
        }}>
          {message}
        </p>
      )}
    </div>
  );
}
