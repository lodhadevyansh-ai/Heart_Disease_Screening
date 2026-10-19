import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { patientService } from '../services/patientService';
import { predictionService } from '../services/predictionService';
import Sidebar from '../components/common/Sidebar';
import Loader from '../components/common/Loader';
import FormError from '../components/forms/FormError';
import MedicalDisclaimer from '../components/predictions/MedicalDisclaimer';
import { formatDateTime } from '../utils/formatters';

export default function Dashboard() {
  const { user } = useAuth();

  const [patients, setPatients] = useState([]);
  const [selectedPatientId, setSelectedPatientId] = useState(null);
  const [assessments, setAssessments] = useState([]);
  const [taskCatalog, setTaskCatalog] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const [ptsRes, tasksRes] = await Promise.all([
          patientService.listPatients({ page: 1, per_page: 10 }),
          predictionService.getTaskCatalog().catch(() => null),
        ]);

        const pts = ptsRes?.items || [];
        setPatients(pts);
        setTaskCatalog(tasksRes);

        if (pts.length > 0) {
          const firstId = pts[0].id;
          setSelectedPatientId(firstId);
          const assessRes = await patientService.listAssessments(firstId);
          setAssessments(assessRes || []);
        }
      } catch (err) {
        setError(err.message || 'Failed to load clinical dashboard.');
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  const handlePatientSelect = async (patientId) => {
    setSelectedPatientId(patientId);
    try {
      const assessRes = await patientService.listAssessments(patientId);
      setAssessments(assessRes || []);
    } catch (err) {
      setError(err.message || 'Failed to load patient assessments.');
    }
  };

  const selectedPatient = patients.find((p) => p.id === selectedPatientId);

  return (
    <div className="app-container" style={{ padding: '2.5rem 1rem 4rem' }}>
      <div style={{ display: 'flex', gap: '2rem', alignItems: 'flex-start' }}>
        <Sidebar />

        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Welcome Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '2rem' }}>
            <div>
              <span className="pill-badge" style={{ marginBottom: '0.4rem' }}>
                <span className="pill-dot" /> Clinical Overview
              </span>
              <h2 style={{ fontSize: '2rem', color: 'var(--text-main)', letterSpacing: '-0.02em' }}>
                Welcome, {user?.name || user?.username || 'Clinician'}
              </h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem' }}>
                Role: <strong style={{ color: 'var(--primary-red)', textTransform: 'capitalize' }}>{user?.role}</strong> &bull; Cardiovascular Decision Support System
              </p>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <Link to="/patient-profile" className="btn btn-secondary">
                + New Patient
              </Link>
              <Link to="/symptom-assessment" className="btn btn-primary">
                Start Screening &rarr;
              </Link>
            </div>
          </div>

          {error && <FormError message={error} onRetry={() => window.location.reload()} />}

          {/* Quick Metrics Grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '1.25rem',
            marginBottom: '2rem',
          }}>
            <div className="clean-card" style={{ padding: '1.25rem 1.5rem' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                Total Patients
              </div>
              <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '0.2rem' }}>
                {patients.length}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--accent-green)', marginTop: '0.2rem' }}>
                &bull; HIPAA De-identified
              </div>
            </div>

            <div className="clean-card" style={{ padding: '1.25rem 1.5rem' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                Active Encounters
              </div>
              <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '0.2rem' }}>
                {assessments.length}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                For active patient
              </div>
            </div>

            <div className="clean-card" style={{ padding: '1.25rem 1.5rem' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                Supported ML Models
              </div>
              <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '0.2rem' }}>
                {taskCatalog?.supported_tasks?.length || 2}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                CAD &bull; HF Mortality
              </div>
            </div>

            <div className="clean-card" style={{ padding: '1.25rem 1.5rem', borderLeft: '4px solid var(--primary-red)' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                Emergency Rule Engine
              </div>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--primary-red)', marginTop: '0.4rem' }}>
                Active &bull; Level 1
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--primary-red)', marginTop: '0.2rem' }}>
                Emergency Primacy Enforced
              </div>
            </div>
          </div>

          {loading ? (
            <Loader message="Loading patient records..." />
          ) : (
            <>
              {/* Patient Selector */}
              <div className="clean-card" style={{ marginBottom: '2rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <h3 style={{ fontSize: '1.25rem' }}>Select Clinical Profile</h3>
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    {patients.length} available record{patients.length !== 1 ? 's' : ''}
                  </span>
                </div>

                {patients.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '3rem 1.5rem', color: 'var(--text-muted)' }}>
                    <div style={{
                      width: '56px',
                      height: '56px',
                      borderRadius: '50%',
                      backgroundColor: '#fee2e2',
                      color: 'var(--primary-red)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      margin: '0 auto 1rem',
                    }}>
                      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
                        <circle cx="12" cy="7" r="4" />
                      </svg>
                    </div>
                    <h4 style={{ fontSize: '1.2rem', color: 'var(--text-main)', marginBottom: '0.4rem' }}>
                      No patients registered yet
                    </h4>
                    <p style={{ fontSize: '0.88rem', maxWidth: '440px', margin: '0 auto 1.5rem', color: 'var(--text-muted)' }}>
                      Get started with your clinical decision workflow by creating a de-identified patient record and beginning a screening intake.
                    </p>
                    <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', flexWrap: 'wrap' }}>
                      <Link to="/patient-profile" className="btn btn-primary">
                        + Create First Patient
                      </Link>
                      <Link to="/symptom-assessment" className="btn btn-secondary">
                        Start Your First Screening &rarr;
                      </Link>
                    </div>
                  </div>
                ) : (
                  <div style={{ display: 'flex', gap: '0.75rem', overflowX: 'auto', paddingBottom: '0.5rem' }}>
                    {patients.map((pt) => {
                      const isSelected = pt.id === selectedPatientId;
                      return (
                        <button
                          key={pt.id}
                          type="button"
                          onClick={() => handlePatientSelect(pt.id)}
                          style={{
                            padding: '0.75rem 1.25rem',
                            borderRadius: 'var(--radius-lg)',
                            border: `1px solid ${isSelected ? 'var(--primary-red)' : '#e5e7eb'}`,
                            backgroundColor: isSelected ? 'var(--primary-red-subtle)' : '#ffffff',
                            cursor: 'pointer',
                            textAlign: 'left',
                            minWidth: '180px',
                            transition: 'all 0.15s ease',
                          }}
                        >
                          <div style={{ fontSize: '0.95rem', fontWeight: 700, color: isSelected ? 'var(--primary-red)' : 'var(--text-main)' }}>
                            {pt.patient_code}
                          </div>
                          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                            {pt.age}y &bull; {pt.sex}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Patient Assessments History */}
              {selectedPatient && (
                <div className="clean-card" style={{ marginBottom: '2rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
                    <div>
                      <h3 style={{ fontSize: '1.25rem' }}>
                        Encounters for {selectedPatient.patient_code}
                      </h3>
                      <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                        Chronological clinical assessment history
                      </p>
                    </div>

                    <Link
                      to={`/symptom-assessment?patient_id=${selectedPatient.id}`}
                      className="btn btn-primary btn-sm"
                    >
                      + New Encounter
                    </Link>
                  </div>

                  {assessments.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '2.5rem 1rem', color: 'var(--text-muted)' }}>
                      No assessment encounters recorded for this patient yet. Click <strong>+ New Encounter</strong> to begin.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                      {assessments.map((a) => {
                        const isEmergency = a.status === 'flagged_emergency' || a.emergency_escalation_level === 'EMERGENCY_IMMEDIATE_911';
                        return (
                          <div
                            key={a.id}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              padding: '1rem 1.25rem',
                              borderRadius: 'var(--radius-md)',
                              backgroundColor: isEmergency ? '#fff5f5' : '#fafafa',
                              border: `1px solid ${isEmergency ? '#fecaca' : '#e5e7eb'}`,
                            }}
                          >
                            <div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                                <span style={{ fontWeight: 700, color: 'var(--text-main)', fontSize: '0.95rem' }}>
                                  Encounter #{a.id} &bull; {a.reason_for_visit || 'Routine Evaluation'}
                                </span>
                                {isEmergency && (
                                  <span style={{
                                    backgroundColor: '#fee2e2',
                                    color: '#b91c1c',
                                    border: '1px solid #fca5a5',
                                    padding: '0.2rem 0.6rem',
                                    borderRadius: 'var(--radius-pill)',
                                    fontSize: '0.72rem',
                                    fontWeight: 800,
                                  }}>
                                    EMERGENCY ESCALATED
                                  </span>
                                )}
                              </div>
                              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                                Recorded: {formatDateTime(a.assessment_date)} &bull; Status: {a.status}
                              </div>
                            </div>

                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                              <Link
                                to={`/test-recommendations?assessment_id=${a.id}`}
                                className="btn btn-secondary btn-sm"
                              >
                                Recommendations
                              </Link>
                              <Link
                                to={`/prediction-results?assessment_id=${a.id}`}
                                className="btn btn-primary btn-sm"
                              >
                                View ML &rarr;
                              </Link>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          <MedicalDisclaimer />
        </div>
      </div>
    </div>
  );
}
