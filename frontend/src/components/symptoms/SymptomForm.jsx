import { useState } from 'react';
import SymptomQuestion from './SymptomQuestion';
import SegmentedControl from '../forms/SegmentedControl';
import { SYMPTOM_DEFINITIONS } from '../../utils/constants';

export default function SymptomForm({ initialData = {}, onSave, isSaving = false }) {
  const [selectedSymptoms, setSelectedSymptoms] = useState(() => {
    const map = {};
    if (initialData.chest_pain) map.chest_pain = true;
    if (initialData.dyspnea) map.dyspnea = true;
    if (initialData.palpitations) map.palpitations = true;
    if (initialData.syncope) map.syncope = true;
    if (initialData.fatigue) map.fatigue = true;
    if (initialData.bilateral_leg_edema) map.bilateral_leg_edema = true;
    return map;
  });

  // Detailed Diamond-Forrester & congestive qualifiers.
  // CRITICAL CLINICAL FIX: Never default Diamond-Forrester criteria to true.
  // Criteria must only be true if explicitly confirmed by the patient/clinician.
  const [qualifiers, setQualifiers] = useState({
    substernal_location: initialData.substernal_location ?? null,
    exertional_provocation: initialData.exertional_provocation ?? null,
    relieved_by_rest: initialData.relieved_by_rest ?? null,
    chest_pain_quality: initialData.chest_pain_quality || 'pressure',
    chest_pain_radiation: initialData.chest_pain_radiation || 'none',
    dyspnea_at_rest: initialData.dyspnea_at_rest ?? null,
    orthopnea: initialData.orthopnea ?? null,
    paroxysmal_nocturnal_dyspnea: initialData.paroxysmal_nocturnal_dyspnea ?? null,
  });

  const toggleSymptom = (id) => {
    setSelectedSymptoms((prev) => {
      const nextVal = !prev[id];
      const updated = { ...prev, [id]: nextVal };
      // If chest pain is unchecked, reset qualifiers so stale values do not leak
      if (id === 'chest_pain' && !nextVal) {
        setQualifiers((q) => ({
          ...q,
          substernal_location: null,
          exertional_provocation: null,
          relieved_by_rest: null,
        }));
      }
      return updated;
    });
  };

  const handleQualifierChange = (field, value) => {
    setQualifiers((prev) => ({ ...prev, [field]: value }));
  };

  const selectedCount = Object.values(selectedSymptoms).filter(Boolean).length;

  const handleSubmit = (e) => {
    e.preventDefault();

    const payload = {
      chest_pain: Boolean(selectedSymptoms.chest_pain),
      dyspnea: Boolean(selectedSymptoms.dyspnea),
      palpitations: Boolean(selectedSymptoms.palpitations),
      syncope: Boolean(selectedSymptoms.syncope),
      diaphoresis: Boolean(selectedSymptoms.chest_pain && qualifiers.chest_pain_quality === 'crushing'),
      bilateral_leg_edema: Boolean(selectedSymptoms.bilateral_leg_edema),
    };

    if (selectedSymptoms.chest_pain) {
      // Only treat criteria as positive if explicitly chosen as true
      payload.substernal_location = qualifiers.substernal_location === true;
      payload.exertional_provocation = qualifiers.exertional_provocation === true;
      payload.relieved_by_rest = qualifiers.relieved_by_rest === true;
      payload.chest_pain_quality = qualifiers.chest_pain_quality;
      payload.chest_pain_radiation = qualifiers.chest_pain_radiation;
    } else {
      payload.substernal_location = false;
      payload.exertional_provocation = false;
      payload.relieved_by_rest = false;
    }

    if (selectedSymptoms.dyspnea) {
      payload.dyspnea_at_rest = qualifiers.dyspnea_at_rest === true;
      payload.orthopnea = qualifiers.orthopnea === true;
      payload.paroxysmal_nocturnal_dyspnea = qualifiers.paroxysmal_nocturnal_dyspnea === true;
    }

    onSave(payload);
  };

  return (
    <form onSubmit={handleSubmit} style={{ width: '100%' }}>
      {/* 6 Grid Symptom Cards with responsive columns */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: '1.25rem',
          marginBottom: '2rem',
        }}
      >
        {SYMPTOM_DEFINITIONS.map((sym) => (
          <SymptomQuestion
            key={sym.id}
            id={sym.id}
            label={sym.label}
            description={sym.description}
            iconType={sym.iconType}
            selected={Boolean(selectedSymptoms[sym.id])}
            onToggle={toggleSymptom}
          />
        ))}
      </div>

      {/* Contextual Diamond-Forrester Angina Questions if Chest Discomfort Selected */}
      {selectedSymptoms.chest_pain && (
        <div
          className="clean-card animate-fade-in"
          style={{
            backgroundColor: '#ffffff',
            border: '1px solid #fee2e2',
            marginBottom: '2rem',
            padding: '1.75rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
            <span className="pill-badge">Clinical Characterization</span>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>
              Diamond-Forrester / AHA 2021 Angina Criteria
            </span>
          </div>
          <h4 style={{ fontSize: '1.2rem', marginBottom: '0.4rem', color: 'var(--text-main)' }}>
            Chest Discomfort Clinical Evaluation
          </h4>
          <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginBottom: '1.5rem', lineHeight: 1.45 }}>
            Characterize the nature, triggers, and relief of discomfort to determine whether presentation reflects typical angina, atypical angina, or non-anginal discomfort.
          </p>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
              gap: '1.5rem',
            }}
          >
            {/* Criterion 1: Substernal */}
            <SegmentedControl
              id="substernal_location"
              name="substernal_location"
              label="1. Substernal Location"
              description="Discomfort located central/behind breastbone (vs. localized peripheral/chest wall)"
              options={[
                { value: true, label: 'Yes (Substernal)' },
                { value: false, label: 'No (Peripheral / Lateral)' },
              ]}
              value={qualifiers.substernal_location}
              onChange={(val) => handleQualifierChange('substernal_location', val)}
            />

            {/* Criterion 2: Exertional Provocation */}
            <SegmentedControl
              id="exertional_provocation"
              name="exertional_provocation"
              label="2. Provoked by Exertion / Stress"
              description="Brought on by physical walking, stairs, cold weather, or emotional distress"
              options={[
                { value: true, label: 'Yes (Provoked)' },
                { value: false, label: 'No (Occurs at Rest)' },
              ]}
              value={qualifiers.exertional_provocation}
              onChange={(val) => handleQualifierChange('exertional_provocation', val)}
            />

            {/* Criterion 3: Relieved by Rest / Nitro */}
            <SegmentedControl
              id="relieved_by_rest"
              name="relieved_by_rest"
              label="3. Relieved by Rest or Nitroglycerin"
              description="Subsides within 5 to 10 minutes of stopping activity or sublingual NTG"
              options={[
                { value: true, label: 'Yes (Relieved < 10m)' },
                { value: false, label: 'No (Persistent / No Relief)' },
              ]}
              value={qualifiers.relieved_by_rest}
              onChange={(val) => handleQualifierChange('relieved_by_rest', val)}
            />

            {/* Discomfort Quality */}
            <div className="form-group" style={{ marginBottom: '1.25rem' }}>
              <label htmlFor="chest_pain_quality" className="form-label" style={{ fontWeight: 700, fontSize: '0.88rem' }}>
                Discomfort Sensation Quality
              </label>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.4rem' }}>
                Primary descriptive character of the sensation
              </span>
              <select
                id="chest_pain_quality"
                value={qualifiers.chest_pain_quality}
                onChange={(e) => handleQualifierChange('chest_pain_quality', e.target.value)}
                className="form-control"
                style={{ height: '42px' }}
              >
                <option value="pressure">Heaviness / Pressure / Tightness (Ischemic type)</option>
                <option value="crushing">Crushing / Severe Squeezing (High acuity)</option>
                <option value="sharp">Sharp / Pleuritic / Stabbing (Musculoskeletal/respiratory type)</option>
                <option value="burning">Burning / Indigestion-like (Atypical/GI type)</option>
              </select>
            </div>

            {/* Radiation */}
            <div className="form-group" style={{ marginBottom: '1.25rem' }}>
              <label htmlFor="chest_pain_radiation" className="form-label" style={{ fontWeight: 700, fontSize: '0.88rem' }}>
                Pain Radiation Pattern
              </label>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.4rem' }}>
                Anatomical extension beyond the chest
              </span>
              <select
                id="chest_pain_radiation"
                value={qualifiers.chest_pain_radiation}
                onChange={(e) => handleQualifierChange('chest_pain_radiation', e.target.value)}
                className="form-control"
                style={{ height: '42px' }}
              >
                <option value="none">No Radiation (Confined to chest)</option>
                <option value="left arm">Left Arm / Shoulder</option>
                <option value="jaw">Neck / Jaw / Teeth</option>
                <option value="back">Interscapular / Upper Back</option>
                <option value="both arms">Both Arms</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Contextual Heart Failure Questions if Breathlessness Selected */}
      {selectedSymptoms.dyspnea && (
        <div
          className="clean-card animate-fade-in"
          style={{
            backgroundColor: '#ffffff',
            border: '1px solid #d1fae5',
            marginBottom: '2rem',
            padding: '1.75rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
            <span className="pill-badge pill-badge-green">Congestive Signs</span>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>
              ESC 2021 Heart Failure Signs
            </span>
          </div>
          <h4 style={{ fontSize: '1.2rem', marginBottom: '0.4rem', color: 'var(--text-main)' }}>
            Respiratory &amp; Congestive Details
          </h4>
          <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginBottom: '1.5rem', lineHeight: 1.45 }}>
            Specific cardinal features distinguishing cardiac congestive pulmonary congestion from non-cardiac dyspnea.
          </p>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
              gap: '1.5rem',
            }}
          >
            <SegmentedControl
              id="dyspnea_at_rest"
              name="dyspnea_at_rest"
              label="Dyspnea at Rest"
              description="Shortness of breath occurs even while sitting or lying still without exertion"
              options={[
                { value: true, label: 'Yes (At Rest)' },
                { value: false, label: 'No (With Exertion Only)' },
              ]}
              value={qualifiers.dyspnea_at_rest}
              onChange={(val) => handleQualifierChange('dyspnea_at_rest', val)}
            />

            <SegmentedControl
              id="orthopnea"
              name="orthopnea"
              label="Orthopnea (Positional)"
              description="Must sleep propped up on 2 or more pillows to avoid breathless discomfort"
              options={[
                { value: true, label: 'Yes (Need Pillows)' },
                { value: false, label: 'No (Sleeps Flat)' },
              ]}
              value={qualifiers.orthopnea}
              onChange={(val) => handleQualifierChange('orthopnea', val)}
            />

            <SegmentedControl
              id="paroxysmal_nocturnal_dyspnea"
              name="paroxysmal_nocturnal_dyspnea"
              label="Paroxysmal Nocturnal Dyspnea (PND)"
              description="Wakes abruptly from sleep gasping for air 1–2 hours after lying down"
              options={[
                { value: true, label: 'Yes (Wakes Gasping)' },
                { value: false, label: 'No' },
              ]}
              value={qualifiers.paroxysmal_nocturnal_dyspnea}
              onChange={(val) => handleQualifierChange('paroxysmal_nocturnal_dyspnea', val)}
            />
          </div>
        </div>
      )}

      {/* Bottom Sticky Action Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#ffffff',
          border: '1px solid var(--border-light)',
          borderRadius: 'var(--radius-xl)',
          padding: '1.25rem 2rem',
          boxShadow: '0 10px 30px rgba(0, 0, 0, 0.04)',
          margin: '2rem 0',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              backgroundColor: selectedCount > 0 ? 'var(--primary-red-subtle)' : '#f3f4f6',
              color: selectedCount > 0 ? 'var(--primary-red)' : 'var(--text-muted)',
              fontWeight: 800,
              fontSize: '0.95rem',
            }}
          >
            {selectedCount}
          </span>
          <span style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '1rem' }}>
            symptom{selectedCount !== 1 ? 's' : ''} reported
          </span>
        </div>

        <button
          type="submit"
          disabled={isSaving}
          className="btn btn-primary btn-lg"
          style={{
            padding: '0.85rem 2.2rem',
            boxShadow: '0 6px 20px rgba(230, 46, 61, 0.35)',
          }}
        >
          {isSaving ? 'Saving Symptoms...' : 'Continue to Vital Signs'} &rarr;
        </button>
      </div>

      {/* Prominent Emergency Notice Banner */}
      <div className="emergency-alert-banner">
        <svg
          className="emergency-icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
        <div style={{ fontSize: '0.92rem', lineHeight: '1.5' }}>
          <strong>Emergency notice: </strong>
          If you have severe or crushing chest pressure, shortness of breath at rest, fainting, or acute pain radiating to the jaw/arm, activate emergency medical services (call 911) immediately. Do not wait for an online screening.
        </div>
      </div>
    </form>
  );
}
