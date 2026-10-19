import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { patientService } from '../services/patientService';
import { symptomService } from '../services/symptomService';
import SymptomForm from '../components/symptoms/SymptomForm';
import VitalSignsForm from '../components/reports/VitalSignsForm';
import Sidebar from '../components/common/Sidebar';
import Loader from '../components/common/Loader';
import FormError from '../components/forms/FormError';

export default function SymptomAssessment() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [step, setStep] = useState('symptoms'); // 'symptoms' | 'vitals'
  const [patients, setPatients] = useState([]);
  const [selectedPatientId, setSelectedPatientId] = useState(searchParams.get('patient_id') || '');
  const [assessmentId, setAssessmentId] = useState(searchParams.get('assessment_id') || null);
  const [loading, setLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function init() {
      setLoading(true);
      setError(null);
      try {
        const res = await patientService.listPatients({ page: 1, per_page: 50 });
        const items = res?.items || [];
        setPatients(items);

        if (!selectedPatientId && items.length > 0) {
          setSelectedPatientId(items[0].id);
        }
      } catch (err) {
        setError(err.message || 'Failed to initialize screening session.');
      } finally {
        setLoading(false);
      }
    }

    init();
  }, []);

  const ensureAssessment = async () => {
    if (assessmentId) return assessmentId;
    if (!selectedPatientId) {
      throw new Error('Please select or create a patient before submitting screening data.');
    }

    const created = await patientService.createAssessment(selectedPatientId, {
      reason_for_visit: 'Guided Cardiovascular Symptom Screening',
    });
    setAssessmentId(created.id);
    return created.id;
  };

  const handleSaveSymptoms = async (symptomsPayload) => {
    setIsSaving(true);
    setError(null);
    try {
      const aId = await ensureAssessment();
      await symptomService.saveSymptoms(aId, symptomsPayload);
      setStep('vitals');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err) {
      setError(err.message || 'Failed to record symptoms.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveVitals = async (vitalsPayload) => {
    setIsSaving(true);
    setError(null);
    try {
      const aId = await ensureAssessment();
      await symptomService.saveVitals(aId, vitalsPayload);
      // Proceed to Test Recommendations with assessment context
      navigate(`/test-recommendations?assessment_id=${aId}`);
    } catch (err) {
      setError(err.message || 'Failed to save vital signs.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="app-container" style={{ padding: '2.5rem 1rem 4rem' }}>
      <div style={{ display: 'flex', gap: '2rem', alignItems: 'flex-start' }}>
        <Sidebar assessmentId={assessmentId} patientId={selectedPatientId} />

        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Header */}
          <div style={{ marginBottom: '2rem' }}>
            <span className="pill-badge" style={{ marginBottom: '0.4rem' }}>
              <span className="pill-dot" /> Phase 1: Guided Intake
            </span>
            <h2 style={{ fontSize: '2.2rem', letterSpacing: '-0.03em' }}>
              Cardiovascular Screening Assessment
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem' }}>
              Step {step === 'symptoms' ? '1 of 2: Symptom Evaluation' : '2 of 2: Objective Vital Signs'}
            </p>
          </div>

          {error && <FormError message={error} onRetry={() => setError(null)} />}

          {loading ? (
            <Loader message="Preparing clinical questionnaire..." />
          ) : (
            <>
              {/* Patient Selector Strip */}
              <div className="clean-card" style={{ marginBottom: '2rem', padding: '1.25rem 1.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
                  <div>
                    <label htmlFor="patient_select" style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main)' }}>
                      Active Patient Profile:
                    </label>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      Screening encounter will be associated with this record
                    </div>
                  </div>

                  <select
                    id="patient_select"
                    value={selectedPatientId}
                    onChange={(e) => setSelectedPatientId(e.target.value)}
                    className="form-control"
                    style={{ maxWidth: '300px' }}
                  >
                    {patients.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.patient_code} (Age {p.age}, {p.sex})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Progress Steps Tabs */}
              <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
                <button
                  type="button"
                  onClick={() => setStep('symptoms')}
                  className={`btn ${step === 'symptoms' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ flex: 1 }}
                >
                  1. Symptom Check-in
                </button>
                <button
                  type="button"
                  onClick={() => setStep('vitals')}
                  className={`btn ${step === 'vitals' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ flex: 1 }}
                >
                  2. Vital Signs &amp; Vitals
                </button>
              </div>

              {step === 'symptoms' ? (
                <SymptomForm
                  onSave={handleSaveSymptoms}
                  isSaving={isSaving}
                />
              ) : (
                <VitalSignsForm
                  onSave={handleSaveVitals}
                  isSaving={isSaving}
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
