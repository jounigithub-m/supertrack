/**
 * API endpoint configuration
 * 
 * This file centralizes all API endpoint definitions and configurations.
 * It provides structured access to API routes and their properties.
 */

// API version prefix
export const API_VERSION = 'v1';

// Base paths for different API domains
const PATHS = {
  AUTH: `/api/${API_VERSION}/auth`,
  MODELS: `/api/${API_VERSION}/models`,
  PROJECTS: `/api/${API_VERSION}/projects`,
  DATA_SOURCES: `/api/${API_VERSION}/data-sources`,
  USERS: `/api/${API_VERSION}/users`,
  ANALYTICS: `/api/${API_VERSION}/analytics`,
} as const;

// Endpoint configuration interface
interface EndpointConfig {
  // The full path to the endpoint
  path: string;
  // Whether the endpoint requires authentication
  requiresAuth: boolean;
  // Cache TTL in seconds (if applicable)
  cacheTTL?: number;
  // Retry configuration
  retry?: {
    // Maximum number of retry attempts
    maxAttempts: number;
    // Base delay between retries in milliseconds
    baseDelay: number;
  };
}

// Creates an endpoint configuration
function createEndpoint(
  path: string,
  requiresAuth = true,
  cacheTTL?: number,
  retry?: EndpointConfig['retry']
): EndpointConfig {
  return {
    path,
    requiresAuth,
    cacheTTL,
    retry: retry || (requiresAuth ? { maxAttempts: 3, baseDelay: 1000 } : undefined),
  };
}

// Authentication endpoints
export const AUTH = {
  SIGNIN: createEndpoint(`${PATHS.AUTH}/signin`, false),
  SIGNUP: createEndpoint(`${PATHS.AUTH}/signup`, false),
  SIGNOUT: createEndpoint(`${PATHS.AUTH}/signout`),
  REFRESH_TOKEN: createEndpoint(`${PATHS.AUTH}/refresh-token`),
  FORGOT_PASSWORD: createEndpoint(`${PATHS.AUTH}/forgot-password`, false),
  RESET_PASSWORD: createEndpoint(`${PATHS.AUTH}/reset-password`, false),
  VERIFY_EMAIL: createEndpoint(`${PATHS.AUTH}/verify-email`, false),
};

// Model endpoints
export const MODELS = {
  LIST: createEndpoint(`${PATHS.MODELS}`, true, 60), // Cache for 1 minute
  GET: (id: string) => createEndpoint(`${PATHS.MODELS}/${id}`, true, 60),
  CREATE: createEndpoint(`${PATHS.MODELS}`),
  UPDATE: (id: string) => createEndpoint(`${PATHS.MODELS}/${id}`),
  DELETE: (id: string) => createEndpoint(`${PATHS.MODELS}/${id}`),
  TRAIN: (id: string) => createEndpoint(`${PATHS.MODELS}/${id}/train`),
  METRICS: (id: string) => createEndpoint(`${PATHS.MODELS}/${id}/metrics`, true, 300), // Cache for 5 minutes
  VERSIONS: (id: string) => createEndpoint(`${PATHS.MODELS}/${id}/versions`, true, 300),
};

// Project endpoints
export const PROJECTS = {
  LIST: createEndpoint(`${PATHS.PROJECTS}`, true, 60),
  GET: (id: string) => createEndpoint(`${PATHS.PROJECTS}/${id}`, true, 60),
  CREATE: createEndpoint(`${PATHS.PROJECTS}`),
  UPDATE: (id: string) => createEndpoint(`${PATHS.PROJECTS}/${id}`),
  DELETE: (id: string) => createEndpoint(`${PATHS.PROJECTS}/${id}`),
  ADD_MODEL: (id: string) => createEndpoint(`${PATHS.PROJECTS}/${id}/models`),
  REMOVE_MODEL: (id: string, modelId: string) => createEndpoint(`${PATHS.PROJECTS}/${id}/models/${modelId}`),
  ADD_MEMBER: (id: string) => createEndpoint(`${PATHS.PROJECTS}/${id}/members`),
  REMOVE_MEMBER: (id: string, userId: string) => createEndpoint(`${PATHS.PROJECTS}/${id}/members/${userId}`),
  ANALYTICS: (id: string) => createEndpoint(`${PATHS.PROJECTS}/${id}/analytics`, true, 300),
};

// Data source endpoints
export const DATA_SOURCES = {
  LIST: createEndpoint(`${PATHS.DATA_SOURCES}`, true, 60),
  GET: (id: string) => createEndpoint(`${PATHS.DATA_SOURCES}/${id}`, true, 60),
  CREATE: createEndpoint(`${PATHS.DATA_SOURCES}`),
  UPDATE: (id: string) => createEndpoint(`${PATHS.DATA_SOURCES}/${id}`),
  DELETE: (id: string) => createEndpoint(`${PATHS.DATA_SOURCES}/${id}`),
  REFRESH: (id: string) => createEndpoint(`${PATHS.DATA_SOURCES}/${id}/refresh`),
  SCHEMA: (id: string) => createEndpoint(`${PATHS.DATA_SOURCES}/${id}/schema`, true, 600), // Cache for 10 minutes
  PREVIEW: (id: string) => createEndpoint(`${PATHS.DATA_SOURCES}/${id}/preview`, true, 600),
  VALIDATE: createEndpoint(`${PATHS.DATA_SOURCES}/validate`, true),
};

// User endpoints
export const USERS = {
  ME: createEndpoint(`${PATHS.USERS}/me`, true, 300),
  LIST: createEndpoint(`${PATHS.USERS}`, true, 60),
  GET: (id: string) => createEndpoint(`${PATHS.USERS}/${id}`, true, 60),
  UPDATE_PROFILE: createEndpoint(`${PATHS.USERS}/me`),
  UPDATE_PASSWORD: createEndpoint(`${PATHS.USERS}/me/password`),
  PREFERENCES: createEndpoint(`${PATHS.USERS}/me/preferences`, true, 300),
  UPDATE_PREFERENCES: createEndpoint(`${PATHS.USERS}/me/preferences`),
};

// Analytics endpoints
export const ANALYTICS = {
  DASHBOARD: createEndpoint(`${PATHS.ANALYTICS}/dashboard`, true, 300),
  MODEL_PERFORMANCE: createEndpoint(`${PATHS.ANALYTICS}/model-performance`, true, 300),
  PROJECT_METRICS: createEndpoint(`${PATHS.ANALYTICS}/project-metrics`, true, 300),
  USAGE_STATS: createEndpoint(`${PATHS.ANALYTICS}/usage`, true, 60),
  EXPORT: createEndpoint(`${PATHS.ANALYTICS}/export`),
};

// All API endpoints grouped by domain
export const API_ENDPOINTS = {
  AUTH,
  MODELS,
  PROJECTS,
  DATA_SOURCES,
  USERS,
  ANALYTICS,
};

export default API_ENDPOINTS;