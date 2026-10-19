/**
 * Machine Learning Inference and Audit History Service.
 */

import { apiClient } from './apiClient';

export const predictionService = {
  async getTaskCatalog() {
    return apiClient.get('/predictions/tasks');
  },

  async runPrediction(assessmentId, payload) {
    return apiClient.post(`/assessments/${assessmentId}/predictions`, payload);
  },

  async getPredictionHistory(assessmentId) {
    return apiClient.get(`/assessments/${assessmentId}/predictions`);
  },

  async getPredictionById(predictionId) {
    return apiClient.get(`/predictions/${predictionId}`);
  },

  async getTaskReadiness(assessmentId) {
    return apiClient.get(`/assessments/${assessmentId}/readiness`);
  },
};

