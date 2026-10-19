import { useState, useMemo } from 'react';
import InputField from '../forms/InputField';
import FormError from '../forms/FormError';
import { validateBloodPressure, validateHeartRate } from '../../utils/validators';

export default function VitalSignsForm({ initialData = {}, onSave, isSaving = false }) {
  const [vitals, setVitals] = useState({
    systolic_bp: initialData.systolic_bp ?? '',
    diastolic_bp: initialData.diastolic_bp ?? '',
    heart_rate: initialData.heart_rate ?? '',
    respiratory_rate: initialData.respiratory_rate ?? '',
    spo2: initialData.spo2 ?? '',
    temperature_celsius: initialData.temperature_celsius ?? '',
    height_cm: initialData.height_cm ?? '',
    weight_kg: initialData.weight_kg ?? '',
  });

  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState(null);

  // Safe, physiological BMI calculation and classification
  const bmiCalculation = useMemo(() => {
    const h = Number(vitals.height_cm);
    const w = Number(vitals.weight_kg);

    // Physiological bounds guard (Adults: 50–250 cm, 20–350 kg)
    if (!vitals.height_cm || !vitals.weight_kg || isNaN(h) || isNaN(w) || h < 50 || h > 250 || w < 20 || w > 350) {
      return {
        value: null,
        formatted: '—',
        category: null,
        badgeColor: null,
        message: 'Enter valid height (50–250 cm) & weight (20–350 kg) to compute.',
      };
    }

    const heightM = h / 100;
    const computedBmi = w / (heightM * heightM);

    if (computedBmi < 10 || computedBmi > 90) {
      return {
        value: null,
        formatted: '—',
        category: 'Unrealistic Value',
        badgeColor: '#fee2e2',
        message: 'Calculated value is outside physiological human ranges.',
      };
    }

    let category = 'Normal Weight';
    let badgeColor = '#dcfce7'; // green
    let textColor = '#15803d';

    if (computedBmi < 18.5) {
      category = 'Underweight';
      badgeColor = '#fef3c7'; // yellow
      textColor = '#b45309';
    } else if (computedBmi >= 25.0 && computedBmi < 30.0) {
      category = 'Overweight';
      badgeColor = '#fef3c7';
      textColor = '#b45309';
    } else if (computedBmi >= 30.0) {
      category = 'Obesity (BMI \u2265 30)';
      badgeColor = '#fee2e2'; // red
      textColor = '#b91c1c';
    }

    return {
      value: Number(computedBmi.toFixed(1)),
      formatted: computedBmi.toFixed(1),
      category,
      badgeColor,
      textColor,
      message: `WHO Classification: ${category}`,
    };
  }, [vitals.height_cm, vitals.weight_kg]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setVitals((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: null }));
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setSubmitError(null);

    // Validate optional BP only if either is provided
    if (vitals.systolic_bp !== '' || vitals.diastolic_bp !== '') {
      const bpErr = validateBloodPressure(vitals.systolic_bp, vitals.diastolic_bp);
      if (bpErr) {
        setErrors((prev) => ({ ...prev, systolic_bp: bpErr }));
        return;
      }
    }

    // Validate optional HR only if provided
    if (vitals.heart_rate !== '') {
      const hrErr = validateHeartRate(vitals.heart_rate);
      if (hrErr) {
        setErrors((prev) => ({ ...prev, heart_rate: hrErr }));
        return;
      }
    }

    // Validate SpO2
    if (vitals.spo2 !== '') {
      const spo2Num = Number(vitals.spo2);
      if (isNaN(spo2Num) || spo2Num < 50 || spo2Num > 100) {
        setErrors((prev) => ({ ...prev, spo2: 'SpO2 must be between 50% and 100%' }));
        return;
      }
    }

    // Convert values preserving strict NULL for omitted fields
    // MANDATE: NEVER silently turn missing clinical measurements into zero.
    const payload = {
      systolic_bp: vitals.systolic_bp !== '' ? Number(vitals.systolic_bp) : null,
      diastolic_bp: vitals.diastolic_bp !== '' ? Number(vitals.diastolic_bp) : null,
      heart_rate: vitals.heart_rate !== '' ? Number(vitals.heart_rate) : null,
      respiratory_rate: vitals.respiratory_rate !== '' ? Number(vitals.respiratory_rate) : null,
      spo2: vitals.spo2 !== '' ? Number(vitals.spo2) : null,
      temperature_celsius: vitals.temperature_celsius !== '' ? Number(vitals.temperature_celsius) : null,
      height_cm: vitals.height_cm !== '' ? Number(vitals.height_cm) : null,
      weight_kg: vitals.weight_kg !== '' ? Number(vitals.weight_kg) : null,
      bmi: bmiCalculation.value,
    };

    onSave(payload);
  };

  return (
    <form onSubmit={handleSubmit} className="clean-card" style={{ maxWidth: '840px', margin: '0 auto', padding: '2rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
        <span className="pill-badge pill-badge-green">Objective Intake</span>
        <span className="modality-tag modality-objective">Physiological Measurements</span>
      </div>
      <h3 style={{ fontSize: '1.45rem', marginBottom: '0.35rem', color: 'var(--text-main)', letterSpacing: '-0.02em' }}>
        Clinical Vital Signs &amp; Anthropometrics
      </h3>
      <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', marginBottom: '2rem', lineHeight: 1.45 }}>
        Record objective vital measurements if available. Every measurement is genuinely optional; unmeasured parameters remain strictly <code>NULL</code> and are never defaulted to zero.
      </p>

      {submitError && <FormError message={submitError} onRetry={() => setSubmitError(null)} />}

      {/* SECTION 1: Cardiovascular & Hemodynamics */}
      <div style={{ marginBottom: '2rem' }}>
        <div style={{
          fontSize: '0.9rem',
          fontWeight: 700,
          color: 'var(--text-main)',
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
          borderBottom: '1px solid #f1f5f9',
          paddingBottom: '0.5rem',
          marginBottom: '1.25rem',
        }}>
          Cardiovascular &amp; Perfusion
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '1.25rem',
        }}>
          <InputField
            id="systolic_bp"
            label="Resting Systolic BP"
            type="number"
            value={vitals.systolic_bp}
            onChange={handleChange}
            placeholder="e.g. 120"
            unit="mmHg"
            optional
            min={50}
            max={260}
            error={errors.systolic_bp}
            helpText="Normal: 90 - 120 mmHg"
          />

          <InputField
            id="diastolic_bp"
            label="Resting Diastolic BP"
            type="number"
            value={vitals.diastolic_bp}
            onChange={handleChange}
            placeholder="e.g. 80"
            unit="mmHg"
            optional
            min={30}
            max={150}
            error={errors.diastolic_bp}
            helpText="Normal: 60 - 80 mmHg"
          />

          <InputField
            id="heart_rate"
            label="Resting Heart Rate"
            type="number"
            value={vitals.heart_rate}
            onChange={handleChange}
            placeholder="e.g. 72"
            unit="bpm"
            optional
            min={30}
            max={240}
            error={errors.heart_rate}
            helpText="Normal: 60 - 100 bpm"
          />

          <InputField
            id="spo2"
            label="Oxygen Saturation (SpO2)"
            type="number"
            value={vitals.spo2}
            onChange={handleChange}
            placeholder="e.g. 98"
            unit="%"
            min={50}
            max={100}
            optional
            error={errors.spo2}
            helpText="Normal: 95 - 100%"
          />
        </div>
      </div>

      {/* SECTION 2: General & Anthropometrics */}
      <div style={{ marginBottom: '2rem' }}>
        <div style={{
          fontSize: '0.9rem',
          fontWeight: 700,
          color: 'var(--text-main)',
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
          borderBottom: '1px solid #f1f5f9',
          paddingBottom: '0.5rem',
          marginBottom: '1.25rem',
        }}>
          Anthropometrics &amp; General Metrics
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '1.25rem',
        }}>
          <InputField
            id="height_cm"
            label="Standing Height"
            type="number"
            value={vitals.height_cm}
            onChange={handleChange}
            placeholder="e.g. 175"
            unit="cm"
            optional
            min={50}
            max={250}
            helpText="Plausible range: 50 - 250 cm"
          />

          <InputField
            id="weight_kg"
            label="Body Weight"
            type="number"
            value={vitals.weight_kg}
            onChange={handleChange}
            placeholder="e.g. 75"
            unit="kg"
            optional
            min={20}
            max={350}
            step="0.1"
            helpText="Plausible range: 20 - 350 kg"
          />

          <InputField
            id="temperature_celsius"
            label="Body Temperature"
            type="number"
            value={vitals.temperature_celsius}
            onChange={handleChange}
            placeholder="e.g. 36.8"
            unit="°C"
            optional
            step="0.1"
            min={30}
            max={45}
            helpText="Normal: 36.5 - 37.5 °C"
          />

          <InputField
            id="respiratory_rate"
            label="Respiratory Rate"
            type="number"
            value={vitals.respiratory_rate}
            onChange={handleChange}
            placeholder="e.g. 16"
            unit="breaths/min"
            optional
            min={6}
            max={60}
            helpText="Normal: 12 - 20 breaths/min"
          />
        </div>
      </div>

      {/* SECTION 3: Clearly Read-Only Calculated BMI Widget */}
      <div style={{
        backgroundColor: '#f8fafc',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid #e2e8f0',
        padding: '1.25rem 1.5rem',
        marginBottom: '2rem',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.92rem', fontWeight: 700, color: 'var(--text-main)' }}>
                Body Mass Index (BMI)
              </span>
              <span style={{
                fontSize: '0.7rem',
                fontWeight: 700,
                textTransform: 'uppercase',
                backgroundColor: '#e2e8f0',
                color: '#475569',
                padding: '0.15rem 0.5rem',
                borderRadius: 'var(--radius-pill)',
              }}>
                Read-Only Computed
              </span>
            </div>
            <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
              {bmiCalculation.message}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem' }}>
            <span style={{
              fontSize: '2rem',
              fontWeight: 800,
              fontFamily: 'var(--font-heading)',
              color: bmiCalculation.value ? 'var(--text-main)' : 'var(--text-muted)',
            }}>
              {bmiCalculation.formatted}
            </span>
            {bmiCalculation.value && (
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                kg/m²
              </span>
            )}
            {bmiCalculation.category && (
              <span style={{
                backgroundColor: bmiCalculation.badgeColor,
                color: bmiCalculation.textColor,
                padding: '0.25rem 0.65rem',
                borderRadius: 'var(--radius-pill)',
                fontSize: '0.78rem',
                fontWeight: 700,
              }}>
                {bmiCalculation.category}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
        <button
          type="submit"
          disabled={isSaving}
          className="btn btn-primary btn-lg"
          style={{ minWidth: '200px' }}
        >
          {isSaving ? 'Recording Vitals...' : 'Save & View Recommendations \u2192'}
        </button>
      </div>
    </form>
  );
}
