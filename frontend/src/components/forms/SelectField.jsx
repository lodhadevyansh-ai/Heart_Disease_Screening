export default function SelectField({
  id,
  label,
  value,
  onChange,
  options = [],
  placeholder = 'Select an option',
  error,
  required = false,
  optional = false,
  disabled = false,
  helpText,
}) {
  const selectId = id || `select-${label?.toLowerCase().replace(/\s+/g, '-')}`;

  return (
    <div className="form-group">
      {label && (
        <label htmlFor={selectId} className="form-label">
          <span>
            {label} {required && <span style={{ color: 'var(--primary-red)' }}>*</span>}
          </span>
          {optional && <span className="form-label-optional">(Optional)</span>}
        </label>
      )}

      <select
        id={selectId}
        name={selectId}
        value={value ?? ''}
        onChange={onChange}
        disabled={disabled}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${selectId}-error` : undefined}
        className="form-control"
        style={{
          borderColor: error ? 'var(--status-emergency)' : undefined,
          cursor: 'pointer',
          appearance: 'auto',
        }}
      >
        <option value="" disabled>
          {placeholder}
        </option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      {helpText && !error && (
        <span style={{ fontSize: '0.78rem', color: 'var(--text-light)', marginTop: '0.2rem' }}>
          {helpText}
        </span>
      )}

      {error && (
        <span id={`${selectId}-error`} className="form-error-msg" role="alert">
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
