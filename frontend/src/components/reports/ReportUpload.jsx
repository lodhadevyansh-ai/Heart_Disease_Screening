import { useState, useRef } from 'react';
import { validateDocumentFile } from '../../utils/validators';
import FormError from '../forms/FormError';

export default function ReportUpload({ onUpload, isUploading = false }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [category, setCategory] = useState('ecg_report_pdf');
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  const handleFile = (file) => {
    setError(null);
    const err = validateDocumentFile(file);
    if (err) {
      setError(err);
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!selectedFile) {
      setError('Please select a valid document to upload.');
      return;
    }
    onUpload(selectedFile, category);
  };

  return (
    <form onSubmit={handleSubmit} className="clean-card" style={{ maxWidth: '640px', margin: '0 auto 2rem' }}>
      <h3 style={{ marginBottom: '0.4rem' }}>Upload Medical Document</h3>
      <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', marginBottom: '1.5rem' }}>
        Store PDF reports or ECG images securely in private hospital storage for clinician review.
      </p>

      {error && <FormError message={error} onRetry={() => setError(null)} />}

      {/* Drag & Drop Upload Zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        style={{
          border: `2px dashed ${dragActive ? 'var(--primary-red)' : '#d1d5db'}`,
          borderRadius: 'var(--radius-lg)',
          backgroundColor: dragActive ? 'var(--primary-red-subtle)' : '#fafafa',
          padding: '2.5rem 1.5rem',
          textAlign: 'center',
          cursor: 'pointer',
          transition: 'all 0.2s ease',
          marginBottom: '1.25rem',
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg"
          style={{ display: 'none' }}
          onChange={(e) => {
            if (e.target.files && e.target.files[0]) {
              handleFile(e.target.files[0]);
            }
          }}
        />

        <div style={{
          width: '48px',
          height: '48px',
          borderRadius: '50%',
          backgroundColor: '#ffffff',
          boxShadow: '0 4px 12px rgba(0,0,0,0.06)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 1rem',
          color: 'var(--primary-red)',
        }}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        </div>

        {selectedFile ? (
          <div>
            <p style={{ fontWeight: 700, color: 'var(--text-main)', fontSize: '1rem' }}>
              {selectedFile.name}
            </p>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
              {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB &bull; Ready to upload
            </p>
          </div>
        ) : (
          <div>
            <p style={{ fontWeight: 600, color: 'var(--text-main)' }}>
              Drag &amp; drop medical report here, or <span style={{ color: 'var(--primary-red)', textDecoration: 'underline' }}>browse</span>
            </p>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-light)', marginTop: '0.3rem' }}>
              Supported: PDF, PNG, JPG, JPEG (Max 10 MB)
            </p>
          </div>
        )}
      </div>

      <div className="form-group">
        <label htmlFor="document_category" className="form-label">
          Document Classification
        </label>
        <select
          id="document_category"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="form-control"
        >
          <option value="ecg_report_pdf">12-Lead ECG Report (PDF)</option>
          <option value="lab_results">Laboratory Bloodwork Results</option>
          <option value="clinical_note">Physician Clinical Consultation Note</option>
          <option value="echocardiogram_summary">Echocardiogram Diagnostic Summary</option>
        </select>
      </div>

      {/* Critical Extraction Disclaimer Notice */}
      <div style={{
        backgroundColor: '#f8fafc',
        border: '1px solid #e2e8f0',
        borderRadius: 'var(--radius-md)',
        padding: '0.85rem 1rem',
        fontSize: '0.8rem',
        color: '#475569',
        lineHeight: 1.45,
        marginBottom: '1.25rem',
      }}>
        <strong>Security &amp; Integrity Policy: </strong>
        Uploaded files are cryptographically hashed (SHA-256) and stored outside public web roots. Raw files are cataloged as <em>stored_unparsed</em>. Automated clinical interpretation is never asserted without a verified, audited extraction pipeline.
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
        <button
          type="submit"
          disabled={!selectedFile || isUploading}
          className="btn btn-primary"
        >
          {isUploading ? 'Uploading & Hashing...' : 'Upload Document'}
        </button>
      </div>
    </form>
  );
}
