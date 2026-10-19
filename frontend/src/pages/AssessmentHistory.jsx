import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { patientService } from '../services/patientService';
import Sidebar from '../components/common/Sidebar';
import Loader from '../components/common/Loader';
import FormError from '../components/forms/FormError';
import MedicalDisclaimer from '../components/predictions/MedicalDisclaimer';
import { formatDateTime } from '../utils/formatters';

export default function AssessmentHistory() {
  const [patients, setPatients] = useState([]);
  const [selectedPatientId, setSelectedPatientId] = useState('');
  const [assessments, setAssessments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const ptsRes = await patientService.listPatients({ page: 1, per_page: 100 });
        const items = ptsRes?.items || [];
        setPatients(items);

        if (items.length > 0) {
          setSelectedPatientId('all');
          // Fetch assessments for all patients concurrently
          const allAssessments = [];
          for (const p of items) {
            try {
              const aRes = await patientService.listAssessments(p.id);
              if (Array.isArray(aRes)) {
                for (const a of aRes) {
                  allAssessments.push({ ...a, patient: p });
                }
              }
            } catch {
              // skip failed patient assessment fetch
            }
          }
          // Sort descending by date
          allAssessments.sort((a, b) => new Date(b.assessment_date) - new Date(a.assessment_date));
          setAssessments(allAssessments);
        }
      } catch (err) {
        setError(err.message || 'Failed to load assessment history.');
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  const filteredAssessments = assessments.filter((a) => {
    if (selectedPatientId !== 'all' && String(a.patient_id) !== String(selectedPatientId)) {
      return false;
    }
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      const codeMatch = a.patient?.patient_code?.toLowerCase().includes(q);
      const reasonMatch = a.reason_for_visit?.toLowerCase().includes(q);
      const statusMatch = a.status?.toLowerCase().includes(q);
      return codeMatch || reasonMatch || statusMatch;
    }
    return true;
  });

  return (
    <div className="app-container" style={{ padding: '2.5rem 1rem 4rem' }}>
      <div style={{ display: 'flex', gap: '2rem', alignItems: 'flex-start' }}>
        <Sidebar />

        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '2rem' }}>
            <div>
              <span className="pill-badge" style={{ marginBottom: '0.4rem' }}>
                <span className="pill-dot" /> Audit Trail
              </span>
              <h2 style={{ fontSize: '2.2rem', letterSpacing: '-0.03em' }}>
                Assessment &amp; Screening History
              </h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem' }}>
                Chronological log of clinical encounters, symptom assessments, and decision support runs.
              </p>
            </div>

            <Link to="/symptom-assessment" className="btn btn-primary">
              + New Assessment &rarr;
            </Link>
          </div>

          {error && <FormError message={error} onRetry={() => window.location.reload()} />}

          {/* Filter Bar */}
          <div className="clean-card" style={{ marginBottom: '2rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
              <div>
                <label className="form-label" htmlFor="filter-patient">
                  Filter by Patient Profile
                </label>
                <select
                  id="filter-patient"
                  className="form-control"
                  value={selectedPatientId}
                  onChange={(e) => setSelectedPatientId(e.target.value)}
                >
                  <option value="all">All Patients ({patients.length})</option>
                  {patients.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.patient_code} ({p.age}y &bull; {p.sex})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="form-label" htmlFor="filter-search">
                  Search by Keyword
                </label>
                <input
                  id="filter-search"
                  type="text"
                  className="form-control"
                  placeholder="Search code, reason, status..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Assessments Table */}
          {loading ? (
            <Loader message="Loading assessment audit trail..." />
          ) : filteredAssessments.length === 0 ? (
            <div className="clean-card" style={{ textAlign: 'center', padding: '3.5rem 1.5rem', color: 'var(--text-muted)' }}>
              <div style={{
                width: '56px',
                height: '56px',
                borderRadius: '50%',
                backgroundColor: '#f1f5f9',
                color: 'var(--text-muted)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 1rem',
              }}>
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                </svg>
              </div>
              <h4 style={{ fontSize: '1.2rem', color: 'var(--text-main)', marginBottom: '0.4rem' }}>
                No Clinical Encounters Found
              </h4>
              <p style={{ fontSize: '0.88rem', maxWidth: '440px', margin: '0 auto 1.5rem' }}>
                There are no recorded patient screening encounters matching this filter. Start a new cardiovascular screening session to begin.
              </p>
              <Link to="/symptom-assessment" className="btn btn-primary">
                Start Your First Screening &rarr;
              </Link>
            </div>
          ) : (
            <div className="clean-card" style={{ overflowX: 'auto', padding: '0.5rem' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #f3f4f6', color: 'var(--text-muted)' }}>
                    <th style={{ padding: '0.85rem 1rem' }}>Encounter</th>
                    <th style={{ padding: '0.85rem 1rem' }}>Patient Code</th>
                    <th style={{ padding: '0.85rem 1rem' }}>Demographics</th>
                    <th style={{ padding: '0.85rem 1rem' }}>Date &amp; Time</th>
                    <th style={{ padding: '0.85rem 1rem' }}>Clinical Status</th>
                    <th style={{ padding: '0.85rem 1rem', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAssessments.map((a) => {
                    const isEmergency =
                      a.status === 'flagged_emergency' ||
                      a.emergency_escalation_level === 'EMERGENCY_IMMEDIATE_911';

                    return (
                      <tr
                        key={a.id}
                        style={{
                          borderBottom: '1px solid #f3f4f6',
                          backgroundColor: isEmergency ? '#fff5f5' : 'transparent',
                          transition: 'background-color 0.1s ease',
                        }}
                      >
                        <td style={{ padding: '1rem', fontWeight: 700, color: 'var(--text-main)' }}>
                          #{a.id}
                          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                            {a.reason_for_visit || 'General Assessment'}
                          </div>
                        </td>

                        <td style={{ padding: '1rem', fontWeight: 600 }}>
                          <span style={{ color: 'var(--primary-red)' }}>
                            {a.patient?.patient_code || `ID ${a.patient_id}`}
                          </span>
                        </td>

                        <td style={{ padding: '1rem', color: 'var(--text-body)' }}>
                          {a.patient ? `${a.patient.age}y • ${a.patient.sex}` : '—'}
                        </td>

                        <td style={{ padding: '1rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                          {formatDateTime(a.assessment_date)}
                        </td>

                        <td style={{ padding: '1rem' }}>
                          <span style={{
                            fontSize: '0.75rem',
                            fontWeight: 700,
                            padding: '0.25rem 0.65rem',
                            borderRadius: 'var(--radius-pill)',
                            backgroundColor: isEmergency ? '#fee2e2' : '#ecfdf5',
                            color: isEmergency ? '#b91c1c' : '#065f46',
                            border: `1px solid ${isEmergency ? '#fca5a5' : '#a7f3d0'}`,
                            textTransform: 'uppercase',
                          }}>
                            {isEmergency ? 'Emergency Flag' : a.status || 'Active'}
                          </span>
                        </td>

                        <td style={{ padding: '1rem', textAlign: 'right' }}>
                          <div style={{ display: 'inline-flex', gap: '0.4rem' }}>
                            <Link
                              to={`/test-recommendations?assessment_id=${a.id}`}
                              className="btn btn-secondary btn-sm"
                            >
                              Recommendations
                            </Link>
                            <Link
                              to={`/report-management?assessment_id=${a.id}`}
                              className="btn btn-secondary btn-sm"
                            >
                              Reports
                            </Link>
                            <Link
                              to={`/prediction-results?assessment_id=${a.id}`}
                              className="btn btn-primary btn-sm"
                            >
                              Predictions &rarr;
                            </Link>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          <MedicalDisclaimer />
        </div>
      </div>
    </div>
  );
}
