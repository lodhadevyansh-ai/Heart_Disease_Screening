export default function InputField({
  id,
  label,
  type = 'text',
  value,
  onChange,
  placeholder,
  error,
  required = false,
  optional = false,
  min,
  max,
  step,
  unit,
  disabled = false,
  helpText,
}) {
  const inputId = id || `field-${label?.toLowerCase().replace(/\s+/g, '-')}`;

  return (
    <div className="form-group">
      {label && (
        <label htmlFor={inputId} className="form-label">
          <span>
            {label} {required && <span style={{ color: 'var(--primary-red)' }}>*</span>}
          </span>
          {optional && <span className="form-label-optional">(Optional)</span>}
        </label>
      )}

      <div
        style={{
          display: 'flex',
          alignItems: 'stretch',
          borderRadius: 'var(--radius-md)',
          border: `1px solid ${error ? 'var(--status-emergency)' : 'var(--border-light)'}`,
          backgroundColor: disabled ? '#f8fafc' : 'var(--bg-input)',
          overflow: 'hidden',
          transition: 'all var(--transition-fast)',
        }}
      >
        <input
          id={inputId}
          name={inputId}
          type={type}
          value={value ?? ''}
          onChange={onChange}
          placeholder={placeholder}
          min={min}
          max={max}
          step={step}
          disabled={disabled}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${inputId}-error` : undefined}
          style={{
            flex: 1,
            minWidth: 0,
            border: 'none',
            background: 'transparent',
            padding: '0.7rem 0.85rem',
            fontFamily: 'var(--font-sans)',
            fontSize: '0.95rem',
            color: disabled ? 'var(--text-muted)' : 'var(--text-main)',
            outline: 'none',
          }}
        />
        {unit && (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '0 0.75rem',
              backgroundColor: '#f1f5f9',
              borderLeft: '1px solid var(--border-light)',
              fontSize: '0.8rem',
              color: 'var(--text-muted)',
              fontWeight: 600,
              whiteSpace: 'nowrap',
              userSelect: 'none',
            }}
          >
            {unit}
          </span>
        )}
      </div>

      {helpText && !error && (
        <span style={{ fontSize: '0.78rem', color: 'var(--text-light)', marginTop: '0.2rem' }}>
          {helpText}
        </span>
      )}

      {error && (
        <span id={`${inputId}-error`} className="form-error-msg" role="alert">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {error}
        </span>
      )}
    </div>
  );
}
