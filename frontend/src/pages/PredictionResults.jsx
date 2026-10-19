import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { predictionService } from '../services/predictionService';
import { patientService } from '../services/patientService';
import { symptomService } from '../services/symptomService';
import RiskCard from '../components/predictions/RiskCard';
import MedicalDisclaimer from '../components/predictions/MedicalDisclaimer';
import Sidebar from '../components/common/Sidebar';
import Loader from '../components/common/Loader';
import FormError from '../components/forms/FormError';
import { formatBloodPressure, formatDateTime, formatAnginaClassification } from '../utils/formatters';

export default function PredictionResults() {
  const [searchParams] = useSearchParams();
  const [assessmentId, setAssessmentId] = useState(searchParams.get('assessment_id') || '');
  const [patients, setPatients] = useState([]);
  const [selectedPatientId, setSelectedPatientId] = useState('');
  const [patientAssessments, setPatientAssessments] = useState([]);

  const [assessmentDetails, setAssessmentDetails] = useState(null);
  const [symptomsData, setSymptomsData] = useState(null);
  const [vitalsData, setVitalsData] = useState(null);

  const [taskCatalog, setTaskCatalog] = useState(null);
  const [selectedTask, setSelectedTask] = useState('coronary_artery_disease');
  const [predictions, setPredictions] = useState([]);

  const [loading, setLoading] = useState(true);
  const [isInferring, setIsInferring] = useState(false);
  const [error, setError] = useState(null);
  const [unsupportedWarning, setUnsupportedWarning] = useState(null);

  // Initialize patients and catalog
  useEffect(() => {
    async function init() {
      setLoading(true);
      setError(null);
      try {
        const [ptsRes, catalogRes] = await Promise.all([
          patientService.listPatients({ page: 1, per_page: 50 }),
          predictionService.getTaskCatalog().catch(() => null),
        ]);

        const items = ptsRes?.items || [];
        setPatients(items);
        setTaskCatalog(catalogRes);

        if (items.length > 0 && !selectedPatientId) {
          setSelectedPatientId(items[0].id);
          const assessRes = await patientService.listAssessments(items[0].id);
          setPatientAssessments(assessRes || []);
          if (!assessmentId && assessRes?.length > 0) {
            setAssessmentId(assessRes[0].id);
          }
        }
      } catch (err) {
        setError(err.message || 'Failed to initialize prediction module.');
      } finally {
        setLoading(false);
      }
    }

    init();
  }, []);

  const handlePatientChange = async (pId) => {
    setSelectedPatientId(pId);
    try {
      const assessRes = await patientService.listAssessments(pId);
      setPatientAssessments(assessRes || []);
      if (assessRes && assessRes.length > 0) {
        setAssessmentId(assessRes[0].id);
      } else {
        setAssessmentId('');
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch assessments.');
    }
  };

  // Load encounter details and prediction history when assessmentId changes
  useEffect(() => {
    if (!assessmentId) return;

    async function loadEncounterData() {
      try {
        const [assess, sym, vit, preds] = await Promise.all([
          symptomService.getAssessment(assessmentId).catch(() => null),
          symptomService.getSymptoms(assessmentId).catch(() => null),
          symptomService.getVitals(assessmentId).catch(() => null),
          predictionService.getPredictionHistory(assessmentId).catch(() => []),
        ]);

        setAssessmentDetails(assess);
        setSymptomsData(sym);
        setVitalsData(vit);
        setPredictions(preds || []);
      } catch (err) {
        setError(err.message || 'Failed to load encounter details.');
      }
    }

    loadEncounterData();
  }, [assessmentId]);

  const handleTaskSelection = (taskId) => {
    setSelectedTask(taskId);
    setUnsupportedWarning(null);

    const isSupported = taskCatalog?.supported_tasks?.some((t) => t.task_id === taskId);
    if (!isSupported && taskId !== 'coronary_artery_disease' && taskId !== 'heart_failure_mortality') {
      setUnsupportedWarning(
        `The task "${taskId}" is currently not supported by our validated ML pipelines. Our clinical decision support engine prohibits generating fabricated or mock predictions for uncalibrated models.`
      );
    }
  };

  const handleRunInference = async () => {
    if (!assessmentId) {
      setError('Please select an active clinical encounter first.');
      return;
    }

    if (unsupportedWarning) {
      setError('Cannot execute inference on unsupported or uncalibrated task.');
      return;
    }

    setIsInferring(true);
    setError(null);
    try {
      const res = await predictionService.runPrediction(assessmentId, {
        task_name: selectedTask,
        task: selectedTask,
        explain: true,
        compute_explanations: true,
      });

      // Prepend newly audited prediction record
      setPredictions((prev) => [res, ...prev]);
    } catch (err) {
      setError(err.message || 'Inference execution failed.');
    } finally {
      setIsInferring(false);
    }
  };

  const isEmergencyEncounter =
    assessmentDetails?.status === 'flagged_emergency' ||
    assessmentDetails?.emergency_escalation_level === 'EMERGENCY_IMMEDIATE_911';

  return (
    <div className="app-container" style={{ padding: '2.5rem 1rem 4rem' }}>
      <div style={{ display: 'flex', gap: '2rem', alignItems: 'flex-start' }}>
        <Sidebar assessmentId={assessmentId} />

        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '2rem' }}>
            <div>
              <span className="pill-badge" style={{ marginBottom: '0.4rem' }}>
                <span className="pill-dot" /> Phase 4: Machine Learning Inference
              </span>
              <h2 style={{ fontSize: '2.2rem', letterSpacing: '-0.03em' }}>
                Cardiovascular Condition-Risk Estimates
              </h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem' }}>
                Calibrated statistical risk prediction and non-causal feature attribution.
              </p>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <Link to="/test-recommendations" className="btn btn-secondary">
                View Recommendations
              </Link>
              <Link to="/assessment-history" className="btn btn-secondary">
                Full Audit History
              </Link>
            </div>
          </div>

          {error && <FormError message={error} onRetry={() => setError(null)} />}

          {/* Emergency Safety Primacy Notice */}
          {isEmergencyEncounter && (
            <div className="emergency-alert" style={{ marginBottom: '2rem' }}>
              <div className="emergency-alert-icon">&#9888;</div>
              <div className="emergency-alert-content">
                <h4>EMERGENCY SAFETY PRIMACY NOTICE</h4>
                <p>
                  This patient encounter was flagged with active acute symptoms requiring immediate medical evaluation.
                  <strong> Clinical rule primacy mandates that statistical model scores must NEVER be used to reassure or down-triage a patient presenting with concerning or emergency symptoms.</strong>
                </p>
              </div>
            </div>
          )}

          {/* Context Selector Card */}
          <div className="clean-card" style={{ marginBottom: '2rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
              <div>
                <label className="form-label" htmlFor="patient-select">
                  Select Patient
                </label>
                <select
                  id="patient-select"
                  className="form-control"
                  value={selectedPatientId}
                  onChange={(e) => handlePatientChange(e.target.value)}
                >
                  {patients.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.patient_code} ({p.age}y, {p.sex})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="form-label" htmlFor="encounter-select">
                  Select Encounter / Assessment
                </label>
                <select
                  id="encounter-select"
                  className="form-control"
                  value={assessmentId}
                  onChange={(e) => setAssessmentId(e.target.value)}
                  disabled={patientAssessments.length === 0}
                >
                  {patientAssessments.length === 0 ? (
                    <option value="">No encounters recorded</option>
                  ) : (
                    patientAssessments.map((a) => (
                      <option key={a.id} value={a.id}>
                        Encounter #{a.id} ({formatDateTime(a.assessment_date)})
                      </option>
                    ))
                  )}
                </select>
              </div>
            </div>
          </div>

          {/* 4-Way Modality Distinction Panel */}
          <div className="clean-card" style={{ marginBottom: '2rem' }}>
            <h3 style={{ fontSize: '1.2rem', marginBottom: '0.4rem' }}>
              Clinical Evidence &amp; Modality Categorization
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.86rem', marginBottom: '1.25rem' }}>
              Rigorous separation between patient self-reports, measured clinical observations, and statistical predictions.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
              {/* Subjective */}
              <div style={{ padding: '1rem', borderRadius: 'var(--radius-md)', backgroundColor: '#fdf4ff', border: '1px solid #f0abfc' }}>
                <span className="modality-tag modality-subjective" style={{ marginBottom: '0.5rem', display: 'inline-block' }}>
                  1. Subjective Self-Reports
                </span>
                <p style={{ fontSize: '0.82rem', color: '#701a75', lineHeight: 1.4 }}>
                  <strong>Angina: </strong>{formatAnginaClassification(symptomsData?.angina_classification)}
                  <br />
                  <strong>Dyspnea: </strong>{symptomsData?.dyspnea ? 'Reported' : 'None'}
                  <br />
                  <strong>Palpitations: </strong>{symptomsData?.palpitations ? 'Reported' : 'None'}
                </p>
              </div>

              {/* Objective */}
              <div style={{ padding: '1rem', borderRadius: 'var(--radius-md)', backgroundColor: '#eff6ff', border: '1px solid #93c5fd' }}>
                <span className="modality-tag modality-objective" style={{ marginBottom: '0.5rem', display: 'inline-block' }}>
                  2. Measured Physiological Values
                </span>
                <p style={{ fontSize: '0.82rem', color: '#1e3a8a', lineHeight: 1.4 }}>
                  <strong>BP: </strong>{formatBloodPressure(vitalsData?.systolic_bp, vitalsData?.diastolic_bp)}
                  <br />
                  <strong>Heart Rate: </strong>{vitalsData?.resting_heart_rate ? `${vitalsData.resting_heart_rate} bpm` : 'Not recorded'}
                  <br />
                  <strong>BMI: </strong>{vitalsData?.bmi ? vitalsData.bmi.toFixed(1) : 'Not calculated'}
                </p>
              </div>

              {/* Model Output */}
              <div style={{ padding: '1rem', borderRadius: 'var(--radius-md)', backgroundColor: '#fff7ed', border: '1px solid #fdba74' }}>
                <span className="modality-tag modality-prediction" style={{ marginBottom: '0.5rem', display: 'inline-block' }}>
                  3. Algorithmic Model Outputs
                </span>
                <p style={{ fontSize: '0.82rem', color: '#7c2d12', lineHeight: 1.4 }}>
                  Audited ML pipelines with Platt / isotonic probability calibration and feature attribution snapshots.
                </p>
              </div>

              {/* Clinical CDS */}
              <div style={{ padding: '1rem', borderRadius: 'var(--radius-md)', backgroundColor: '#f0fdf4', border: '1px solid #86efac' }}>
                <span className="modality-tag modality-recommendation" style={{ marginBottom: '0.5rem', display: 'inline-block' }}>
                  4. Clinical Recommendations
                </span>
                <p style={{ fontSize: '0.82rem', color: '#14532d', lineHeight: 1.4 }}>
                  AHA / ACC / ESC guideline-directed diagnostic pathways and emergency referral protocols.
                </p>
              </div>
            </div>
          </div>

          {/* Model Inference Runner Card */}
          <div className="clean-card" style={{ marginBottom: '2.5rem' }}>
            <h3 style={{ fontSize: '1.25rem', marginBottom: '0.4rem' }}>
              Execute Machine Learning Inference
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', marginBottom: '1.5rem' }}>
              Select a validated clinical predictive modeling pipeline to evaluate this encounter's feature vectors.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
              {/* Task Options */}
              <div
                onClick={() => handleTaskSelection('coronary_artery_disease')}
                style={{
                  padding: '1.25rem',
                  borderRadius: 'var(--radius-lg)',
                  border: `2px solid ${selectedTask === 'coronary_artery_disease' ? 'var(--primary-red)' : '#e5e7eb'}`,
                  backgroundColor: selectedTask === 'coronary_artery_disease' ? 'var(--primary-red-subtle)' : '#ffffff',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 700, fontSize: '1.05rem', color: 'var(--text-main)' }}>
                    Coronary Artery Disease (CAD)
                  </span>
                  <span style={{
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    backgroundColor: '#dcfce7',
                    color: '#15803d',
                    padding: '0.2rem 0.5rem',
                    borderRadius: 'var(--radius-pill)',
                  }}>
                    Calibrated &bull; Validated
                  </span>
                </div>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '0.5rem', lineHeight: 1.4 }}>
                  Predicts presence of &ge;50% coronary lumen narrowing. Validated on multi-center clinical cohorts.
                </p>
              </div>

              <div
                onClick={() => handleTaskSelection('heart_failure_mortality')}
                style={{
                  padding: '1.25rem',
                  borderRadius: 'var(--radius-lg)',
                  border: `2px solid ${selectedTask === 'heart_failure_mortality' ? 'var(--primary-red)' : '#e5e7eb'}`,
                  backgroundColor: selectedTask === 'heart_failure_mortality' ? 'var(--primary-red-subtle)' : '#ffffff',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 700, fontSize: '1.05rem', color: 'var(--text-main)' }}>
                    Heart Failure Survival (HF)
                  </span>
                  <span style={{
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    backgroundColor: '#dcfce7',
                    color: '#15803d',
                    padding: '0.2rem 0.5rem',
                    borderRadius: 'var(--radius-pill)',
                  }}>
                    Calibrated &bull; Validated
                  </span>
                </div>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '0.5rem', lineHeight: 1.4 }}>
                  Predicts in-hospital or 30-day mortality risk in clinical heart failure presentations.
                </p>
              </div>

              {/* Unsupported Model Example to demonstrate safe validation */}
              <div
                onClick={() => handleTaskSelection('heart_failure_screening')}
                style={{
                  padding: '1.25rem',
                  borderRadius: 'var(--radius-lg)',
                  border: `2px dashed ${selectedTask === 'heart_failure_screening' ? '#94a3b8' : '#e2e8f0'}`,
                  backgroundColor: '#f8fafc',
                  cursor: 'pointer',
                  opacity: 0.85,
                  transition: 'all 0.15s ease',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 700, fontSize: '1.05rem', color: '#64748b' }}>
                    Heart Failure Screening (General)
                  </span>
                  <span style={{
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    backgroundColor: '#fee2e2',
                    color: '#991b1b',
                    padding: '0.2rem 0.5rem',
                    borderRadius: 'var(--radius-pill)',
                  }}>
                    Unsupported Task
                  </span>
                </div>
                <p style={{ fontSize: '0.82rem', color: '#64748b', marginTop: '0.5rem', lineHeight: 1.4 }}>
                  General community HF screening model is under clinical trial and is not authorized for decision support.
                </p>
              </div>
            </div>

            {unsupportedWarning && (
              <div style={{
                backgroundColor: '#fff1f2',
                border: '1px solid #fecdd3',
                color: '#9f1239',
                padding: '0.85rem 1.25rem',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.88rem',
                marginBottom: '1.5rem',
                lineHeight: 1.45,
              }}>
                <strong>Model Policy Constraint: </strong>{unsupportedWarning}
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
              <button
                type="button"
                onClick={handleRunInference}
                disabled={isInferring || !assessmentId || Boolean(unsupportedWarning)}
                className="btn btn-primary"
                style={{ minWidth: '180px' }}
              >
                {isInferring ? 'Executing Inference...' : 'Run Calibrated Inference \u2192'}
              </button>
            </div>
          </div>

          {/* Results Section */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h3 style={{ fontSize: '1.4rem' }}>
                Encounter Prediction Audit Log ({predictions.length})
              </h3>
              <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                Audited &bull; Immutable History
              </span>
            </div>

            {loading ? (
              <Loader message="Loading prediction audit history..." />
            ) : predictions.length === 0 ? (
              <div className="clean-card" style={{ textAlign: 'center', padding: '3rem 1.5rem', color: 'var(--text-muted)' }}>
                <p style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>
                  No predictive model evaluations have been run for Encounter #{assessmentId} yet.
                </p>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-light)' }}>
                  Click <strong>Run Calibrated Inference</strong> above to execute a validated pipeline.
                </p>
              </div>
            ) : (
              <div>
                {predictions.map((pred) => (
                  <RiskCard key={pred.id} prediction={pred} />
                ))}
              </div>
            )}
          </div>

          <MedicalDisclaimer />
        </div>
      </div>
    </div>
  );
}
