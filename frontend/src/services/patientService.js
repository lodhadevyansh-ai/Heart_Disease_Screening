/**
 * Patient Profiles and Clinical Encounter Service.
 */

import { apiClient } from './apiClient';

export const patientService = {
  async listPatients(params = {}) {
    const query = new URLSearchParams();
    if (params.page) query.append('page', params.page);
    if (params.per_page) query.append('per_page', params.per_page);
    if (params.search) query.append('search', params.search);
    if (params.sex) query.append('sex', params.sex);

    const qs = query.toString();
    return apiClient.get(`/patients${qs ? '?' + qs : ''}`);
  },

  async getPatient(id) {
    return apiClient.get(`/patients/${id}`);
  },

  async createPatient(payload) {
    return apiClient.post('/patients', payload);
  },

  async updatePatient(id, payload) {
    return apiClient.put(`/patients/${id}`, payload);
  },

  async listAssessments(patientId) {
    return apiClient.get(`/patients/${patientId}/assessments`);
  },

  async createAssessment(patientId, payload = {}) {
    return apiClient.post(`/patients/${patientId}/assessments`, payload);
  },
};
