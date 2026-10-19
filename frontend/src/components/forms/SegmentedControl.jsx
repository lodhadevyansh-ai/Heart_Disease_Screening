import React from 'react';

export default function SegmentedControl({
  id,
  name,
  label,
  description,
  options = [
    { value: true, label: 'Yes' },
    { value: false, label: 'No' },
  ],
  value,
  onChange,
  disabled = false,
  error = null,
}) {
  const controlId = id || `seg-${name || label?.toLowerCase().replace(/\s+/g, '-')}`;

  return (
    <div className="form-group" style={{ marginBottom: '1.25rem' }}>
      {label && (
        <div style={{ marginBottom: '0.4rem' }}>
          <label
            id={`${controlId}-label`}
            htmlFor={controlId}
            style={{
              fontFamily: 'var(--font-heading)',
              fontSize: '0.88rem',
              fontWeight: 700,
              color: 'var(--text-main)',
              display: 'block',
              lineHeight: 1.35,
            }}
          >
            {label}
          </label>
          {description && (
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'block', marginTop: '0.15rem' }}>
              {description}
            </span>
          )}
        </div>
      )}

      <div
        id={controlId}
        role="radiogroup"
        aria-labelledby={label ? `${controlId}-label` : undefined}
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${options.length}, 1fr)`,
          gap: '0.35rem',
          backgroundColor: '#f1f5f9',
          padding: '0.3rem',
          borderRadius: 'var(--radius-lg)',
          border: `1px solid ${error ? 'var(--status-emergency)' : '#e2e8f0'}`,
        }}
      >
        {options.map((opt) => {
          const isSelected = value === opt.value;
          return (
            <button
              key={String(opt.value)}
              type="button"
              role="radio"
              aria-checked={isSelected}
              disabled={disabled}
              onClick={() => onChange(opt.value)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                textAlign: 'center',
                padding: '0.55rem 0.75rem',
                fontSize: '0.86rem',
                fontWeight: isSelected ? 700 : 500,
                borderRadius: 'var(--radius-md)',
                border: 'none',
                backgroundColor: isSelected ? 'var(--primary-red)' : 'transparent',
                color: isSelected ? '#ffffff' : 'var(--text-main)',
                boxShadow: isSelected ? '0 2px 8px rgba(230, 46, 61, 0.28)' : 'none',
                cursor: disabled ? 'not-allowed' : 'pointer',
                transition: 'all 0.15s ease',
                outline: 'none',
                minHeight: '38px',
                lineHeight: 1.25,
                wordBreak: 'break-word',
              }}
            >
              {isSelected && (
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  style={{ marginRight: '0.35rem', flexShrink: 0 }}
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              )}
              {opt.label}
            </button>
          );
        })}
      </div>

      {error && (
        <span className="form-error-msg" role="alert">
          {error}
        </span>
      )}
    </div>
  );
}
