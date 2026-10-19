/**
 * Authentication and Session Management Service.
 */

import { apiClient } from './apiClient';
import { AUTH_TOKEN_KEY, AUTH_USER_KEY } from '../utils/constants';

export const authService = {
  async register(payload) {
    const data = await apiClient.post('/auth/register', payload);
    if (data?.access_token) {
      localStorage.setItem(AUTH_TOKEN_KEY, data.access_token);
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify(data.user));
      window.dispatchEvent(new Event('auth:changed'));
    }
    return data;
  },

  async login(username, password) {
    const data = await apiClient.post('/auth/login', { username, password });
    if (data?.access_token) {
      localStorage.setItem(AUTH_TOKEN_KEY, data.access_token);
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify(data.user));
      window.dispatchEvent(new Event('auth:changed'));
    }
    return data;
  },

  async getMe() {
    return apiClient.get('/auth/me');
  },

  async deleteAccount(password) {
    const data = await apiClient.delete('/auth/me', { password });
    this.logout();
    return data;
  },

  logout() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
    window.dispatchEvent(new Event('auth:changed'));
  },

  getToken() {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  },

  getCurrentUser() {
    try {
      const raw = localStorage.getItem(AUTH_USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  isAuthenticated() {
    return Boolean(localStorage.getItem(AUTH_TOKEN_KEY));
  },
};
