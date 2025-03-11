import { useState, useEffect, useCallback } from 'react';
import api, { ApiError, RequestConfig } from '@/lib/api-client';
import { handleError } from '@/lib/error-handler';
import API_ENDPOINTS from '@/lib/api-config';

export interface UseFetchOptions<T> {
  initialData?: T;
  fetchOnMount?: boolean;
  dependencies?: any[];
  onSuccess?: (data: T) => void;
  onError?: (error: ApiError) => void;
  shouldCache?: boolean;
  cacheKey?: string;
  cacheTTL?: number; // Time to live in seconds
}

// Simple in-memory cache
interface CacheItem<T> {
  data: T;
  timestamp: number;
  ttl: number; // Time to live in milliseconds
}

const cache = new Map<string, CacheItem<any>>();

/**
 * A custom hook for data fetching that handles loading, error states, and caching
 * 
 * @param method HTTP method (get, post, put, patch, delete)
 * @param url API endpoint URL
 * @param defaultParams Default parameters to send with the request
 * @param options Configuration options
 * @returns Object containing data, loading state, error, and fetch function
 */
export function useFetch<T = any, P = any>(
  method: 'get' | 'post' | 'put' | 'patch' | 'delete',
  url: string,
  defaultParams?: P,
  options: UseFetchOptions<T> = {}
) {
  // Extract options with defaults
  const {
    initialData,
    fetchOnMount = true,
    dependencies = [],
    onSuccess,
    onError,
    shouldCache = method === 'get',
    cacheKey = url,
    cacheTTL = 60, // Default: 1 minute
  } = options;

  // State for data, loading, and error
  const [data, setData] = useState<T | undefined>(initialData);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<ApiError | null>(null);

  // Check if there's a valid cached item
  const getCachedItem = useCallback(() => {
    if (!shouldCache || !cacheKey) return null;
    
    const cachedItem = cache.get(cacheKey);
    if (!cachedItem) return null;
    
    // Check if cache is still valid
    const now = Date.now();
    if (now - cachedItem.timestamp > cachedItem.ttl) {
      // Cache expired, remove it
      cache.delete(cacheKey);
      return null;
    }
    
    return cachedItem.data as T;
  }, [shouldCache, cacheKey]);

  // Cache data with TTL
  const cacheData = useCallback((data: T) => {
    if (shouldCache && cacheKey) {
      cache.set(cacheKey, {
        data,
        timestamp: Date.now(),
        ttl: cacheTTL * 1000, // Convert to milliseconds
      });
    }
  }, [shouldCache, cacheKey, cacheTTL]);

  // The main fetch function
  const fetchData = useCallback(async (params?: P, config?: RequestConfig): Promise<T | undefined> => {
    // Check cache first (for GET requests)
    if (method === 'get' && !params) {
      const cachedData = getCachedItem();
      if (cachedData) {
        setData(cachedData);
        return cachedData;
      }
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      // Use our API client to make the request
      const mergedParams = { ...defaultParams, ...params } as P;
      
      // Find the endpoint config if possible
      let endpoint = Object.values(API_ENDPOINTS)
        .flatMap(domain => Object.values(domain))
        .find(endpoint => {
          if (typeof endpoint === 'function') return false;
          return endpoint.path === url;
        });
      
      // If endpoint was not found directly, look for dynamic endpoints
      if (!endpoint) {
        // This is a simplification; in a real app you might need more sophisticated matching
        endpoint = Object.values(API_ENDPOINTS)
          .flatMap(domain => Object.values(domain))
          .find(ep => {
            if (typeof ep === 'function') {
              // Try calling with a placeholder to see if it matches
              const dynamicEndpoint = ep('id');
              return dynamicEndpoint.path.replace('/id', '') === url.replace(/\/[^/]+$/, '');
            }
            return false;
          });
      }
      
      // Apply endpoint configuration if available
      const endpointConfig = endpoint && typeof endpoint !== 'function' ? {
        retry: endpoint.retry?.maxAttempts !== undefined,
        retryCount: endpoint.retry?.maxAttempts,
        retryDelay: endpoint.retry?.baseDelay,
      } : {};
      
      // Make the API request
      const response = await api[method]<T>(url, method === 'get' ? mergedParams : undefined, {
        ...(method !== 'get' ? { data: mergedParams } : {}),
        ...endpointConfig,
        ...config,
      });
      
      const result = response.data;
      
      // Update state with the result
      setData(result);
      
      // Cache the result if it's a GET request
      if (method === 'get') {
        cacheData(result);
      }
      
      // Call onSuccess callback if provided
      if (onSuccess) {
        onSuccess(result);
      }
      
      return result;
    } catch (err) {
      // Format and handle the error
      const apiError = err as ApiError;
      setError(apiError);
      
      // Call onError callback if provided
      if (onError) {
        onError(apiError);
      } else {
        // Use the global error handler by default
        handleError(apiError, { method, url, params });
      }
      
      return undefined;
    } finally {
      setIsLoading(false);
    }
  }, [method, url, defaultParams, onSuccess, onError, cacheData, getCachedItem]);

  // Fetch data on mount and when dependencies change
  useEffect(() => {
    if (fetchOnMount) {
      fetchData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchOnMount, ...dependencies]);

  // Clear cache for this endpoint
  const invalidateCache = useCallback(() => {
    if (cacheKey) {
      cache.delete(cacheKey);
    }
  }, [cacheKey]);
  
  // Clear all cached data
  const clearAllCache = useCallback(() => {
    cache.clear();
  }, []);

  return {
    data,
    isLoading,
    error,
    fetch: fetchData,
    invalidateCache,
    clearAllCache,
  };
}

export default useFetch;