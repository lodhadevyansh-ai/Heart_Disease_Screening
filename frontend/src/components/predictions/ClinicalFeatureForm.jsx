import { useState, useEffect, useMemo, forwardRef, useImperativeHandle } from 'react';

// Clinical parameter definitions for Coronary Artery Disease (CAD)
const CAD_FIELD_DEFS = [
  {
    key: 'thalach',
    label: 'Maximum Heart Rate (thalach)',
    type: 'number',
    unit: 'bpm',
    min: 50,
    max: 240,
    step: 1,
    placeholder: 'e.g. 150',
    helpText: 'Peak heart rate achieved during exercise stress testing (bpm). Plausible bounds: 50–240 bpm. Measured value is required (resting heart rate cannot be substituted).',
    validate: (v) => {
      if (v === '' || v === null || v === undefined) return 'Maximum heart rate (thalach) is required for inference.';
      const n = Number(v);
      if (isNaN(n) || n < 50 || n > 240) return 'Maximum heart rate must be between 50 and 240 bpm.';
      return null;
    },
  },
  {
    key: 'chol',
    label: 'Serum Total Cholesterol',
    type: 'number',
    unit: 'mg/dL',
    min: 0,
    max: 700,
    step: 1,
    placeholder: 'e.g. 210',
    helpText: 'Plausible clinical bounds: 0–700 mg/dL. Values around 150–260 are typical. Note: 0 indicates historically unmeasured.',
    validate: (v) => {
      if (v === '' || v === null || v === undefined) return 'Cholesterol measurement is required.';
      const n = Number(v);
      if (isNaN(n) || n < 0 || n > 700) return 'Cholesterol must be between 0 and 700 mg/dL.';
      return null;
    },
  },
  {
    key: 'fbs',
    label: 'Fasting Blood Sugar > 120 mg/dL',
    type: 'select',
    options: [
      { value: '', label: '-- Select Fasting Glucose Status --' },
      { value: '0', label: 'Normal / Non-elevated (≤ 120 mg/dL) [fbs = 0]' },
      { value: '1', label: 'Elevated (> 120 mg/dL) [fbs = 1]' },
    ],
    helpText: 'Clinical diagnostic indicator for impaired fasting glucose.',
    validate: (v) => {
      if (v === '' || v === null || v === undefined) return 'Fasting blood sugar status is required.';
      if (v !== '0' && v !== '1' && v !== 0 && v !== 1) return 'Select a valid fasting glucose option.';
      return null;
    },
  },
  {
    key: 'restecg',
    label: 'Resting ECG Result',
    type: 'select',
    options: [
      { value: '', label: '-- Select Resting ECG Result --' },
      { value: 'normal', label: 'Normal' },
      { value: 'st-t abnormality', label: 'ST-T Wave Abnormality (T-inversions / ST deviation > 0.05 mV)' },
      { value: 'lv hypertrophy', label: 'Left Ventricular Hypertrophy (Estes criteria)' },
    ],
    helpText: 'Standard 12-lead resting electrocardiographic diagnostic finding.',
    validate: (v) => {
      if (!v) return 'Resting ECG result is required.';
      if (!['normal', 'st-t abnormality', 'lv hypertrophy'].includes(String(v).toLowerCase())) {
        return 'Select a valid resting ECG classification.';
      }
      return null;
    },
  },
  {
    key: 'oldpeak',
    label: 'Exercise-Induced ST Depression (oldpeak)',
    type: 'number',
    unit: 'mm',
    min: -3.0,
    max: 10.0,
    step: 0.1,
    placeholder: 'e.g. 0.0 or 1.5',
    helpText: 'ST segment depression relative to baseline. Plausible bounds: -3.0 to 10.0 mm. 0.0 mm is normal baseline.',
    validate: (v) => {
      if (v === '' || v === null || v === undefined) return 'ST depression value is required. Enter 0.0 if no depression.';
      const n = Number(v);
      if (isNaN(n) || n < -3.0 || n > 10.0) return 'ST depression must be between -3.0 and 10.0 mm.';
      return null;
    },
  },
  {
    key: 'slope',
    label: 'Peak Exercise ST Segment Slope',
    type: 'select',
    options: [
      { value: '', label: '-- Select Peak ST Slope --' },
      { value: 'upsloping', label: 'Upsloping (Typically lower ischemia probability)' },
      { value: 'flat', label: 'Flat (Equivocal / moderate ischemia indicator)' },
      { value: 'downsloping', label: 'Downsloping (High ischemia indicator)' },
    ],
    helpText: 'Slope morphology observed at peak treadmill / bicycle stress ECG.',
    validate: (v) => {
      if (!v) return 'Peak ST slope is required.';
      if (!['upsloping', 'flat', 'downsloping'].includes(String(v).toLowerCase())) {
        return 'Select a valid ST slope option.';
      }
      return null;
    },
  },
  {
    key: 'ca',
    label: 'Major Vessels with ≥50% Stenosis (ca)',
    type: 'select',
    options: [
      { value: '', label: '-- Select Fluoroscopy Vessels Count --' },
      { value: '0', label: '0 vessels (No major coronary narrowing)' },
      { value: '1', label: '1 major vessel' },
      { value: '2', label: '2 major vessels' },
      { value: '3', label: '3 major vessels (Multi-vessel CAD)' },
    ],
    helpText: 'Number of major coronary vessels (0–3) visualized by fluoroscopy. 0 is normal and clinically valid.',
    validate: (v) => {
      if (v === '' || v === null || v === undefined) return 'Fluoroscopy vessels count is required.';
      const n = Number(v);
      if (isNaN(n) || n < 0 || n > 3) return 'Vessels count must be an integer between 0 and 3.';
      return null;
    },
  },
  {
    key: 'thal',
    label: 'Thallium Stress Scintigraphy (thal)',
    type: 'select',
    options: [
      { value: '', label: '-- Select Scintigraphy Status --' },
      { value: 'normal', label: 'Normal Perfusion' },
      { value: 'fixed defect', label: 'Fixed Defect (Infarction / non-viable myocardium)' },
      { value: 'reversable defect', label: 'Reversible Defect (Ischemia with redistribution)' },
    ],
    helpText: 'Nuclear myocardial perfusion scintigraphy category.',
    validate: (v) => {
      if (!v) return 'Thallium scintigraphy result is required.';
      if (!['normal', 'fixed defect', 'reversable defect'].includes(String(v).toLowerCase())) {
        return 'Select a valid perfusion defect status.';
      }
      return null;
    },
  },
];

// Clinical parameter definitions for Heart Failure Survival (HF Mortality)
const HF_FIELD_DEFS = [
  {
    key: 'ejection_fraction',
    label: 'Left Ventricular Ejection Fraction (LVEF)',
    type: 'number',
    unit: '%',
    min: 10,
    max: 80,
    step: 1,
    placeholder: 'e.g. 35',
    helpText: 'Plausible bounds: 10–80%. Normal: 55–70%. Reduced (HFrEF): <40%.',
    validate: (v) => {
      if (v === '' || v === null || v === undefined) return 'Ejection fraction is required.';
      const n = Number(v);
      if (isNaN(n) || n < 10 || n > 80) return 'LVEF must be between 10% and 80%.';
      return null;
    },
  },
  {
    key: 'serum_creatinine',
    label: 'Serum Creatinine',
    type: 'number',
    unit: 'mg/dL',
    min: 0.1,
    max: 15.0,
    step: 0.1,
    placeholder: 'e.g. 1.2',
    helpText: 'Plausible bounds: 0.1–15.0 mg/dL. Normal baseline: 0.6–1.3 mg/dL.',
    validate: (v) => {
      if (v === '' || v === null || v === undefined) return 'Serum creatinine is required.';
      const n = Number(v);
      if (isNaN(n) || n < 0.1 || n > 15.0) return 'Serum creatinine must be between 0.1 and 15.0 mg/dL.';
      return null;
    },
  },
  {
    key: 'serum_sodium',
    label: 'Serum Sodium',
    type: 'number',
    unit: 'mEq/L',
    min: 100,
    max: 175,
    step: 1,
    placeholder: 'e.g. 138',
    helpText: 'Plausible bounds: 100–175 mEq/L. Normal baseline: 135–145 mEq/L.',
    validate: (v) => {
      if (v === '' || v === null || v === undefined) return 'Serum sodium is required.';
      const n = Number(v);
      if (isNaN(n) || n < 100 || n > 175) return 'Serum sodium must be between 100 and 175 mEq/L.';
      return null;
    },
  },
  {
    key: 'platelets',
    label: 'Platelet Count',
    type: 'number',
    unit: '/mcL',
    min: 10000,
    max: 1500000,
    step: 1000,
    placeholder: 'e.g. 250000',
    helpText: 'Plausible bounds: 10,000–1,500,000 /mcL. Normal: 150,000–450,000 /mcL.',
    validate: (v) => {
      if (v === '' || v === null || v === undefined) return 'Platelet count is required.';
      const n = Number(v);
      if (isNaN(n) || n < 10000 || n > 1500000) return 'Platelets must be between 10,000 and 1,500,000 /mcL.';
      return null;
    },
  },
  {
    key: 'creatinine_phosphokinase',
    label: 'Creatinine Phosphokinase (CPK)',
    type: 'number',
    unit: 'U/L',
    min: 10,
    max: 10000,
    step: 1,
    placeholder: 'e.g. 250',
    helpText: 'Plausible bounds: 10–10,000 U/L. Normal range: 20–200 U/L.',
    validate: (v) => {
      if (v === '' || v === null || v === undefined) return 'CPK enzyme level is required.';
      const n = Number(v);
      if (isNaN(n) || n < 10 || n > 10000) return 'CPK must be between 10 and 10,000 U/L.';
      return null;
    },
  },
  {
    key: 'anaemia',
    label: 'Anaemia Indicator (Hb < 12 g/dL)',
    type: 'select',
    options: [
      { value: '', label: '-- Select Anaemia Status --' },
      { value: '0', label: '0: No Anaemia (Normal hemoglobin ≥ 12 g/dL)' },
      { value: '1', label: '1: Anaemia Present (Hemoglobin < 12 g/dL)' },
    ],
    helpText: 'Indicates clinically significant decrease in red blood cells or hemoglobin.',
    validate: (v) => {
      if (v === '' || v === null || v === undefined) return 'Anaemia status is required.';
      if (v !== '0' && v !== '1' && v !== 0 && v !== 1) return 'Select valid anaemia status.';
      return null;
    },
  },
  {
    key: 'diabetes',
    label: 'Diabetes Mellitus History',
    type: 'select',
    options: [
      { value: '', label: '-- Select Diabetes Status --' },
      { value: '0', label: '0: No Diabetes (Fasting glucose < 126 mg/dL / HbA1c < 6.5%)' },
      { value: '1', label: '1: Diabetes Present' },
    ],
    helpText: 'Diagnosed diabetes mellitus or verified glycemic elevation.',
    validate: (v) => {
      if (v === '' || v === null || v === undefined) return 'Diabetes status is required.';
      if (v !== '0' && v !== '1' && v !== 0 && v !== 1) return 'Select valid diabetes status.';
      return null;
    },
  },
  {
    key: 'smoking',
    label: 'Tobacco Smoking Status',
    type: 'select',
    options: [
      { value: '', label: '-- Select Smoking Status --' },
      { value: '0', label: '0: Non-smoker' },
      { value: '1', label: '1: Active or Recent Tobacco Smoker' },
    ],
    helpText: 'Current or recent history of active tobacco smoking.',
    validate: (v) => {
      if (v === '' || v === null || v === undefined) return 'Smoking status is required.';
      if (v !== '0' && v !== '1' && v !== 0 && v !== 1) return 'Select valid smoking status.';
      return null;
    },
  },
];

const ClinicalFeatureForm = forwardRef(function ClinicalFeatureForm(
  {
    task,
    patient,
    assessmentDetails,
    symptomsData,
    vitalsData,
    initialFeatures = {},
    onChange,
  },
  ref
) {
  const isCad = task === 'coronary_artery_disease';
  const isHf = task === 'heart_failure_mortality';
  const fieldDefs = useMemo(() => {
    return isCad ? CAD_FIELD_DEFS : isHf ? HF_FIELD_DEFS : [];
  }, [isCad, isHf]);

  // Form input state
  const [formData, setFormData] = useState({});
  const [touched, setTouched] = useState({});

  // Populate from initialFeatures or persisted labs
  useEffect(() => {
    const prefill = {};
    fieldDefs.forEach((f) => {
      let initVal = initialFeatures[f.key];
      if (f.key === 'thalach' && (initVal === undefined || initVal === null || initVal === '')) {
        initVal = initialFeatures.thalch ?? initialFeatures.maximum_heart_rate;
      }
      if (initVal !== undefined && initVal !== null && initVal !== '') {
        prefill[f.key] = String(initVal);
      } else {
        prefill[f.key] = '';
      }
    });
    setFormData(prefill);
  }, [fieldDefs, initialFeatures]);

  // Resolve authoritative patient record
  const effectivePatient = useMemo(() => {
    return patient || assessmentDetails?.patient || null;
  }, [patient, assessmentDetails]);

  // Derive age with date-of-birth fallback
  const derivedAge = useMemo(() => {
    const rawAge = effectivePatient?.age ?? effectivePatient?.patient_age;
    if (rawAge !== undefined && rawAge !== null && rawAge !== '') {
      const n = Number(rawAge);
      if (!isNaN(n) && n >= 0) return n;
    }
    const dobStr = effectivePatient?.date_of_birth || effectivePatient?.dob;
    if (dobStr) {
      const dob = new Date(dobStr);
      if (!isNaN(dob.getTime())) {
        const refDate = assessmentDetails?.assessment_date ? new Date(assessmentDetails.assessment_date) : new Date();
        let diffYears = refDate.getFullYear() - dob.getFullYear();
        const m = refDate.getMonth() - dob.getMonth();
        if (m < 0 || (m === 0 && refDate.getDate() < dob.getDate())) {
          diffYears--;
        }
        if (diffYears >= 0) return diffYears;
      }
    }
    return null;
  }, [effectivePatient, assessmentDetails]);

  // Normalize sex to Male or Female
  const derivedSex = useMemo(() => {
    const rawSex = effectivePatient?.sex ?? effectivePatient?.biological_sex ?? effectivePatient?.gender;
    if (!rawSex) return null;
    const s = String(rawSex).trim().toLowerCase();
    if (s === 'male' || s === 'm' || s === '1') return 'Male';
    if (s === 'female' || s === 'f' || s === '0') return 'Female';
    return String(rawSex).trim();
  }, [effectivePatient]);

  // Derived auto-mapped features from patient demographics, vitals, and symptoms
  const preMappedEncounterFeatures = useMemo(() => {
    if (isCad) {
      return [
        {
          key: 'age',
          name: 'Age (age)',
          value: derivedAge !== null ? `${derivedAge} years` : 'Missing',
          source: 'Patient Record',
          valid: derivedAge !== null && derivedAge >= 18 && derivedAge <= 120,
        },
        {
          key: 'sex',
          name: 'Biological Sex (sex)',
          value: derivedSex ? derivedSex : 'Missing',
          source: 'Patient Record',
          valid: derivedSex === 'Male' || derivedSex === 'Female',
        },
        {
          key: 'cp',
          name: 'Chest Pain Type (cp)',
          value: symptomsData?.angina_classification
            ? symptomsData.angina_classification.replace(/_/g, ' ')
            : symptomsData?.chest_pain === false
            ? 'Asymptomatic'
            : 'Missing',
          source: 'Symptoms Intake',
          valid: Boolean(symptomsData?.angina_classification || symptomsData?.chest_pain === false),
        },
        {
          key: 'trestbps',
          name: 'Resting Blood Pressure (trestbps)',
          value: vitalsData?.systolic_bp ? `${vitalsData.systolic_bp} mmHg` : 'Missing',
          source: 'Vital Signs',
          valid: Boolean(vitalsData?.systolic_bp && vitalsData.systolic_bp >= 50 && vitalsData.systolic_bp <= 260),
        },
        {
          key: 'exang',
          name: 'Exercise-Induced Angina (exang)',
          value:
            symptomsData?.exertional_provocation !== undefined && symptomsData?.exertional_provocation !== null
              ? symptomsData.exertional_provocation
                ? 'Yes (Exertional provocation: 1)'
                : 'No (Provocation absent: 0)'
              : 'Missing',
          source: 'Symptoms Intake',
          valid: symptomsData?.exertional_provocation !== undefined && symptomsData?.exertional_provocation !== null,
        },
      ];
    } else if (isHf) {
      const isHtn =
        vitalsData?.systolic_bp !== undefined && vitalsData?.diastolic_bp !== undefined
          ? vitalsData.systolic_bp >= 140 || vitalsData.diastolic_bp >= 90
            ? '1 (Hypertensive: BP ≥ 140/90)'
            : '0 (Normotensive: BP < 140/90)'
          : 'Missing';

      return [
        {
          key: 'age',
          name: 'Age (age)',
          value: derivedAge !== null ? `${derivedAge} years` : 'Missing',
          source: 'Patient Record',
          valid: derivedAge !== null && derivedAge >= 18 && derivedAge <= 120,
        },
        {
          key: 'sex',
          name: 'Biological Sex (sex)',
          value: derivedSex ? (derivedSex === 'Male' ? '1 (Male)' : '0 (Female)') : 'Missing',
          source: 'Patient Record',
          valid: derivedSex === 'Male' || derivedSex === 'Female',
        },
        {
          key: 'high_blood_pressure',
          name: 'High Blood Pressure History (high_blood_pressure)',
          value: isHtn,
          source: 'Vital Signs Derivation',
          valid: Boolean(vitalsData?.systolic_bp && vitalsData?.diastolic_bp),
        },
      ];
    }
    return [];
  }, [derivedAge, derivedSex, symptomsData, vitalsData, isCad, isHf]);

  // Compute field errors and completion status
  const { errors, isValid, missingFields, totalFeatures, readyFeatures } = useMemo(() => {
    const errs = {};
    const missing = [];

    // Validate structured form fields
    fieldDefs.forEach((def) => {
      const val = formData[def.key];
      const err = def.validate(val);
      if (err) {
        errs[def.key] = err;
        missing.push(def.key);
      }
    });

    // Check pre-mapped encounter features
    preMappedEncounterFeatures.forEach((f) => {
      if (!f.valid) {
        missing.push(f.name);
      }
    });

    const total = preMappedEncounterFeatures.length + fieldDefs.length;
    const ready = total - missing.length;
    const valid = missing.length === 0;

    return {
      errors: errs,
      isValid: valid,
      missingFields: missing,
      totalFeatures: total,
      readyFeatures: ready,
    };
  }, [formData, fieldDefs, preMappedEncounterFeatures]);

  // Notify parent of state updates
  useEffect(() => {
    if (onChange) {
      const payloadData = { ...formData };
      if (payloadData.thalach !== undefined && payloadData.thalch === undefined) {
        payloadData.thalch = payloadData.thalach;
      }
      onChange({
        isValid,
        formData: payloadData,
        errors,
        missingFields,
        readyFeatures,
        totalFeatures,
      });
    }
  }, [isValid, formData, errors, missingFields, readyFeatures, totalFeatures, onChange]);

  // Expose focusFirstMissing method via ref
  useImperativeHandle(ref, () => ({
    focusFirstMissing: () => {
      for (const def of fieldDefs) {
        if (errors[def.key]) {
          const el = document.getElementById(`field-${def.key}`);
          if (el) {
            el.focus();
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            return;
          }
        }
      }
    },
  }));

  const handleFieldChange = (key, value) => {
    setFormData((prev) => {
      const updated = { ...prev, [key]: value };
      if (key === 'thalach') {
        updated.thalch = value;
      } else if (key === 'thalch') {
        updated.thalach = value;
      }
      return updated;
    });
    setTouched((prev) => ({ ...prev, [key]: true }));
  };

  if (!isCad && !isHf) {
    return null;
  }

  return (
    <div
      id="clinical-feature-form"
      className="clean-card"
      style={{
        marginBottom: '2rem',
        border: isValid ? '1px solid #86efac' : '1px solid #fde047',
        backgroundColor: '#fafafa',
      }}
    >
      {/* Form Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '1.25rem',
        }}
      >
        <div>
          <span
            className="pill-badge"
            style={{
              backgroundColor: isValid ? '#dcfce7' : '#fef3c7',
              color: isValid ? '#15803d' : '#92400e',
              border: `1px solid ${isValid ? '#86efac' : '#fde047'}`,
              marginBottom: '0.4rem',
            }}
          >
            {isValid ? '✓ All Required Features Validated' : '⚠ Required Clinical Inputs Needed'}
          </span>
          <h3 style={{ fontSize: '1.3rem', margin: '0.2rem 0' }}>
            {isCad
              ? 'Coronary Artery Disease Feature Verification (13 Features)'
              : 'Heart Failure Mortality Stratifier Inputs (11 Features)'}
          </h3>
          <p style={{ fontSize: '0.86rem', color: 'var(--text-muted)' }}>
            {isCad
              ? 'The CAD model requires 13 physiological parameters. Pre-mapped features are derived from this encounter; please review or provide the remaining laboratory and diagnostic tests below.'
              : 'The HF Survival model requires 11 prognostic biomarkers for mortality risk evaluation in confirmed heart failure patients. Never use for general screening.'}
          </p>
        </div>

        <div style={{ textAlign: 'right' }}>
          <div
            style={{
              fontSize: '1.5rem',
              fontWeight: 800,
              fontFamily: 'var(--font-heading)',
              color: isValid ? 'var(--accent-green)' : 'var(--primary-red)',
            }}
          >
            {readyFeatures} / {totalFeatures}
          </div>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 600 }}>
            Features Ready for Inference
          </span>
        </div>
      </div>

      {/* Section 1: Pre-mapped Encounter Features */}
      <div style={{ marginBottom: '1.75rem' }}>
        <h4 style={{ fontSize: '0.95rem', color: '#1e293b', marginBottom: '0.6rem', fontWeight: 700 }}>
          1. Auto-Mapped Encounter Values ({preMappedEncounterFeatures.length})
        </h4>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.75rem' }}>
          {preMappedEncounterFeatures.map((f, i) => (
            <div
              key={i}
              style={{
                backgroundColor: f.valid ? '#ffffff' : '#fef2f2',
                border: `1px solid ${f.valid ? '#e2e8f0' : '#fca5a5'}`,
                borderRadius: 'var(--radius-md)',
                padding: '0.75rem',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-light)', fontWeight: 600 }}>
                  {f.source}
                </span>
                <span style={{ fontSize: '0.75rem', color: f.valid ? '#15803d' : '#b91c1c' }}>
                  {f.valid ? '✓ Ready' : '✗ Missing'}
                </span>
              </div>
              <div style={{ fontSize: '0.84rem', fontWeight: 600, color: '#0f172a' }}>
                {f.name}
              </div>
              <div style={{ fontSize: '0.92rem', color: f.valid ? '#1e293b' : '#dc2626', fontWeight: 700, marginTop: '0.2rem' }}>
                {f.value}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Section 2: Missing Required Clinical / Laboratory Inputs */}
      <div>
        <h4 style={{ fontSize: '0.95rem', color: '#1e293b', marginBottom: '0.4rem', fontWeight: 700 }}>
          2. Required Diagnostic &amp; Laboratory Inputs ({fieldDefs.length})
        </h4>
        <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
          Silently imputing missing clinical values with zeros, means, or synthetic defaults is strictly prohibited.
          Legitimate physiological zeros (e.g. 0.0 mm ST depression, 0 vessels) are preserved and distinguished from missing data.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem' }}>
          {fieldDefs.map((def) => {
            const val = formData[def.key] ?? '';
            const err = errors[def.key];
            const isFieldValid = !err && (val !== '' && val !== null && val !== undefined);
            const isTouched = touched[def.key];

            return (
              <div
                key={def.key}
                style={{
                  backgroundColor: '#ffffff',
                  border: `1px solid ${err && isTouched ? '#fca5a5' : isFieldValid ? '#86efac' : '#cbd5e1'}`,
                  borderRadius: 'var(--radius-md)',
                  padding: '1rem',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
                  transition: 'border-color 0.15s ease',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.35rem' }}>
                  <label
                    htmlFor={`field-${def.key}`}
                    className="form-label"
                    style={{ marginBottom: 0, fontWeight: 700, fontSize: '0.88rem' }}
                  >
                    {def.label} {def.unit && <span style={{ color: 'var(--text-muted)', fontWeight: 500 }}>({def.unit})</span>}
                  </label>
                  {isFieldValid && (
                    <span style={{ fontSize: '0.72rem', color: '#15803d', fontWeight: 700 }}>
                      ✓ Valid
                    </span>
                  )}
                  {err && isTouched && (
                    <span style={{ fontSize: '0.72rem', color: '#b91c1c', fontWeight: 700 }}>
                      ✗ Required
                    </span>
                  )}
                </div>

                {def.type === 'number' ? (
                  <input
                    id={`field-${def.key}`}
                    type="number"
                    min={def.min}
                    max={def.max}
                    step={def.step}
                    placeholder={def.placeholder}
                    className="form-control"
                    value={val}
                    onChange={(e) => handleFieldChange(def.key, e.target.value)}
                    onBlur={() => setTouched((prev) => ({ ...prev, [def.key]: true }))}
                    style={{
                      borderColor: err && isTouched ? '#ef4444' : isFieldValid ? '#22c55e' : undefined,
                      fontWeight: 600,
                    }}
                  />
                ) : (
                  <select
                    id={`field-${def.key}`}
                    className="form-control"
                    value={val}
                    onChange={(e) => handleFieldChange(def.key, e.target.value)}
                    onBlur={() => setTouched((prev) => ({ ...prev, [def.key]: true }))}
                    style={{
                      borderColor: err && isTouched ? '#ef4444' : isFieldValid ? '#22c55e' : undefined,
                      fontWeight: 600,
                    }}
                  >
                    {def.options.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                )}

                <div style={{ fontSize: '0.74rem', color: 'var(--text-light)', marginTop: '0.35rem', lineHeight: 1.35 }}>
                  {def.helpText}
                </div>

                {err && isTouched && (
                  <div style={{ fontSize: '0.74rem', color: '#b91c1c', marginTop: '0.3rem', fontWeight: 600 }}>
                    {err}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
});

export default ClinicalFeatureForm;
