import axios, { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { getAccessToken, setAccessToken, refresh } from "./auth";
import { getApiBaseUrl } from "./config";
import { getTenantFromHost } from "./tenant";

// Define API error interface for Django backend
interface APIError {
  message?: string;
  detail?: string;
  non_field_errors?: string[];
  [key: string]: unknown;
}

// Enhanced error class for API errors
export class APIException extends Error {
  public status: number;
  public data: APIError;
  public isAPIError = true;

  constructor(status: number, data: APIError, originalError?: AxiosError) {
    const message = data.detail || data.message || data.non_field_errors?.[0] || 'An error occurred';
    super(message);
    this.name = 'APIException';
    this.status = status;
    this.data = data;
  }
}

const api = axios.create({
  baseURL: getApiBaseUrl(),
  withCredentials: true, // allow refresh cookie
});

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  const tenant = getTenantFromHost();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  if (tenant) {
    config.headers["X-Tenancy-Mode"] = "header";
    config.headers["X-Tenant-Id"] = tenant;
  }
  return config;
});

let refreshing = false;
let queue: Array<() => void> = [];

api.interceptors.response.use(
  (res: AxiosResponse) => res,
  async (err: AxiosError) => {
    const original = err.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;

    // Handle 401 Unauthorized - attempt token refresh
    if (err?.response?.status === 401 && original && !original._retry) {
      original._retry = true;
      if (!refreshing) {
        refreshing = true;
        try {
          const newToken = await refresh(); // calls /auth/refresh, httpOnly cookie provides refresh
          setAccessToken(newToken);
          queue.forEach((fn) => fn());
          queue = [];
        } catch (refreshError) {
          // Refresh failed - redirect to login or handle appropriately
          console.error('Token refresh failed:', refreshError);
          // Clear any stored tokens
          setAccessToken('');
          // In a real app, you might redirect to login here
          if (typeof window !== 'undefined') {
            window.location.href = '/login';
          }
        } finally {
          refreshing = false;
        }
      }
      return new Promise((resolve) => {
        queue.push(() => resolve(api(original)));
      });
    }
    
    // Enhanced error handling for different status codes
    if (err.response) {
      const { status, data } = err.response;
      
      // Log errors in development
      if (process.env.NODE_ENV === 'development') {
        console.group(`🚨 API Error ${status}`);
        console.error('URL:', err.config?.url);
        console.error('Method:', err.config?.method?.toUpperCase());
        console.error('Status:', status);
        console.error('Data:', data);
        console.error('Headers:', err.config?.headers);
        console.groupEnd();
      }
      
      // Create structured API exception
      const apiError = new APIException(status, data as APIError, err);
      
      // Handle specific status codes
      switch (status) {
        case 400:
          // Bad Request - validation errors
          console.warn('Validation error:', data);
          break;
        case 403:
          // Forbidden - insufficient permissions
          console.warn('Access denied:', data);
          break;
        case 404:
          // Not Found
          console.warn('Resource not found:', err.config?.url);
          break;
        case 429:
          // Rate Limited
          console.warn('Rate limited - please slow down requests');
          break;
        case 500:
          // Internal Server Error
          console.error('Server error - please try again later');
          break;
        case 502:
        case 503:
        case 504:
          // Service unavailable
          console.error('Service temporarily unavailable');
          break;
        default:
          console.error('Unexpected error:', status, data);
      }
      
      return Promise.reject(apiError);
    } else if (err.request) {
      // Network error
      console.error('Network error - check your connection');
      const networkError = new APIException(0, { 
        message: 'Network error - please check your connection and try again'
      }, err);
      return Promise.reject(networkError);
    } else {
      // Request setup error
      console.error('Request setup error:', err.message);
      const setupError = new APIException(0, { 
        message: 'Request setup error - please try again'
      }, err);
      return Promise.reject(setupError);
    }
  }
);

// Utility functions for error handling
export const isAPIError = (error: unknown): error is APIException => {
  return (
    typeof error === 'object' &&
    error !== null &&
    (error as { isAPIError?: boolean }).isAPIError === true
  );
};

export const getErrorMessage = (error: unknown): string => {
  if (isAPIError(error)) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === 'string') {
    return error;
  }
  return 'An unexpected error occurred';
};

export const getValidationErrors = (error: unknown): Record<string, string[]> => {
  if (isAPIError(error) && error.status === 400) {
    const errors: Record<string, string[]> = {};
    Object.keys(error.data).forEach(key => {
      if (key !== 'detail' && key !== 'message') {
        const value = error.data[key];
        if (Array.isArray(value)) {
          errors[key] = value;
        } else if (typeof value === 'string') {
          errors[key] = [value];
        }
      }
    });
    return errors;
  }
  return {};
};

// Export both default and named exports for flexibility
export { api };
export default api;
