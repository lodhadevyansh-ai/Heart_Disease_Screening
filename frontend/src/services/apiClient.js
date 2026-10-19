/**
 * Centralized API Client.
 * Connects frontend requests to the Flask REST API backend with token injection,
 * consistent response unwrapping, and standardized error normalization.
 */

import { API_BASE_URL, AUTH_TOKEN_KEY } from '../utils/constants';

class ApiError extends Error {
  constructor(message, status, details = null, errorName = 'ApiError') {
    super(message);
    this.name = errorName;
    this.status = status;
    this.details = details;
  }
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = { ...options.headers };

  // Attach JWT Bearer token if present
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Set JSON content-type if body is JSON string and not FormData
  if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const config = {
    ...options,
    headers,
  };

  let response;
  try {
    response = await fetch(url, config);
  } catch {
    throw new ApiError(
      'Unable to connect to the CardioCare server. Please verify the backend service is running.',
      0,
      null,
      'NetworkError'
    );
  }

  // Handle file download streams directly
  if (options.responseType === 'blob') {
    if (!response.ok) {
      throw new ApiError('Failed to download document from repository.', response.status);
    }
    return response.blob();
  }

  let jsonResult;
  try {
    jsonResult = await response.json();
  } catch {
    jsonResult = null;
  }

  if (!response.ok) {
    const errorObj = jsonResult?.error || {};
    const message = errorObj.message || jsonResult?.message || `Server responded with HTTP ${response.status}`;
    const details = errorObj.details || null;
    const errorName = errorObj.name || 'RequestError';

    // Auto-clear invalid/expired session
    if (response.status === 401 && token) {
      localStorage.removeItem(AUTH_TOKEN_KEY);
      // Dispatch custom event for session expiry
      window.dispatchEvent(new Event('auth:expired'));
    }

    throw new ApiError(message, response.status, details, errorName);
  }

  return jsonResult?.data !== undefined ? jsonResult.data : jsonResult;
}

export const apiClient = {
  get: (endpoint, options = {}) => request(endpoint, { ...options, method: 'GET' }),
  post: (endpoint, body, options = {}) =>
    request(endpoint, {
      ...options,
      method: 'POST',
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),
  put: (endpoint, body, options = {}) =>
    request(endpoint, {
      ...options,
      method: 'PUT',
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),
  delete: (endpoint, body = null, options = {}) => {
    const opts = { ...options, method: 'DELETE' };
    if (body !== null && typeof body === 'object' && !(body.headers || body.method)) {
      opts.body = body instanceof FormData ? body : JSON.stringify(body);
    } else if (body !== null && (body.headers || body.method)) {
      // Called with (endpoint, options) format
      Object.assign(opts, body);
    }
    return request(endpoint, opts);
  },
};

export { ApiError };
