/**
 * Clinical Assessment, Symptoms, and Vital Signs Service.
 */

import { apiClient } from './apiClient';

export const symptomService = {
  async getAssessment(id) {
    return apiClient.get(`/assessments/${id}`);
  },

  async updateAssessment(id, payload) {
    return apiClient.put(`/assessments/${id}`, payload);
  },

  async getSymptoms(assessmentId) {
    return apiClient.get(`/assessments/${assessmentId}/symptoms`);
  },

  async saveSymptoms(assessmentId, payload) {
    return apiClient.post(`/assessments/${assessmentId}/symptoms`, payload);
  },

  async getVitals(assessmentId) {
    return apiClient.get(`/assessments/${assessmentId}/vitals`);
  },

  async saveVitals(assessmentId, payload) {
    return apiClient.post(`/assessments/${assessmentId}/vitals`, payload);
  },
};
