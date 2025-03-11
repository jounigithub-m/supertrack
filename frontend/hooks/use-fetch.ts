import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '@/lib/api';
import { useToast } from '@/components/ui/use-toast';

/**
 * Options for the useFetch hook
 */
export interface UseFetchOptions<T> {
  /**
   * Initial data to use before fetch completes
   */
  initialData?: T;
  
  /**
   * Whether to fetch data immediately on mount
   * @default true
   */
  fetchOnMount?: boolean;
  
  /**
   * Dependencies array to trigger refetch when changed
   */
  deps?: any[];
  
  /**
   * Custom error handler
   */
  onError?: (error: any) => void;
  
  /**
   * Custom success handler
   */
  onSuccess?: (data: T) => void;
  
  /**
   * Whether to show toast messages on error
   * @default true
   */
  showErrorToast?: boolean;
}

/**
 * Custom hook for fetching data from the API
 * 
 * @template T The type of data being fetched
 */
export function useFetch<T = any>(
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH',
  url: string,
  options: UseFetchOptions<T> = {}
) {
  const {
    initialData,
    fetchOnMount = true,
    deps = [],
    onError,
    onSuccess,
    showErrorToast = true,
  } = options;
  
  const { toast } = useToast();
  const [data, setData] = useState<T | undefined>(initialData);
  const [isLoading, setIsLoading] = useState<boolean>(fetchOnMount);
  const [error, setError] = useState<any>(null);
  
  // Fetch function that can be called manually
  const fetchData = useCallback(async (requestData?: any) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const result = await apiRequest<T>(method, url, requestData);
      setData(result);
      
      if (onSuccess) {
        onSuccess(result);
      }
      
      return result;
    } catch (err: any) {
      setError(err);
      
      if (onError) {
        onError(err);
      }
      
      if (showErrorToast) {
        toast({
          title: 'Error fetching data',
          description: err.message || 'An unexpected error occurred',
          variant: 'destructive',
        });
      }
      
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [method, url, onSuccess, onError, showErrorToast, toast]);
  
  // Fetch data when dependencies change
  useEffect(() => {
    if (fetchOnMount) {
      fetchData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchOnMount, ...deps]);
  
  // Function to manually reset the state
  const reset = useCallback(() => {
    setData(initialData);
    setIsLoading(false);
    setError(null);
  }, [initialData]);
  
  // Function to manually update the data
  const updateData = useCallback((newData: T) => {
    setData(newData);
  }, []);
  
  return {
    data,
    isLoading,
    error,
    fetchData,
    reset,
    updateData,
  };
}

export default useFetch;