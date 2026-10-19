import { useState } from 'react';
import InputField from '../forms/InputField';
import SelectField from '../forms/SelectField';
import FormError from '../forms/FormError';
import { validateAge } from '../../utils/validators';

export default function MedicalHistoryForm({ initialData = {}, onSubmit, isSubmitting = false }) {
  const [formData, setFormData] = useState({
    age: initialData.age ?? '',
    sex: initialData.sex ?? 'Male',
    medical_record_number: initialData.medical_record_number ?? '',
    notes: initialData.notes ?? '',
  });

  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: null }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitError(null);

    const ageErr = validateAge(formData.age);
    if (ageErr) {
      setErrors({ age: ageErr });
      return;
    }

    try {
      await onSubmit({
        age: Number(formData.age),
        sex: formData.sex,
        medical_record_number: formData.medical_record_number || null,
        notes: formData.notes || null,
      });
    } catch (err) {
      setSubmitError(err.message || 'Failed to save patient profile.');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="clean-card" style={{ maxWidth: '640px', margin: '0 auto' }}>
      <h3 style={{ marginBottom: '0.5rem' }}>
        {initialData.id ? 'Update Patient Profile' : 'New Patient Intake'}
      </h3>
      <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', marginBottom: '1.5rem' }}>
        Patient codes are generated automatically to guarantee HIPAA Safe Harbor de-identification.
      </p>

      {submitError && <FormError message={submitError} onRetry={() => setSubmitError(null)} />}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
        <InputField
          id="age"
          label="Patient Age"
          type="number"
          value={formData.age}
          onChange={handleChange}
          placeholder="e.g. 58"
          min={18}
          max={120}
          required
          error={errors.age}
          helpText="Adults 18 - 120 years"
        />

        <SelectField
          id="sex"
          label="Biological Sex"
          value={formData.sex}
          onChange={handleChange}
          options={[
            { value: 'Male', label: 'Male' },
            { value: 'Female', label: 'Female' },
          ]}
          required
        />
      </div>

      <InputField
        id="medical_record_number"
        label="Medical Record Number (MRN)"
        value={formData.medical_record_number}
        onChange={handleChange}
        placeholder="e.g. MRN-88210"
        optional
        helpText="Converted to a one-way SHA-256 hash immediately upon ingestion. Never stored in plaintext."
      />

      <div className="form-group">
        <label htmlFor="notes" className="form-label">
          <span>Clinical Intake Notes</span>
          <span className="form-label-optional">(Optional)</span>
        </label>
        <textarea
          id="notes"
          name="notes"
          value={formData.notes}
          onChange={handleChange}
          rows={3}
          placeholder="Brief clinical context, referral indication, or relevant history..."
          className="form-control"
          style={{ resize: 'vertical' }}
        />
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1.5rem' }}>
        <button type="submit" disabled={isSubmitting} className="btn btn-primary">
          {isSubmitting ? 'Saving Profile...' : initialData.id ? 'Save Changes' : 'Create Patient Profile'}
        </button>
      </div>
    </form>
  );
}
