import axios from 'axios';

const getApiBaseUrl = () => {
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  if (typeof window !== 'undefined' && window.location) {
    return `${window.location.protocol}//${window.location.hostname}:8000/api/v1`;
  }
  return 'http://localhost:8000/api/v1';
};

const API_BASE_URL = getApiBaseUrl();

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to attach JWT token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Mutex state for refresh token rotation and concurrent 401 handling
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: any) => void;
}> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else if (token) {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Response interceptor to handle 401 Unauthorized with concurrency mutex
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      // If the 401 occurred on the refresh endpoint itself, immediately log out
      if (originalRequest.url?.includes('/auth/refresh') || originalRequest.url?.includes('/auth/login')) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }

      if (isRefreshing) {
        // Queue this request until the in-flight refresh completes
        return new Promise<string>((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((newToken) => {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            return apiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const res = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          const newAccessToken = res.data.access_token;
          const newRefreshToken = res.data.refresh_token;

          localStorage.setItem('access_token', newAccessToken);
          if (newRefreshToken) {
            localStorage.setItem('refresh_token', newRefreshToken);
          }
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;

          processQueue(null, newAccessToken);
          return apiClient(originalRequest);
        } catch (refreshErr) {
          processQueue(refreshErr, null);
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
            window.location.href = '/login';
          }
          return Promise.reject(refreshErr);
        } finally {
          isRefreshing = false;
        }
      } else {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

