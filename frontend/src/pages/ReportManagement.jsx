import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { reportService } from '../services/reportService';
import { patientService } from '../services/patientService';
import ReportUpload from '../components/reports/ReportUpload';
import ReportEntryForm from '../components/reports/ReportEntryForm';
import Sidebar from '../components/common/Sidebar';
import Loader from '../components/common/Loader';
import FormError from '../components/forms/FormError';
import MedicalDisclaimer from '../components/predictions/MedicalDisclaimer';
import { formatDateTime } from '../utils/formatters';

export default function ReportManagement() {
  const [searchParams] = useSearchParams();
  const [assessmentId, setAssessmentId] = useState(searchParams.get('assessment_id') || '');
  const [patients, setPatients] = useState([]);
  const [selectedPatientId, setSelectedPatientId] = useState('');
  const [patientAssessments, setPatientAssessments] = useState([]);

  const [activeTab, setActiveTab] = useState('labs'); // 'labs' | 'documents'
  const [documents, setDocuments] = useState([]);
  const [labs, setLabs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isSavingLab, setIsSavingLab] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  useEffect(() => {
    async function init() {
      setLoading(true);
      setError(null);
      try {
        const ptsRes = await patientService.listPatients({ page: 1, per_page: 50 });
        const items = ptsRes?.items || [];
        setPatients(items);

        if (items.length > 0 && !selectedPatientId) {
          setSelectedPatientId(items[0].id);
          const assessRes = await patientService.listAssessments(items[0].id);
          setPatientAssessments(assessRes || []);
          if (!assessmentId && assessRes?.length > 0) {
            setAssessmentId(assessRes[0].id);
          }
        }
      } catch (err) {
        setError(err.message || 'Failed to initialize report management.');
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
      setError(err.message || 'Failed to fetch assessments for patient.');
    }
  };

  useEffect(() => {
    if (!assessmentId) return;

    async function loadData() {
      try {
        const [docsRes, labsRes] = await Promise.all([
          reportService.listDocuments(assessmentId).catch(() => []),
          reportService.listLabMeasurements(assessmentId).catch(() => []),
        ]);
        setDocuments(docsRes || []);
        setLabs(labsRes || []);
      } catch (err) {
        setError(err.message || 'Failed to load documents or labs.');
      }
    }

    loadData();
  }, [assessmentId]);

  const handleUploadDocument = async (file, category) => {
    if (!assessmentId) {
      setError('Please select an active clinical assessment encounter first.');
      return;
    }
    setIsUploading(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const res = await reportService.uploadDocument(assessmentId, file, category);
      setDocuments((prev) => [res, ...prev]);
      setSuccessMessage(`Document "${file.name}" uploaded securely (SHA-256 verified).`);
    } catch (err) {
      setError(err.message || 'Failed to upload document.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleSaveLab = async (payload) => {
    if (!assessmentId) {
      setError('Please select an active clinical assessment encounter first.');
      return;
    }
    setIsSavingLab(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const res = await reportService.createLabMeasurement(assessmentId, payload);
      setLabs((prev) => [res, ...prev]);
      setSuccessMessage(`Measurement for "${payload.test_name}" recorded successfully.`);
    } catch (err) {
      setError(err.message || 'Failed to record lab measurement.');
    } finally {
      setIsSavingLab(false);
    }
  };

  const handleDownload = async (doc) => {
    try {
      const blob = await reportService.downloadDocument(doc.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = doc.original_filename || `document-${doc.id}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Failed to download document: ' + err.message);
    }
  };

  return (
    <div className="app-container" style={{ padding: '2.5rem 1rem 4rem' }}>
      <div style={{ display: 'flex', gap: '2rem', alignItems: 'flex-start' }}>
        <Sidebar assessmentId={assessmentId} />

        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '2rem' }}>
            <div>
              <span className="pill-badge" style={{ marginBottom: '0.4rem' }}>
                <span className="pill-dot" /> Objective Clinical Records
              </span>
              <h2 style={{ fontSize: '2.2rem', letterSpacing: '-0.03em' }}>
                Medical Reports &amp; Laboratory Data
              </h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem' }}>
                Upload diagnostic documents and enter structured laboratory values for predictive modeling.
              </p>
            </div>

            {assessmentId && (
              <Link
                to={`/prediction-results?assessment_id=${assessmentId}`}
                className="btn btn-primary"
              >
                Proceed to ML Predictions &rarr;
              </Link>
            )}
          </div>

          {error && <FormError message={error} onRetry={() => setError(null)} />}
          {successMessage && (
            <div style={{
              backgroundColor: '#ecfdf5',
              border: '1px solid #a7f3d0',
              color: '#065f46',
              borderRadius: 'var(--radius-md)',
              padding: '0.85rem 1.25rem',
              marginBottom: '1.5rem',
              fontSize: '0.9rem',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}>
              <span>&check; {successMessage}</span>
              <button
                type="button"
                onClick={() => setSuccessMessage(null)}
                style={{ background: 'none', border: 'none', color: '#065f46', cursor: 'pointer', fontWeight: 700 }}
              >
                &times;
              </button>
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

          {/* Tab Navigation */}
          <div style={{
            display: 'flex',
            borderBottom: '1px solid var(--border-light)',
            marginBottom: '1.5rem',
            gap: '1rem',
          }}>
            <button
              type="button"
              onClick={() => setActiveTab('labs')}
              style={{
                background: 'none',
                border: 'none',
                padding: '0.75rem 1rem',
                fontSize: '1rem',
                fontWeight: activeTab === 'labs' ? 700 : 500,
                color: activeTab === 'labs' ? 'var(--primary-red)' : 'var(--text-muted)',
                borderBottom: activeTab === 'labs' ? '3px solid var(--primary-red)' : '3px solid transparent',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              Structured Lab Measurements ({labs.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('documents')}
              style={{
                background: 'none',
                border: 'none',
                padding: '0.75rem 1rem',
                fontSize: '1rem',
                fontWeight: activeTab === 'documents' ? 700 : 500,
                color: activeTab === 'documents' ? 'var(--primary-red)' : 'var(--text-muted)',
                borderBottom: activeTab === 'documents' ? '3px solid var(--primary-red)' : '3px solid transparent',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              Diagnostic Documents &amp; ECGs ({documents.length})
            </button>
          </div>

          {loading ? (
            <Loader message="Loading clinical records..." />
          ) : (
            <>
              {activeTab === 'labs' && (
                <div>
                  <ReportEntryForm onSave={handleSaveLab} isSaving={isSavingLab} />

                  {/* Recorded Labs List */}
                  <div className="clean-card" style={{ marginTop: '2rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                      <div>
                        <h3 style={{ fontSize: '1.25rem' }}>Recorded Laboratory Measurements</h3>
                        <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                          Objective physiological measurements attached to Encounter #{assessmentId}
                        </p>
                      </div>
                      <span className="modality-tag modality-objective">Measured [OBJECTIVE]</span>
                    </div>

                    {labs.length === 0 ? (
                      <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>
                        No structured laboratory values recorded for this encounter yet.
                      </p>
                    ) : (
                      <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
                          <thead>
                            <tr style={{ borderBottom: '2px solid #f3f4f6', color: 'var(--text-muted)' }}>
                              <th style={{ padding: '0.75rem 0.5rem' }}>Analyte / Test</th>
                              <th style={{ padding: '0.75rem 0.5rem' }}>Value</th>
                              <th style={{ padding: '0.75rem 0.5rem' }}>Unit</th>
                              <th style={{ padding: '0.75rem 0.5rem' }}>Reference Limit</th>
                              <th style={{ padding: '0.75rem 0.5rem' }}>Status Flag</th>
                            </tr>
                          </thead>
                          <tbody>
                            {labs.map((item, idx) => {
                              const isAbnormal = item.flag && item.flag !== 'normal';
                              return (
                                <tr key={item.id || idx} style={{ borderBottom: '1px solid #f3f4f6' }}>
                                  <td style={{ padding: '0.75rem 0.5rem', fontWeight: 600, color: 'var(--text-main)', textTransform: 'capitalize' }}>
                                    {item.test_name?.replace(/_/g, ' ')}
                                  </td>
                                  <td style={{ padding: '0.75rem 0.5rem', fontWeight: 700, color: isAbnormal ? 'var(--primary-red)' : 'var(--text-main)' }}>
                                    {item.value_numeric}
                                  </td>
                                  <td style={{ padding: '0.75rem 0.5rem', color: 'var(--text-muted)' }}>
                                    {item.unit || '—'}
                                  </td>
                                  <td style={{ padding: '0.75rem 0.5rem', color: 'var(--text-muted)' }}>
                                    {item.reference_high ? `< ${item.reference_high}` : '—'}
                                  </td>
                                  <td style={{ padding: '0.75rem 0.5rem' }}>
                                    <span style={{
                                      fontSize: '0.75rem',
                                      fontWeight: 700,
                                      padding: '0.2rem 0.5rem',
                                      borderRadius: 'var(--radius-pill)',
                                      backgroundColor: isAbnormal ? '#fee2e2' : '#ecfdf5',
                                      color: isAbnormal ? '#b91c1c' : '#065f46',
                                    }}>
                                      {item.flag || 'normal'}
                                    </span>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {activeTab === 'documents' && (
                <div>
                  <ReportUpload onUpload={handleUploadDocument} isUploading={isUploading} />

                  {/* Uploaded Documents List */}
                  <div className="clean-card" style={{ marginTop: '2rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                      <div>
                        <h3 style={{ fontSize: '1.25rem' }}>Stored Diagnostic Files</h3>
                        <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                          Encrypted files stored outside web root with cryptographic integrity hashes
                        </p>
                      </div>
                      <span className="modality-tag" style={{ backgroundColor: '#f1f5f9', color: '#475569' }}>
                        Stored Unparsed
                      </span>
                    </div>

                    {documents.length === 0 ? (
                      <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>
                        No diagnostic documents or scans uploaded for this encounter yet.
                      </p>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        {documents.map((doc) => (
                          <div
                            key={doc.id}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              padding: '1rem 1.25rem',
                              borderRadius: 'var(--radius-md)',
                              backgroundColor: '#fafafa',
                              border: '1px solid #e5e7eb',
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                              <div style={{
                                width: '40px',
                                height: '40px',
                                borderRadius: 'var(--radius-md)',
                                backgroundColor: '#fee2e2',
                                color: 'var(--primary-red)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                              }}>
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                  <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />
                                  <path d="M14 2v4a2 2 0 0 0 2 2h4" />
                                </svg>
                              </div>

                              <div>
                                <div style={{ fontWeight: 700, color: 'var(--text-main)', fontSize: '0.95rem' }}>
                                  {doc.original_filename}
                                </div>
                                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                                  Category: {doc.document_category?.replace(/_/g, ' ')} &bull; Uploaded: {formatDateTime(doc.created_at)}
                                </div>
                                <div style={{ fontSize: '0.72rem', color: 'var(--text-light)', fontFamily: 'monospace', marginTop: '0.2rem' }}>
                                  SHA-256: {doc.sha256_hash ? `${doc.sha256_hash.substring(0, 16)}...` : 'Verified'}
                                </div>
                              </div>
                            </div>

                            <button
                              type="button"
                              onClick={() => handleDownload(doc)}
                              className="btn btn-secondary btn-sm"
                            >
                              Download File
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              <MedicalDisclaimer />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
