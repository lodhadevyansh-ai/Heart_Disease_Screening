/**
 * Application Constants and Configuration Values.
 */

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api/v1';

export const AUTH_TOKEN_KEY = 'cardiocare_token';
export const AUTH_USER_KEY = 'cardiocare_user';

export const USER_ROLES = {
  CLINICIAN: 'clinician',
  ADMIN: 'admin',
  PATIENT: 'patient',
};

export const CLINICAL_SAFETY_DISCLAIMER =
  'CardioCare AI is a research and clinical decision-support prototype. It does NOT provide a definitive medical diagnosis and does NOT replace professional judgment or emergency services. In case of acute or life-threatening symptoms, immediately contact emergency services (911/EMS).';

export const SUPPORTED_TASKS = {
  CAD: 'coronary_artery_disease',
  HF_MORTALITY: 'heart_failure_mortality',
  ARRHYTHMIA_ECG: 'arrhythmia_ecg',
};

export const PROHIBITED_TASKS = {
  HF_SCREENING: 'heart_failure_screening',
  ARRHYTHMIA_SYMPTOM: 'arrhythmia_symptom_screening',
};

export const SYMPTOM_DEFINITIONS = [
  {
    id: 'chest_pain',
    label: 'Chest discomfort',
    description: 'Pressure, tightness, aching, or squeezing sensation across the chest',
    iconType: 'heart-crack',
  },
  {
    id: 'dyspnea',
    label: 'Breathlessness',
    description: 'Shortness of breath during exertion or while resting flat',
    iconType: 'wind',
  },
  {
    id: 'palpitations',
    label: 'Palpitations',
    description: 'Fluttering, pounding, racing, or skipped heartbeats',
    iconType: 'pulse',
  },
  {
    id: 'syncope',
    label: 'Dizziness or fainting',
    description: 'Lightheadedness, transient loss of consciousness, or near-fainting',
    iconType: 'sparkle',
  },
  {
    id: 'fatigue',
    label: 'Unusual fatigue',
    description: 'Unexplained profound exhaustion reducing daily physical capacity',
    iconType: 'battery-low',
  },
  {
    id: 'bilateral_leg_edema',
    label: 'Leg swelling',
    description: 'Puffiness, swelling, or fluid buildup in ankles, feet, or lower legs',
    iconType: 'footprint',
  },
];
