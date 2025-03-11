import axios, { AxiosError, AxiosRequestConfig, AxiosResponse } from 'axios';
import { toast } from '@/components/ui/use-toast';
import { getSession } from 'next-auth/react';

// Create axios instance with default config
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Function to get auth token
const getAuthToken = async (): Promise<string | null> => {
  try {
    const session = await getSession();
    return session?.accessToken || null;
  } catch (error) {
    console.error('Error getting auth token:', error);
    return null;
  }
};

// Request interceptor to add auth token
api.interceptors.request.use(
  async (config) => {
    const token = await getAuthToken();
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Handle specific error statuses
    if (error.response) {
      const { status } = error.response;
      
      switch (status) {
        case 401:
          toast({
            title: 'Authentication Error',
            description: 'Your session has expired. Please sign in again.',
            variant: 'destructive',
          });
          // Redirect to login page or refresh token
          break;
          
        case 403:
          toast({
            title: 'Access Denied',
            description: 'You do not have permission to perform this action.',
            variant: 'destructive',
          });
          break;
          
        case 404:
          toast({
            title: 'Not Found',
            description: 'The requested resource was not found.',
            variant: 'destructive',
          });
          break;
          
        case 500:
        case 502:
        case 503:
        case 504:
          toast({
            title: 'Server Error',
            description: 'Something went wrong. Please try again later.',
            variant: 'destructive',
          });
          break;
          
        default:
          toast({
            title: 'Error',
            description: error.message || 'An unexpected error occurred.',
            variant: 'destructive',
          });
      }
    } else if (error.request) {
      // Network error or no response
      toast({
        title: 'Network Error',
        description: 'Unable to connect to the server. Please check your internet connection.',
        variant: 'destructive',
      });
    } else {
      // Something happened in setting up the request
      toast({
        title: 'Request Error',
        description: error.message || 'An error occurred while sending the request.',
        variant: 'destructive',
      });
    }
    
    return Promise.reject(error);
  }
);

// Generic request function with type safety
export const apiRequest = async <T = any>(
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH',
  url: string,
  data?: any,
  config?: AxiosRequestConfig
): Promise<T> => {
  try {
    let response: AxiosResponse<T>;
    
    switch (method) {
      case 'GET':
        response = await api.get<T>(url, { ...config, params: data });
        break;
      case 'POST':
        response = await api.post<T>(url, data, config);
        break;
      case 'PUT':
        response = await api.put<T>(url, data, config);
        break;
      case 'DELETE':
        response = await api.delete<T>(url, { ...config, data });
        break;
      case 'PATCH':
        response = await api.patch<T>(url, data, config);
        break;
      default:
        throw new Error(`Unsupported method: ${method}`);
    }
    
    return response.data;
  } catch (error) {
    // Error is already handled by the interceptor
    throw error;
  }
};

// Specific API endpoints as functions
interface ApiEndpoints {
  // Data sources
  getDataSources: () => Promise<any[]>;
  getDataSourceById: (id: string) => Promise<any>;
  createDataSource: (data: any) => Promise<any>;
  updateDataSource: (id: string, data: any) => Promise<any>;
  deleteDataSource: (id: string) => Promise<any>;
  
  // AI Models
  getModels: () => Promise<any[]>;
  getModelById: (id: string) => Promise<any>;
  createModel: (data: any) => Promise<any>;
  updateModel: (id: string, data: any) => Promise<any>;
  deleteModel: (id: string) => Promise<any>;
  
  // Projects
  getProjects: () => Promise<any[]>;
  getProjectById: (id: string) => Promise<any>;
  createProject: (data: any) => Promise<any>;
  updateProject: (id: string, data: any) => Promise<any>;
  deleteProject: (id: string) => Promise<any>;
  
  // Users
  getUsers: () => Promise<any[]>;
  getUserById: (id: string) => Promise<any>;
  createUser: (data: any) => Promise<any>;
  updateUser: (id: string, data: any) => Promise<any>;
  deleteUser: (id: string) => Promise<any>;
}

export const apiEndpoints: ApiEndpoints = {
  // Data sources
  getDataSources: () => apiRequest('GET', '/data-sources'),
  getDataSourceById: (id) => apiRequest('GET', `/data-sources/${id}`),
  createDataSource: (data) => apiRequest('POST', '/data-sources', data),
  updateDataSource: (id, data) => apiRequest('PUT', `/data-sources/${id}`, data),
  deleteDataSource: (id) => apiRequest('DELETE', `/data-sources/${id}`),
  
  // AI Models
  getModels: () => apiRequest('GET', '/models'),
  getModelById: (id) => apiRequest('GET', `/models/${id}`),
  createModel: (data) => apiRequest('POST', '/models', data),
  updateModel: (id, data) => apiRequest('PUT', `/models/${id}`, data),
  deleteModel: (id) => apiRequest('DELETE', `/models/${id}`),
  
  // Projects
  getProjects: () => apiRequest('GET', '/projects'),
  getProjectById: (id) => apiRequest('GET', `/projects/${id}`),
  createProject: (data) => apiRequest('POST', '/projects', data),
  updateProject: (id, data) => apiRequest('PUT', `/projects/${id}`, data),
  deleteProject: (id) => apiRequest('DELETE', `/projects/${id}`),
  
  // Users
  getUsers: () => apiRequest('GET', '/users'),
  getUserById: (id) => apiRequest('GET', `/users/${id}`),
  createUser: (data) => apiRequest('POST', '/users', data),
  updateUser: (id, data) => apiRequest('PUT', `/users/${id}`, data),
  deleteUser: (id) => apiRequest('DELETE', `/users/${id}`),
};

export default api;