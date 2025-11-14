import axios from 'axios';

export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 60000,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'Request failed';
    if (message) {
      error.message = message;
    }
    return Promise.reject(error);
  }
);
