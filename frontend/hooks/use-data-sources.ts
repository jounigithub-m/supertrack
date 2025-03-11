import { useState, useCallback } from 'react';
import useFetch from './use-fetch';
import API_ENDPOINTS from '@/lib/api-config';
import { handleError } from '@/lib/error-handler';

// Type definitions
export type DataSourceStatus = 'connected' | 'disconnected' | 'pending' | 'error';
export type DataSourceType = 'database' | 'csv' | 'api' | 'warehouse' | 'streaming';

export interface DataSource {
  id: string;
  name: string;
  type: DataSourceType;
  size: number;
  rowCount?: number;
  lastUpdated: string;
  status: DataSourceStatus;
  connectionDetails: {
    host?: string;
    port?: string;
    username?: string;
    database?: string;
    table?: string;
    filePath?: string;
    apiUrl?: string;
    apiKey?: string;
    [key: string]: any;
  };
  createdAt: string;
  updatedAt: string;
  createdBy: string;
}

export interface CreateDataSourceInput {
  name: string;
  type: DataSourceType;
  connectionDetails: {
    host?: string;
    port?: string;
    username?: string;
    password?: string;
    database?: string;
    table?: string;
    filePath?: string;
    apiUrl?: string;
    apiKey?: string;
    [key: string]: any;
  };
}

export interface UpdateDataSourceInput {
  name?: string;
  connectionDetails?: {
    host?: string;
    port?: string;
    username?: string;
    password?: string;
    database?: string;
    table?: string;
    filePath?: string;
    apiUrl?: string;
    apiKey?: string;
    [key: string]: any;
  };
}

// Mock data for development and testing
// This will be used until the API is fully implemented
const MOCK_DATA_SOURCES: DataSource[] = [
  {
    id: 'ds-001',
    name: 'Customer Database',
    type: 'database',
    size: 2560000000, // 2.56 GB
    rowCount: 5000000,
    lastUpdated: '2024-02-28T10:15:30Z',
    status: 'connected',
    connectionDetails: {
      host: 'customer-db.example.com',
      port: '5432',
      username: 'readonly_user',
      database: 'customer_data',
      table: 'customers'
    },
    createdAt: '2023-10-15T08:20:10Z',
    updatedAt: '2024-02-28T10:15:30Z',
    createdBy: 'user-001'
  },
  {
    id: 'ds-002',
    name: 'Sales Transactions',
    type: 'database',
    size: 4200000000, // 4.2 GB
    rowCount: 8500000,
    lastUpdated: '2024-03-01T14:30:00Z',
    status: 'connected',
    connectionDetails: {
      host: 'sales-db.example.com',
      port: '3306',
      username: 'analytics_user',
      database: 'sales_data',
      table: 'transactions'
    },
    createdAt: '2023-09-20T13:45:25Z',
    updatedAt: '2024-03-01T14:30:00Z',
    createdBy: 'user-002'
  },
  {
    id: 'ds-003',
    name: 'Customer Behavior Analytics',
    type: 'csv',
    size: 450000000, // 450 MB
    rowCount: 2000000,
    lastUpdated: '2024-02-15T09:10:45Z',
    status: 'connected',
    connectionDetails: {
      filePath: 's3://analytics-bucket/customer-behavior/latest.csv'
    },
    createdAt: '2023-12-05T16:30:20Z',
    updatedAt: '2024-02-15T09:10:45Z',
    createdBy: 'user-001'
  },
  {
    id: 'ds-004',
    name: 'Customer Feedback Data',
    type: 'api',
    size: 125000000, // 125 MB
    lastUpdated: '2024-02-20T11:20:15Z',
    status: 'connected',
    connectionDetails: {
      apiUrl: 'https://api.feedback.example.com/v1/data',
      apiKey: '[REDACTED]'
    },
    createdAt: '2024-01-10T14:25:30Z',
    updatedAt: '2024-02-20T11:20:15Z',
    createdBy: 'user-003'
  },
  {
    id: 'ds-005',
    name: 'Fraud Detection Data',
    type: 'streaming',
    size: 1800000000, // 1.8 GB
    lastUpdated: '2024-03-02T08:45:10Z',
    status: 'connected',
    connectionDetails: {
      host: 'kafka.example.com',
      port: '9092',
      topic: 'transaction-events'
    },
    createdAt: '2023-11-22T10:15:45Z',
    updatedAt: '2024-03-02T08:45:10Z',
    createdBy: 'user-003'
  },
  {
    id: 'ds-006',
    name: 'Image Database',
    type: 'warehouse',
    size: 5600000000, // 5.6 GB
    lastUpdated: '2024-02-25T16:30:00Z',
    status: 'disconnected',
    connectionDetails: {
      host: 'data-warehouse.example.com',
      port: '443',
      username: 'images_user',
      database: 'product_images'
    },
    createdAt: '2023-10-30T12:40:50Z',
    updatedAt: '2024-02-25T16:30:00Z',
    createdBy: 'user-002'
  },
  {
    id: 'ds-007',
    name: 'Inventory Data',
    type: 'database',
    size: 350000000, // 350 MB
    rowCount: 1000000,
    lastUpdated: '2024-02-10T10:05:30Z',
    status: 'error',
    connectionDetails: {
      host: 'inventory-db.example.com',
      port: '5432',
      username: 'readonly_user',
      database: 'inventory',
      table: 'stock_levels'
    },
    createdAt: '2023-12-15T09:25:15Z',
    updatedAt: '2024-02-10T10:05:30Z',
    createdBy: 'user-001'
  },
  {
    id: 'ds-008',
    name: 'New Data Source',
    type: 'csv',
    size: 0,
    lastUpdated: '2024-03-01T12:00:00Z',
    status: 'pending',
    connectionDetails: {
      filePath: 'preparing'
    },
    createdAt: '2024-03-01T12:00:00Z',
    updatedAt: '2024-03-01T12:00:00Z',
    createdBy: 'user-001'
  }
];

// Mock schema for a data source
const MOCK_SCHEMA = [
  { name: 'id', type: 'integer' },
  { name: 'first_name', type: 'string' },
  { name: 'last_name', type: 'string' },
  { name: 'email', type: 'string' },
  { name: 'gender', type: 'string' },
  { name: 'ip_address', type: 'string' },
  { name: 'created_at', type: 'timestamp' },
  { name: 'last_login', type: 'timestamp' },
  { name: 'account_balance', type: 'decimal(10,2)' },
  { name: 'is_active', type: 'boolean' },
  { name: 'preferences', type: 'json' },
  { name: 'age', type: 'integer' },
  { name: 'country', type: 'string' },
  { name: 'signup_source', type: 'string' }
];

// Feature flag to control whether to use real or mock data
const USE_MOCK_DATA = !process.env.NEXT_PUBLIC_API_URL;

/**
 * Hook for managing data sources
 */
export const useDataSources = () => {
  // State for the selected data source
  const [selectedDataSource, setSelectedDataSource] = useState<DataSource | null>(null);

  // Use our fetch hook for API requests
  const {
    data: dataSources = USE_MOCK_DATA ? MOCK_DATA_SOURCES : [],
    isLoading: isLoadingDataSources,
    error: dataSourcesError,
    fetch: fetchDataSourcesFromApi,
    invalidateCache,
  } = useFetch<DataSource[]>(
    'get',
    API_ENDPOINTS.DATA_SOURCES.LIST.path,
    undefined,
    {
      fetchOnMount: !USE_MOCK_DATA,
      shouldCache: true,
      cacheTTL: 60, // 1 minute
    }
  );

  // Fetch data sources
  const fetchDataSources = useCallback(async () => {
    if (USE_MOCK_DATA) {
      return MOCK_DATA_SOURCES;
    }
    return await fetchDataSourcesFromApi();
  }, [fetchDataSourcesFromApi]);

  // Fetch a specific data source
  const fetchDataSource = useCallback(async (id: string) => {
    if (USE_MOCK_DATA) {
      const dataSource = MOCK_DATA_SOURCES.find(ds => ds.id === id) || null;
      setSelectedDataSource(dataSource);
      return dataSource;
    }

    try {
      const endpoint = API_ENDPOINTS.DATA_SOURCES.GET(id);
      const { data: fetchedDataSource } = await fetch(endpoint.path);
      setSelectedDataSource(fetchedDataSource || null);
      return fetchedDataSource;
    } catch (error) {
      handleError(error, { context: 'fetchDataSource', dataSourceId: id });
      return null;
    }
  }, []);

  // Create a new data source
  const createDataSource = useCallback(async (input: CreateDataSourceInput) => {
    if (USE_MOCK_DATA) {
      // Generate a mock data source from the input
      const newId = `ds-${Math.floor(Math.random() * 1000)}`;
      const newDataSource: DataSource = {
        id: newId,
        name: input.name,
        type: input.type,
        size: 0,
        lastUpdated: new Date().toISOString(),
        status: 'pending',
        connectionDetails: { ...input.connectionDetails },
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        createdBy: 'current-user',
      };
      
      // In a real app, we would push this to the server
      // For mock purposes, we'll just return the new data source
      invalidateCache(); // Invalidate the data sources cache
      return newDataSource;
    }

    try {
      const { data } = await fetch(API_ENDPOINTS.DATA_SOURCES.CREATE.path, {
        method: 'POST',
        body: JSON.stringify(input),
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      // Invalidate the data sources cache to refresh the list
      invalidateCache();
      
      return data;
    } catch (error) {
      handleError(error, { context: 'createDataSource', input });
      throw error;
    }
  }, [invalidateCache]);

  // Update an existing data source
  const updateDataSource = useCallback(async (id: string, input: UpdateDataSourceInput) => {
    if (USE_MOCK_DATA) {
      // For mock purposes, return a success status
      invalidateCache(); // Invalidate the data sources cache
      return { success: true };
    }

    try {
      const endpoint = API_ENDPOINTS.DATA_SOURCES.UPDATE(id);
      const { data } = await fetch(endpoint.path, {
        method: 'PUT',
        body: JSON.stringify(input),
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      // Invalidate the data sources cache to refresh the list
      invalidateCache();
      
      // If this was the selected data source, update it
      if (selectedDataSource && selectedDataSource.id === id) {
        fetchDataSource(id);
      }
      
      return data;
    } catch (error) {
      handleError(error, { context: 'updateDataSource', dataSourceId: id, input });
      throw error;
    }
  }, [fetchDataSource, invalidateCache, selectedDataSource]);

  // Delete a data source
  const deleteDataSource = useCallback(async (id: string) => {
    if (USE_MOCK_DATA) {
      // For mock purposes, return a success status
      invalidateCache(); // Invalidate the data sources cache
      return { success: true };
    }

    try {
      const endpoint = API_ENDPOINTS.DATA_SOURCES.DELETE(id);
      const { data } = await fetch(endpoint.path, {
        method: 'DELETE',
      });
      
      // Invalidate the data sources cache to refresh the list
      invalidateCache();
      
      // If this was the selected data source, clear it
      if (selectedDataSource && selectedDataSource.id === id) {
        setSelectedDataSource(null);
      }
      
      return data;
    } catch (error) {
      handleError(error, { context: 'deleteDataSource', dataSourceId: id });
      throw error;
    }
  }, [invalidateCache, selectedDataSource]);

  // Refresh a data source
  const refreshDataSource = useCallback(async (id: string) => {
    if (USE_MOCK_DATA) {
      // For mock purposes, update the lastUpdated field
      const dataSourceIndex = MOCK_DATA_SOURCES.findIndex(ds => ds.id === id);
      if (dataSourceIndex >= 0) {
        MOCK_DATA_SOURCES[dataSourceIndex] = {
          ...MOCK_DATA_SOURCES[dataSourceIndex],
          lastUpdated: new Date().toISOString(),
          status: 'connected',
        };
      }
      invalidateCache(); // Invalidate the data sources cache
      return { success: true };
    }

    try {
      const endpoint = API_ENDPOINTS.DATA_SOURCES.REFRESH(id);
      const { data } = await fetch(endpoint.path, {
        method: 'POST',
      });
      
      // Invalidate the data sources cache to refresh the list
      invalidateCache();
      
      // If this was the selected data source, update it
      if (selectedDataSource && selectedDataSource.id === id) {
        fetchDataSource(id);
      }
      
      return data;
    } catch (error) {
      handleError(error, { context: 'refreshDataSource', dataSourceId: id });
      throw error;
    }
  }, [fetchDataSource, invalidateCache, selectedDataSource]);

  // Get schema for a data source
  const getDataSourceSchema = useCallback(async (id: string) => {
    if (USE_MOCK_DATA) {
      // Return mock schema
      return MOCK_SCHEMA;
    }

    try {
      const endpoint = API_ENDPOINTS.DATA_SOURCES.SCHEMA(id);
      const { data } = await fetch(endpoint.path);
      return data;
    } catch (error) {
      handleError(error, { context: 'getDataSourceSchema', dataSourceId: id });
      throw error;
    }
  }, []);

  return {
    dataSources,
    selectedDataSource,
    isLoadingDataSources,
    dataSourcesError,
    fetchDataSources,
    fetchDataSource,
    createDataSource,
    updateDataSource,
    deleteDataSource,
    refreshDataSource,
    getDataSourceSchema,
  };
};

export default useDataSources;