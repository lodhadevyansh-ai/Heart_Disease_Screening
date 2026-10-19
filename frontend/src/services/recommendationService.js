/**
 * Clinical Safety and Diagnostic Recommendations Service.
 */

import { apiClient } from './apiClient';

export const recommendationService = {
  async evaluateAdHoc(payload) {
    return apiClient.post('/recommendations/evaluate', payload);
  },

  async evaluateAssessment(assessmentId) {
    return apiClient.get(`/assessments/${assessmentId}/recommendations`);
  },
};
