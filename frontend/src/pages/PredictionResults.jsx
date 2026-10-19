import { useState, useEffect, useRef } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { predictionService } from '../services/predictionService';
import { patientService } from '../services/patientService';
import { symptomService } from '../services/symptomService';
import RiskCard from '../components/predictions/RiskCard';
import ClinicalFeatureForm from '../components/predictions/ClinicalFeatureForm';
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
  const [successBanner, setSuccessBanner] = useState(null);

  const featureFormRef = useRef(null);
  const [featureFormState, setFeatureFormState] = useState({
    isValid: false,
    formData: {},
    errors: {},
    missingFields: [],
    readyFeatures: 0,
    totalFeatures: 0,
  });

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

  const [taskReadiness, setTaskReadiness] = useState(null);

  // Load encounter details and prediction history when assessmentId changes
  useEffect(() => {
    if (!assessmentId) return;

    async function loadEncounterData() {
      try {
        const [assess, sym, vit, preds, readiness] = await Promise.all([
          symptomService.getAssessment(assessmentId).catch(() => null),
          symptomService.getSymptoms(assessmentId).catch(() => null),
          symptomService.getVitals(assessmentId).catch(() => null),
          predictionService.getPredictionHistory(assessmentId).catch(() => []),
          predictionService.getTaskReadiness(assessmentId).catch(() => null),
        ]);

        setAssessmentDetails(assess);
        setSymptomsData(sym);
        setVitalsData(vit);
        setPredictions(preds || []);
        setTaskReadiness(readiness);

        // Ensure selected patient is synced with encounter's patient
        if (assess && assess.patient_id) {
          setSelectedPatientId(String(assess.patient_id));
          patientService.listAssessments(assess.patient_id).then((res) => {
            setPatientAssessments(res || []);
          }).catch(() => {});
        }
      } catch (err) {
        setError(err.message || 'Failed to load encounter details.');
      }
    }

    loadEncounterData();
  }, [assessmentId]);

  const handleTaskSelection = (taskId) => {
    setSelectedTask(taskId);
    setUnsupportedWarning(null);

    const isSupported = (
      taskCatalog?.supported_tasks?.some((t) => t.task_id === taskId || t.task_name === taskId) ||
      taskId === 'coronary_artery_disease' ||
      taskId === 'heart_failure_mortality'
    ) && taskId !== 'heart_failure_screening';

    if (!isSupported) {
      const specificMsg =
        taskCatalog?.unsupported_tasks?.[taskId] ||
        (taskId === 'heart_failure_screening'
          ? 'UNSUPPORTED TASK: Heart failure screening in general populations is prohibited. The underlying dataset contains exclusively hospitalized NYHA Class III-IV patients with confirmed heart failure and no non-heart-failure controls. Predicting heart failure occurrence from this dataset is medically invalid.'
          : `The task "${taskId}" is currently not supported by our validated ML pipelines.`);
      setUnsupportedWarning(specificMsg);
    }
  };

  const handleRunInference = async () => {
    if (!assessmentId) {
      setError('Please select an active clinical encounter first.');
      return;
    }

    if (unsupportedWarning || selectedTask === 'heart_failure_screening') {
      setError('Cannot execute inference on unsupported task.');
      return;
    }

    if (!featureFormState.isValid) {
      setError(`Cannot execute inference: ${featureFormState.missingFields.length} required clinical parameters are missing or invalid. Please review and complete the fields highlighted below.`);
      featureFormRef.current?.focusFirstMissing();
      return;
    }

    setIsInferring(true);
    setError(null);
    setSuccessBanner(null);
    try {
      const res = await predictionService.runPrediction(assessmentId, {
        task_name: selectedTask,
        task: selectedTask,
        patient_id: assessmentDetails?.patient_id ? Number(assessmentDetails.patient_id) : selectedPatientId ? Number(selectedPatientId) : undefined,
        assessment_id: Number(assessmentId),
        direct_features: featureFormState.formData,
        explain: true,
        compute_explanations: true,
      });

      // Prepend newly audited prediction record (prevent duplicate in list)
      setPredictions((prev) => [res, ...prev.filter((p) => p.id !== res.id)]);

      // Re-fetch readiness from backend now that lab measurements are persisted
      const updatedReadiness = await predictionService.getTaskReadiness(assessmentId).catch(() => null);
      if (updatedReadiness) {
        setTaskReadiness(updatedReadiness);
      }

      setSuccessBanner({
        task_name: res.task_name,
        model_name: res.model_name,
        model_version: res.model_version,
        predicted_class_label: res.predicted_class_label,
        probability: res.calibrated_probability !== null ? (res.calibrated_probability * 100).toFixed(1) + '%' : null,
        raw_score: res.raw_score,
        target_definition: res.target_definition,
        disclaimer: res.clinical_prototype_disclaimer,
        timestamp: res.created_at,
      });
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
                    Platt-Calibrated Probability
                  </span>
                </div>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '0.5rem', lineHeight: 1.4 }}>
                  Predicts presence of &ge;50% coronary lumen narrowing. Validated on multi-center clinical cohorts.
                </p>
                {taskReadiness?.coronary_artery_disease && (
                  <div style={{
                    fontSize: '0.76rem',
                    marginTop: '0.5rem',
                    color: taskReadiness.coronary_artery_disease.ready ? '#15803d' : '#b45309',
                    fontWeight: 600,
                  }}>
                    {taskReadiness.coronary_artery_disease.ready
                      ? '&check; Input features ready (13/13)'
                      : `Features: ${taskReadiness.coronary_artery_disease.available_features_count}/13 mapped`}
                  </div>
                )}
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
                    backgroundColor: '#fef3c7',
                    color: '#92400e',
                    border: '1px solid #fde68a',
                    padding: '0.2rem 0.5rem',
                    borderRadius: 'var(--radius-pill)',
                  }}>
                    Classifier Confidence Score (Uncalibrated)
                  </span>
                </div>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '0.5rem', lineHeight: 1.4 }}>
                  Predicts follow-up mortality risk (DEATH_EVENT) in diagnosed heart failure patients. Prohibited for screening. Experimental model (N=299).
                </p>
                {taskReadiness?.heart_failure_mortality && (
                  <div style={{
                    fontSize: '0.76rem',
                    marginTop: '0.5rem',
                    color: taskReadiness.heart_failure_mortality.ready ? '#15803d' : '#b45309',
                    fontWeight: 600,
                  }}>
                    {taskReadiness.heart_failure_mortality.ready
                      ? '&check; Input features ready (11/11)'
                      : `Features: ${taskReadiness.heart_failure_mortality.available_features_count}/11 mapped`}
                  </div>
                )}
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
                  General community HF screening model is prohibited. Underlying dataset contains no healthy controls.
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

            {/* Structured Clinical Input & Feature Verification Form */}
            {selectedTask !== 'heart_failure_screening' && (
              <ClinicalFeatureForm
                ref={featureFormRef}
                task={selectedTask}
                patient={assessmentDetails?.patient || patients.find((p) => String(p.id) === String(selectedPatientId)) || null}
                assessmentDetails={assessmentDetails}
                symptomsData={symptomsData}
                vitalsData={vitalsData}
                initialFeatures={taskReadiness?.[selectedTask]?.available_features || {}}
                onChange={(state) => setFeatureFormState(state)}
              />
            )}

            {/* Run Inference Action Control */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
                {!featureFormState.isValid && selectedTask !== 'heart_failure_screening' && (
                  <button
                    type="button"
                    onClick={() => featureFormRef.current?.focusFirstMissing()}
                    className="btn btn-secondary"
                    style={{ fontSize: '0.84rem' }}
                  >
                    Review required inputs &darr;
                  </button>
                )}

                <button
                  type="button"
                  onClick={handleRunInference}
                  disabled={
                    isInferring ||
                    !assessmentId ||
                    Boolean(unsupportedWarning) ||
                    selectedTask === 'heart_failure_screening' ||
                    !featureFormState.isValid
                  }
                  className="btn btn-primary"
                  style={{ minWidth: '220px' }}
                >
                  {isInferring
                    ? 'Executing Inference...'
                    : selectedTask === 'heart_failure_mortality'
                    ? 'Run Mortality Inference \u2192'
                    : 'Run Calibrated Inference \u2192'}
                </button>
              </div>

              {Boolean(unsupportedWarning || selectedTask === 'heart_failure_screening') && (
                <div style={{ fontSize: '0.82rem', color: '#b91c1c', fontWeight: 600, textAlign: 'right' }}>
                  &times; Inference disabled: Selected task is prohibited by clinical validation governance.
                </div>
              )}
              {!assessmentId && (
                <div style={{ fontSize: '0.82rem', color: '#b45309', fontWeight: 600, textAlign: 'right' }}>
                  &times; Inference disabled: Please select an active clinical encounter above.
                </div>
              )}
              {assessmentId && selectedTask !== 'heart_failure_screening' && !featureFormState.isValid && (
                <div style={{ fontSize: '0.84rem', color: '#b91c1c', fontWeight: 600, textAlign: 'right' }}>
                  &times; Inference disabled: {featureFormState.missingFields?.length || 'Required'} clinical inputs are missing or invalid. Please complete the highlighted fields above.
                </div>
              )}
              {assessmentId && selectedTask !== 'heart_failure_screening' && featureFormState.isValid && (
                <div style={{ fontSize: '0.84rem', color: '#15803d', fontWeight: 600, textAlign: 'right' }}>
                  &check; All {featureFormState.totalFeatures} required clinical features verified and ready for execution.
                </div>
              )}
            </div>
          </div>

          {/* New Prediction Success Confirmation Banner */}
          {successBanner && (
            <div
              style={{
                backgroundColor: '#f0fdf4',
                border: '1px solid #86efac',
                borderRadius: 'var(--radius-lg)',
                padding: '1.25rem 1.5rem',
                marginBottom: '2rem',
                boxShadow: '0 2px 4px rgba(0,0,0,0.04)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span className="pill-badge pill-badge-green">
                  &check; ML Inference Generated and Audited
                </span>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-light)' }}>
                  {formatDateTime(successBanner.timestamp)}
                </span>
              </div>
              <h3 style={{ fontSize: '1.25rem', color: '#14532d', marginBottom: '0.25rem' }}>
                {successBanner.predicted_class_label}
              </h3>
              <p style={{ fontSize: '0.86rem', color: '#166534', marginBottom: '0.5rem' }}>
                {successBanner.probability ? (
                  <><strong>Calibrated Probability: </strong>{successBanner.probability}</>
                ) : (
                  <><strong>Classifier Score: </strong>{successBanner.raw_score}</>
                )} &bull; Model: {successBanner.model_name} (v{successBanner.model_version})
              </p>
              <p style={{ fontSize: '0.8rem', color: '#374151', lineHeight: 1.4 }}>
                <strong>Target Definition: </strong>{successBanner.target_definition}
                <br />
                <span style={{ color: 'var(--text-muted)' }}>{successBanner.disclaimer}</span>
              </p>
            </div>
          )}

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
