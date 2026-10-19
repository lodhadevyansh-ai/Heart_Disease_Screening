import { useState } from 'react';
import InputField from '../forms/InputField';
import SelectField from '../forms/SelectField';
import FormError from '../forms/FormError';

const COMMON_LAB_TESTS = [
  { value: 'cholesterol', label: 'Total Cholesterol', unit: 'mg/dL', defaultHigh: 200 },
  { value: 'serum_creatinine', label: 'Serum Creatinine', unit: 'mg/dL', defaultHigh: 1.2 },
  { value: 'ejection_fraction', label: 'Left Ventricular Ejection Fraction (LVEF)', unit: '%', defaultHigh: 70 },
  { value: 'platelets', label: 'Platelet Count', unit: 'cells/mcL', defaultHigh: 450000 },
  { value: 'serum_sodium', label: 'Serum Sodium', unit: 'mEq/L', defaultHigh: 145 },
  { value: 'fasting_blood_sugar', label: 'Fasting Blood Sugar (Glucose)', unit: 'mg/dL', defaultHigh: 100 },
  { value: 'troponin_i', label: 'Cardiac Troponin I', unit: 'ng/mL', defaultHigh: 0.04 },
  { value: 'creatinine_phosphokinase', label: 'Creatinine Phosphokinase (CPK)', unit: 'mcg/L', defaultHigh: 200 },
];

export default function ReportEntryForm({ onSave, isSaving = false }) {
  const [testKey, setTestKey] = useState('cholesterol');
  const [valueNumeric, setValueNumeric] = useState('');
  const [unit, setUnit] = useState('mg/dL');
  const [referenceHigh, setReferenceHigh] = useState('200');
  const [flag, setFlag] = useState('normal');
  const [error, setError] = useState(null);

  const handleTestChange = (e) => {
    const selectedKey = e.target.value;
    setTestKey(selectedKey);
    const preset = COMMON_LAB_TESTS.find((t) => t.value === selectedKey);
    if (preset) {
      setUnit(preset.unit);
      setReferenceHigh(preset.defaultHigh ? String(preset.defaultHigh) : '');
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setError(null);

    if (valueNumeric === '') {
      setError('Please provide a numeric measurement value.');
      return;
    }

    const numVal = Number(valueNumeric);
    if (isNaN(numVal)) {
      setError('Measurement must be a valid number.');
      return;
    }

    onSave({
      test_name: testKey,
      value_numeric: numVal,
      unit: unit || null,
      reference_high: referenceHigh ? Number(referenceHigh) : null,
      flag: flag || 'normal',
    });

    setValueNumeric('');
  };

  return (
    <form onSubmit={handleSubmit} className="clean-card" style={{ maxWidth: '640px', margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.5rem' }}>
        <span className="pill-badge pill-badge-green">Structured Input</span>
        <span className="modality-tag modality-objective">Lab Value</span>
      </div>
      <h3 style={{ marginBottom: '0.4rem' }}>Record Laboratory Measurement</h3>
      <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', marginBottom: '1.5rem' }}>
        Structured lab parameters feed directly into condition-risk inference pipelines.
      </p>

      {error && <FormError message={error} onRetry={() => setError(null)} />}

      <div className="form-group">
        <label htmlFor="test_selection" className="form-label">
          Standardized Clinical Test
        </label>
        <select
          id="test_selection"
          value={testKey}
          onChange={handleTestChange}
          className="form-control"
        >
          {COMMON_LAB_TESTS.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label} ({t.unit})
            </option>
          ))}
        </select>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
        <InputField
          id="value_numeric"
          label="Measured Value"
          type="number"
          step="any"
          value={valueNumeric}
          onChange={(e) => setValueNumeric(e.target.value)}
          placeholder="e.g. 240"
          unit={unit}
          required
        />

        <InputField
          id="reference_high"
          label="Reference Limit (High)"
          type="number"
          step="any"
          value={referenceHigh}
          onChange={(e) => setReferenceHigh(e.target.value)}
          placeholder="e.g. 200"
          optional
        />

        <SelectField
          id="clinical_flag"
          label="Clinical Status Flag"
          value={flag}
          onChange={(e) => setFlag(e.target.value)}
          options={[
            { value: 'normal', label: 'Normal / Within Reference' },
            { value: 'high', label: 'Elevated (High)' },
            { value: 'critical_high', label: 'Critical High (Alert)' },
            { value: 'low', label: 'Below Reference (Low)' },
          ]}
        />
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1.5rem' }}>
        <button type="submit" disabled={isSaving} className="btn btn-primary">
          {isSaving ? 'Recording...' : 'Add Measurement'}
        </button>
      </div>
    </form>
  );
}
