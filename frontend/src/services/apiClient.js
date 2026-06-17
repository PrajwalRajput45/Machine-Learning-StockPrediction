import axios from 'axios';
import { useAuth } from '@clerk/clerk-react';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

let clerkToken = null;
let clerkUserId = null;

export function setClerkToken(token) {
  clerkToken = token;
}

export function setClerkUserId(userId) {
  clerkUserId = userId;
}

export function clearClerkToken() {
  clerkToken = null;
  clerkUserId = null;
}

apiClient.interceptors.request.use(
  async (config) => {
    if (clerkToken) {
      config.headers.Authorization = `Bearer ${clerkToken}`;
    }
    if (clerkUserId) {
      config.headers['X-Clerk-User-Id'] = clerkUserId;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      console.error('Authentication required');
    } else if (error.response?.status === 403) {
      console.error('Access denied');
    }
    return Promise.reject(error);
  }
);

export default apiClient;