import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { getSession, signOut } from 'next-auth/react';

// API response types
export interface ApiResponse<T> {
  data: T;
  status: number;
  statusText: string;
  headers: Record<string, string>;
}

export interface ApiError {
  message: string;
  code?: string;
  status?: number;
  errors?: Record<string, string[]>;
  originalError?: unknown;
}

// Request configuration with retry options
export interface RequestConfig extends AxiosRequestConfig {
  retry?: boolean;
  retryCount?: number;
  retryDelay?: number;
  skipAuthRefresh?: boolean;
}

// Constants
const MAX_RETRY_COUNT = 3;
const RETRY_DELAY_MS = 1000;
const AUTH_ERROR_CODES = [401, 403];

/**
 * Create and configure the API client with interceptors for authentication,
 * error handling, and request retries.
 */
export function createApiClient(): AxiosInstance {
  // Create axios instance with default config
  const apiClient = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || '/api',
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Request interceptor for authentication
  apiClient.interceptors.request.use(
    async (config) => {
      // Clone the config to avoid mutating the original
      const newConfig = { ...config };

      // Skip auth for login/register endpoints or if skipAuthRefresh is true
      if (
        newConfig.url?.includes('auth/signin') ||
        newConfig.url?.includes('auth/signup') ||
        newConfig.skipAuthRefresh
      ) {
        return newConfig;
      }

      try {
        // Get the session for auth token
        const session = await getSession();
        
        if (session?.accessToken) {
          // Set the auth header with token
          newConfig.headers = newConfig.headers || {};
          newConfig.headers.Authorization = `Bearer ${session.accessToken}`;
        }
      } catch (error) {
        console.error('Error getting auth token:', error);
      }

      return newConfig;
    },
    (error) => Promise.reject(error)
  );

  // Response interceptor for error handling
  apiClient.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const originalRequest = error.config as RequestConfig;
      
      // Handle authentication errors
      if (
        error.response &&
        AUTH_ERROR_CODES.includes(error.response.status) &&
        !originalRequest.skipAuthRefresh
      ) {
        try {
          // If it's an auth error, try to sign out
          // A real implementation might try to refresh the token instead
          await signOut({ redirect: false });
          
          // Redirect to login page
          window.location.href = '/signin';
          
          return Promise.reject(formatApiError(error));
        } catch (refreshError) {
          return Promise.reject(formatApiError(refreshError));
        }
      }

      // Handle retry logic
      if (
        originalRequest &&
        originalRequest.retry !== false &&
        (!error.response || error.response.status >= 500) &&
        (originalRequest.retryCount || 0) < (originalRequest.retryCount || MAX_RETRY_COUNT)
      ) {
        originalRequest.retryCount = (originalRequest.retryCount || 0) + 1;
        
        // Wait before retrying
        const delay = originalRequest.retryDelay || RETRY_DELAY_MS;
        await new Promise((resolve) => setTimeout(resolve, delay * originalRequest.retryCount!));
        
        // Retry the request
        return apiClient(originalRequest);
      }

      // Format error before rejecting
      return Promise.reject(formatApiError(error));
    }
  );

  return apiClient;
}

/**
 * Format API errors into a consistent structure
 */
export function formatApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const response = error.response;
    
    // Try to extract API error information from response
    if (response?.data) {
      const apiError = response.data as any;
      
      return {
        message: apiError.message || apiError.error || 'An error occurred',
        code: apiError.code || `HTTP_${response.status}`,
        status: response.status,
        errors: apiError.errors || undefined,
        originalError: error,
      };
    }
    
    // Handle network errors
    if (error.request && !response) {
      return {
        message: 'Network error. Please check your connection and try again.',
        code: 'NETWORK_ERROR',
        originalError: error,
      };
    }
    
    // Generic axios error
    return {
      message: error.message || 'An error occurred',
      code: 'AXIOS_ERROR',
      originalError: error,
    };
  }
  
  // Handle non-axios errors
  if (error instanceof Error) {
    return {
      message: error.message || 'An unknown error occurred',
      code: 'UNKNOWN_ERROR',
      originalError: error,
    };
  }
  
  // Fallback for truly unknown errors
  return {
    message: 'An unknown error occurred',
    code: 'UNKNOWN_ERROR',
    originalError: error,
  };
}

// Create singleton instance
const apiClient = createApiClient();

/**
 * Make an API request with error handling and type safety
 */
export async function apiRequest<T = any>(
  method: string,
  url: string,
  data?: any,
  config?: RequestConfig
): Promise<ApiResponse<T>> {
  try {
    const response = await apiClient({
      method,
      url,
      data: method !== 'get' ? data : undefined,
      params: method === 'get' ? data : undefined,
      ...config,
    });
    
    return {
      data: response.data,
      status: response.status,
      statusText: response.statusText,
      headers: response.headers as Record<string, string>,
    };
  } catch (error) {
    // The error is already formatted by the interceptor
    throw error;
  }
}

// Convenient method wrappers
export const api = {
  get: <T = any>(url: string, params?: any, config?: RequestConfig) => 
    apiRequest<T>('get', url, params, config),
  post: <T = any>(url: string, data?: any, config?: RequestConfig) => 
    apiRequest<T>('post', url, data, config),
  put: <T = any>(url: string, data?: any, config?: RequestConfig) => 
    apiRequest<T>('put', url, data, config),
  patch: <T = any>(url: string, data?: any, config?: RequestConfig) => 
    apiRequest<T>('patch', url, data, config),
  delete: <T = any>(url: string, config?: RequestConfig) => 
    apiRequest<T>('delete', url, config),
};

export default api;