/**
 * Client-side Clinical & Usability Input Validators.
 * Provides immediate feedback to users while security and correctness are enforced on backend.
 */

export function validateAge(age) {
  const num = Number(age);
  if (!age || isNaN(num)) return 'Age is required and must be a number.';
  if (num < 18 || num > 120) return 'Age must be within clinical adult bounds (18 - 120 years).';
  return null;
}

export function validateBloodPressure(systolic, diastolic) {
  const sys = systolic !== '' && systolic !== null ? Number(systolic) : null;
  const dia = diastolic !== '' && diastolic !== null ? Number(diastolic) : null;

  if (sys !== null) {
    if (isNaN(sys) || sys < 40 || sys > 300) {
      return 'Systolic BP must be between 40 and 300 mmHg.';
    }
  }

  if (dia !== null) {
    if (isNaN(dia) || dia < 20 || dia > 200) {
      return 'Diastolic BP must be between 20 and 200 mmHg.';
    }
  }

  if (sys !== null && dia !== null && dia >= sys) {
    return 'Diastolic BP cannot be greater than or equal to Systolic BP.';
  }

  return null;
}

export function validateHeartRate(hr) {
  if (hr === '' || hr === null || hr === undefined) return null;
  const num = Number(hr);
  if (isNaN(num) || num < 20 || num > 300) {
    return 'Heart rate must be between 20 and 300 bpm.';
  }
  return null;
}

export function validateDocumentFile(file) {
  if (!file) return 'Please select a file to upload.';
  const allowedExtensions = ['pdf', 'png', 'jpg', 'jpeg'];
  const ext = file.name.split('.').pop().toLowerCase();

  if (!allowedExtensions.includes(ext)) {
    return `Unsupported file extension (.${ext}). Allowed: ${allowedExtensions.join(', ')}`;
  }

  const maxBytes = 10 * 1024 * 1024; // 10MB
  if (file.size > maxBytes) {
    return `File size exceeds 10 MB limit (current: ${(file.size / (1024 * 1024)).toFixed(1)} MB).`;
  }

  return null;
}
