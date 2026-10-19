/**
 * Clinical Document Upload and Structured Lab Measurements Service.
 */

import { apiClient } from './apiClient';

export const reportService = {
  async uploadDocument(assessmentId, file, category = 'ecg_report_pdf') {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_category', category);

    return apiClient.post(`/assessments/${assessmentId}/documents`, formData);
  },

  async listDocuments(assessmentId) {
    return apiClient.get(`/assessments/${assessmentId}/documents`);
  },

  async downloadDocument(documentId) {
    return apiClient.get(`/documents/${documentId}/download`, { responseType: 'blob' });
  },

  async createLabMeasurement(assessmentId, payload) {
    return apiClient.post(`/assessments/${assessmentId}/labs`, payload);
  },

  async listLabMeasurements(assessmentId) {
    return apiClient.get(`/assessments/${assessmentId}/labs`);
  },
};
