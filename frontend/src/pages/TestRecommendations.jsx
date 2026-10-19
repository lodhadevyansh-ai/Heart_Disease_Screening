import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { recommendationService } from '../services/recommendationService';
import Sidebar from '../components/common/Sidebar';
import Loader from '../components/common/Loader';
import FormError from '../components/forms/FormError';
import MedicalDisclaimer from '../components/predictions/MedicalDisclaimer';

export default function TestRecommendations() {
  const [searchParams] = useSearchParams();
  const assessmentId = searchParams.get('assessment_id');

  const [recommendations, setRecommendations] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchRecommendations() {
      if (!assessmentId) {
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const data = await recommendationService.evaluateAssessment(assessmentId);
        setRecommendations(data);
      } catch (err) {
        setError(err.message || 'Failed to retrieve clinical recommendations.');
      } finally {
        setLoading(false);
      }
    }

    fetchRecommendations();
  }, [assessmentId]);

  const isEmergency = recommendations?.is_emergency;
  const emergencyRules = recommendations?.emergency_triage?.triggered_rules || [];
  const testRecs = recommendations?.diagnostic_recommendations?.recommendations || [];
  const symptomEval = recommendations?.symptom_evaluation || {};

  return (
    <div className="app-container" style={{ padding: '2.5rem 1rem 4rem' }}>
      <div style={{ display: 'flex', gap: '2rem', alignItems: 'flex-start' }}>
        <Sidebar assessmentId={assessmentId} />

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '2rem' }}>
            <div>
              <span className="pill-badge" style={{ marginBottom: '0.4rem' }}>
                <span className="pill-dot" /> Clinical Safety &amp; CDS
              </span>
              <h2 style={{ fontSize: '2.2rem', letterSpacing: '-0.03em' }}>
                Evidence-Based Test Recommendations
              </h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem' }}>
                Encounter #{assessmentId || 'Ad-Hoc'} &bull; AHA/ACC/ESC Clinical Practice Guidelines
              </p>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <Link to={`/report-management?assessment_id=${assessmentId}`} className="btn btn-secondary">
                Add Lab Measurements &rarr;
              </Link>
              <Link to={`/prediction-results?assessment_id=${assessmentId}`} className="btn btn-primary">
                View AI Risk Estimates &rarr;
              </Link>
            </div>
          </div>

          {error && <FormError message={error} onRetry={() => window.location.reload()} />}

          {!assessmentId ? (
            <div className="clean-card" style={{ textAlign: 'center', padding: '3.5rem 1.5rem' }}>
              <h3 style={{ marginBottom: '0.5rem' }}>No Encounter Selected</h3>
              <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem' }}>
                Select an existing encounter from the Dashboard or complete a Symptom Check-in to view clinical recommendations.
              </p>
              <Link to="/symptom-assessment" className="btn btn-primary">
                Start Symptom Assessment &rarr;
              </Link>
            </div>
          ) : loading ? (
            <Loader message="Synthesizing clinical safety rules and evidence recommendations..." />
          ) : (
            <>
              {/* Emergency Primacy Alert Banner if Red Flag Present */}
              {isEmergency && (
                <div style={{
                  backgroundColor: '#fef2f2',
                  border: '2px solid #ef4444',
                  borderRadius: 'var(--radius-xl)',
                  padding: '2rem',
                  marginBottom: '2rem',
                  boxShadow: '0 12px 30px rgba(239, 68, 68, 0.15)',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', marginBottom: '1rem' }}>
                    <div style={{
                      width: '42px',
                      height: '42px',
                      borderRadius: '50%',
                      backgroundColor: 'var(--primary-red)',
                      color: '#ffffff',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 800,
                      fontSize: '1.2rem',
                    }}>
                      !
                    </div>
                    <div>
                      <h3 style={{ color: '#991b1b', fontSize: '1.45rem', fontWeight: 800 }}>
                        RED-FLAG EMERGENCY PROTOCOL TRIGGERED
                      </h3>
                      <p style={{ color: '#b91c1c', fontSize: '0.9rem', fontWeight: 600 }}>
                        Immediate Emergency Medical Services (911 / EMS) Required
                      </p>
                    </div>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', marginTop: '1.25rem' }}>
                    {emergencyRules.map((rule, idx) => (
                      <div key={idx} style={{
                        backgroundColor: '#ffffff',
                        border: '1px solid #fecaca',
                        borderRadius: 'var(--radius-md)',
                        padding: '1rem 1.25rem',
                      }}>
                        <div style={{ fontWeight: 800, color: '#991b1b', fontSize: '1rem' }}>
                          {rule.title}
                        </div>
                        <p style={{ fontSize: '0.88rem', color: '#7f1d1d', marginTop: '0.25rem' }}>
                          <strong>Clinical Rationale: </strong>{rule.rationale}
                        </p>
                        <p style={{ fontSize: '0.88rem', color: '#166534', marginTop: '0.4rem', fontWeight: 600 }}>
                          <strong>Action Guidance: </strong>{rule.action_guidance}
                        </p>
                        <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: '0.35rem' }}>
                          Source: {rule.guideline_source} &bull; Reviewed: {rule.review_date}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Symptom Pattern Evaluation */}
              <div className="clean-card" style={{ marginBottom: '2rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.75rem' }}>
                  <span className="pill-badge">Pattern Characterization</span>
                  <span className="modality-tag modality-subjective">Patient Reported</span>
                </div>
                <h3 style={{ fontSize: '1.35rem', marginBottom: '1rem' }}>
                  Diagnostic Classification Summary
                </h3>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
                  <div style={{ backgroundColor: '#fafafa', padding: '1rem 1.25rem', borderRadius: 'var(--radius-md)', border: '1px solid #f0f0f0' }}>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                      Angina Classification
                    </div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '0.2rem' }}>
                      {symptomEval.angina_classification ? symptomEval.angina_classification.replace(/_/g, ' ') : 'None / Not Reported'}
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-light)', marginTop: '0.2rem' }}>
                      Diamond-Forrester / AHA 2021
                    </div>
                  </div>

                  <div style={{ backgroundColor: '#fafafa', padding: '1rem 1.25rem', borderRadius: 'var(--radius-md)', border: '1px solid #f0f0f0' }}>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                      Congestive Score
                    </div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '0.2rem' }}>
                      {symptomEval.congestive_symptom_score ?? 0} points
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-light)', marginTop: '0.2rem' }}>
                      ESC 2021 Congestive Signs
                    </div>
                  </div>

                  <div style={{ backgroundColor: '#fafafa', padding: '1rem 1.25rem', borderRadius: 'var(--radius-md)', border: '1px solid #f0f0f0' }}>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                      Overall Priority Tier
                    </div>
                    <div style={{
                      fontSize: '1.2rem',
                      fontWeight: 800,
                      color: isEmergency ? 'var(--primary-red)' : 'var(--accent-green)',
                      marginTop: '0.2rem',
                    }}>
                      {recommendations?.overall_urgency?.replace(/_/g, ' ') || 'Routine'}
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-light)', marginTop: '0.2rem' }}>
                      Clinical urgency tier
                    </div>
                  </div>
                </div>
              </div>

              {/* Secondary Diagnostic Test Recommendations */}
              <div className="clean-card" style={{ marginBottom: '2rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.75rem' }}>
                  <span className="pill-badge pill-badge-green">Evidence-Based Pathways</span>
                  <span className="modality-tag modality-objective">Secondary Workup</span>
                </div>
                <h3 style={{ fontSize: '1.35rem', marginBottom: '1rem' }}>
                  Recommended Secondary Diagnostic Investigations
                </h3>

                {testRecs.length === 0 ? (
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem' }}>
                    No specific secondary diagnostic testing indicated based on the recorded profile. Routine preventive maintenance recommended.
                  </p>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {testRecs.map((rec, idx) => (
                      <div key={idx} style={{
                        padding: '1.25rem',
                        borderRadius: 'var(--radius-md)',
                        backgroundColor: '#ffffff',
                        border: '1px solid var(--border-light)',
                        borderLeft: `5px solid ${rec.priority?.includes('EMERGENCY') ? 'var(--primary-red)' : 'var(--accent-green)'}`,
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: '0.5rem' }}>
                          <h4 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-main)' }}>
                            {rec.title}
                          </h4>
                          <span style={{
                            fontSize: '0.75rem',
                            fontWeight: 700,
                            padding: '0.25rem 0.65rem',
                            borderRadius: 'var(--radius-pill)',
                            backgroundColor: '#f3f4f6',
                            color: '#374151',
                          }}>
                            Class I / IIa Guideline
                          </span>
                        </div>

                        <p style={{ fontSize: '0.88rem', color: 'var(--text-body)', marginTop: '0.4rem', lineHeight: 1.5 }}>
                          <strong>Indication: </strong>{rec.rationale}
                        </p>

                        <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                          <strong>Action: </strong>{rec.action_guidance}
                        </p>

                        <div style={{ fontSize: '0.75rem', color: 'var(--text-light)', marginTop: '0.5rem' }}>
                          Citation: {rec.guideline_source} &bull; Review Date: {rec.review_date}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <MedicalDisclaimer />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
