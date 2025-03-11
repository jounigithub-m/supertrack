'use client';

import { API_ENDPOINTS } from './api-config';
import { getAccessToken } from './auth-utils';
import offlineService from '@/services/offline-service';

export type HttpMethod = 'get' | 'post' | 'put' | 'patch' | 'delete';

export interface RequestOptions {
  method?: HttpMethod;
  headers?: Record<string, string>;
  body?: any;
  cache?: RequestCache;
  next?: NextFetchRequestConfig;
  queryParams?: Record<string, string>;
  retry?: number;
  offlineOptions?: {
    enabled: boolean;
    priority?: number;
    expiration?: number; // in milliseconds
    uniqueId?: string;
  };
}

interface NextFetchRequestConfig {
  revalidate?: number | false;
  tags?: string[];
}

/**
 * Make an API request to the specified endpoint
 */
export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const {
    method = 'get',
    headers = {},
    body,
    cache,
    next,
    queryParams = {},
    retry = 2,
    offlineOptions = { enabled: true }
  } = options;

  // Check if we're offline and should queue this request
  if (
    offlineOptions.enabled && 
    offlineService && 
    typeof window !== 'undefined' && 
    !navigator.onLine && 
    method !== 'get'
  ) {
    // Queue this operation for when we're back online
    await offlineService.queueOperation({
      id: offlineOptions.uniqueId || `${method}-${endpoint}-${Date.now()}`,
      method,
      path: endpoint,
      body,
      headers,
      priority: offlineOptions.priority || 1,
      timestamp: Date.now(),
      expiration: offlineOptions.expiration || Date.now() + 7 * 24 * 60 * 60 * 1000, // Default 7 days
    });
    
    // For methods that modify data, we need to return a placeholder response
    // This allows the UI to continue as if the operation succeeded
    // The actual sync will happen when back online
    if (method !== 'get') {
      // Return a mock success response
      // The ID will be temporary until sync
      return {
        success: true,
        id: `offline-${Date.now()}`,
        _isOfflinePlaceholder: true
      } as unknown as T;
    }
  }

  // Determine if this endpoint requires authentication
  const endpointConfig = API_ENDPOINTS[endpoint];
  const requiresAuth = endpointConfig?.requiresAuth ?? true;

  // Build URL with query parameters
  const url = new URL(
    `${process.env.NEXT_PUBLIC_API_BASE_URL || ''}${endpoint}`,
    typeof window !== 'undefined' ? window.location.origin : undefined
  );
  
  // Add query parameters
  Object.entries(queryParams).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      url.searchParams.append(key, value);
    }
  });

  // Set headers
  const requestHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...headers,
  };

  // Add auth token if required
  if (requiresAuth) {
    const token = await getAccessToken();
    if (token) {
      requestHeaders['Authorization'] = `Bearer ${token}`;
    }
  }

  // Prepare request options
  const requestOptions: RequestInit = {
    method: method.toUpperCase(),
    headers: requestHeaders,
    cache,
    next,
  };

  // Add body for non-GET requests
  if (method !== 'get' && body !== undefined) {
    requestOptions.body = JSON.stringify(body);
  }

  let retryCount = 0;
  let error: Error | null = null;

  // Try request with retries
  while (retryCount <= retry) {
    try {
      // Check if we can use a cached response for GET requests when offline
      if (
        method === 'get' &&
        offlineOptions.enabled &&
        offlineService && 
        typeof window !== 'undefined' && 
        !navigator.onLine
      ) {
        const cachedResponse = await offlineService.getOfflineData(endpoint, queryParams);
        if (cachedResponse) {
          return cachedResponse as T;
        }
      }
      
      const response = await fetch(url.toString(), requestOptions);
      
      // Handle batch endpoint responses
      if (endpoint === '/api/v1/batch') {
        const responseData = await response.json();
        // For batch requests, we always return the full response
        // The caller is responsible for handling individual operation results
        return responseData as T;
      }
      
      // Handle non-batch responses
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          JSON.stringify({
            status: response.status,
            statusText: response.statusText,
            ...errorData,
          })
        );
      }

      const data = await response.json() as T;
      
      // Cache GET responses for offline use
      if (method === 'get' && offlineOptions.enabled && offlineService) {
        await offlineService.cacheResponse(endpoint, queryParams, data);
      }
      
      return data;
    } catch (err) {
      error = err instanceof Error ? err : new Error(String(err));
      retryCount++;
      
      if (retryCount <= retry) {
        // Exponential backoff
        await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, retryCount - 1)));
      }
    }
  }

  throw error;
}

/**
 * Batch multiple API requests into a single HTTP request
 */
export async function batchRequests<T = any[]>(
  operations: Array<{
    id: string;
    method: HttpMethod;
    path: string;
    body?: any;
  }>,
  options: RequestOptions = {}
): Promise<Array<{
  id: string;
  status: number;
  statusText: string;
  data?: any;
  error?: string;
}>> {
  return apiRequest<any>('/api/v1/batch', {
    method: 'post',
    body: { operations },
    ...options,
  });
}

export default {
  request: apiRequest,
  batch: batchRequests,
};