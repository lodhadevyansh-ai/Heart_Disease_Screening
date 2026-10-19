import { useState, useEffect } from 'react';
import { patientService } from '../services/patientService';
import Sidebar from '../components/common/Sidebar';
import PatientProfileCard from '../components/patient/PatientProfileCard';
import MedicalHistoryForm from '../components/patient/MedicalHistoryForm';
import Loader from '../components/common/Loader';
import FormError from '../components/forms/FormError';

export default function PatientProfile() {
  const [patients, setPatients] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState(null);

  const fetchPatients = async () => {
    try {
      const res = await patientService.listPatients({ page: 1, per_page: 20 });
      const items = res?.items || [];
      setPatients(items);
      if (items.length > 0 && !selectedPatient) {
        setSelectedPatient(items[0]);
      }
    } catch (err) {
      setError(err.message || 'Failed to load patient records.');
    }
  };

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const res = await patientService.listPatients({ page: 1, per_page: 20 });
        const items = res?.items || [];
        setPatients(items);
        if (items.length > 0) {
          setSelectedPatient(items[0]);
        }
      } catch (err) {
        setError(err.message || 'Failed to load patient records.');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const handleCreatePatient = async (payload) => {
    setIsSubmitting(true);
    try {
      const newPt = await patientService.createPatient(payload);
      setSuccessMessage(`Patient ${newPt.patient_code} successfully created.`);
      setShowCreateForm(false);
      setSelectedPatient(newPt);
      await fetchPatients();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="app-container" style={{ padding: '2.5rem 1rem 4rem' }}>
      <div style={{ display: 'flex', gap: '2rem', alignItems: 'flex-start' }}>
        <Sidebar />

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.75rem', flexWrap: 'wrap', gap: '1rem' }}>
            <div>
              <span className="pill-badge" style={{ marginBottom: '0.4rem' }}>
                <span className="pill-dot" /> Demographic Management
              </span>
              <h2 style={{ fontSize: '2rem' }}>Patient Profiles</h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                HIPAA Safe Harbor de-identified records with cryptographic MRN hashing.
              </p>
            </div>

            <button
              type="button"
              onClick={() => {
                setShowCreateForm(!showCreateForm);
                setSuccessMessage(null);
              }}
              className="btn btn-primary"
            >
              {showCreateForm ? 'View Patient Records' : '+ New Patient Profile'}
            </button>
          </div>

          {successMessage && (
            <div style={{
              backgroundColor: '#f0fdf4',
              border: '1px solid #bbf7d0',
              borderRadius: 'var(--radius-md)',
              padding: '0.9rem 1.25rem',
              color: '#166534',
              marginBottom: '1.5rem',
              fontWeight: 600,
            }}>
              &#10003; {successMessage}
            </div>
          )}

          {error && <FormError message={error} onRetry={fetchPatients} />}

          {showCreateForm ? (
            <MedicalHistoryForm
              onSubmit={handleCreatePatient}
              isSubmitting={isSubmitting}
            />
          ) : loading ? (
            <Loader message="Loading patient records..." />
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '1.5rem' }}>
              {/* Left Patient List */}
              <div className="clean-card" style={{ padding: '1rem' }}>
                <h4 style={{ fontSize: '1rem', padding: '0.5rem 0.5rem 0.75rem', borderBottom: '1px solid #f0f0f0' }}>
                  Registered Patients ({patients.length})
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginTop: '0.75rem' }}>
                  {patients.map((pt) => {
                    const isSelected = selectedPatient?.id === pt.id;
                    return (
                      <div
                        key={pt.id}
                        onClick={() => setSelectedPatient(pt)}
                        style={{
                          padding: '0.85rem',
                          borderRadius: 'var(--radius-md)',
                          backgroundColor: isSelected ? 'var(--primary-red-subtle)' : 'transparent',
                          border: `1px solid ${isSelected ? 'var(--primary-red-border)' : 'transparent'}`,
                          cursor: 'pointer',
                          transition: 'all 0.15s ease',
                        }}
                      >
                        <div style={{ fontWeight: 700, fontSize: '0.95rem', color: isSelected ? 'var(--primary-red)' : 'var(--text-main)' }}>
                          {pt.patient_code}
                        </div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                          Age {pt.age} &bull; {pt.sex} &bull; {pt.assessments_count || 0} visits
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Right Detail View */}
              <div>
                {selectedPatient ? (
                  <PatientProfileCard patient={selectedPatient} />
                ) : (
                  <div className="clean-card" style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-muted)' }}>
                    Select a patient from the list to view profile details.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
