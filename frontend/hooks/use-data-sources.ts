import { useFetch } from './use-fetch';
import { useState, useCallback } from 'react';
import { apiEndpoints } from '@/lib/api';
import { useToast } from '@/components/ui/use-toast';

// Define data source types
export type DataSourceStatus = 'active' | 'processing' | 'inactive';
export type DataSourceType = 'SQL Database' | 'JSON API' | 'CSV Files' | 'Log Files' | 'Excel Files' | 'NoSQL Database' | 'Data Warehouse' | 'Streaming';

export interface DataSource {
  id: string;
  name: string;
  type: DataSourceType;
  connectionDetails?: string;
  size: string;
  lastUpdated: string;
  status: DataSourceStatus;
  schema?: Record<string, any>;
  description?: string;
  createdBy?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface CreateDataSourceInput {
  name: string;
  type: DataSourceType;
  connectionDetails: string;
  description?: string;
  authMethod?: string;
  authDetails?: Record<string, any>;
}

export interface UpdateDataSourceInput extends Partial<CreateDataSourceInput> {
  id: string;
  status?: DataSourceStatus;
}

// Mock data for fallback or development
const mockDataSources: DataSource[] = [
  {
    id: '1',
    name: 'Customer Database',
    type: 'SQL Database',
    size: '2.3 GB',
    lastUpdated: '2025-03-10',
    status: 'active',
    connectionDetails: 'jdbc:postgresql://db.example.com:5432/customers',
    description: 'Primary customer database containing user profiles and transactions.'
  },
  {
    id: '2',
    name: 'Product Catalog',
    type: 'JSON API',
    size: '450 MB',
    lastUpdated: '2025-03-08',
    status: 'active',
    connectionDetails: 'https://api.example.com/products',
    description: 'REST API for accessing product information and inventory.'
  },
  {
    id: '3',
    name: 'Sales Transactions',
    type: 'CSV Files',
    size: '1.2 GB',
    lastUpdated: '2025-03-07',
    status: 'active',
    connectionDetails: 's3://data.example.com/sales/',
    description: 'Daily sales transaction records exported from POS systems.'
  },
  {
    id: '4',
    name: 'User Activity Logs',
    type: 'Log Files',
    size: '3.7 GB',
    lastUpdated: '2025-03-06',
    status: 'processing',
    connectionDetails: 'https://logs.example.com/activity',
    description: 'Web and mobile application user activity logs.'
  },
  {
    id: '5',
    name: 'Inventory Data',
    type: 'Excel Files',
    size: '890 MB',
    lastUpdated: '2025-03-05',
    status: 'inactive',
    connectionDetails: 's3://data.example.com/inventory/',
    description: 'Warehouse inventory reports and reconciliation data.'
  },
];

/**
 * Custom hook for managing data sources
 * 
 * @param options Options to customize the behavior
 */
export function useDataSources(options: {
  /**
   * Whether to use mock data instead of API calls
   * @default false in production, true in development
   */
  useMockData?: boolean;
  
  /**
   * Whether to fetch data on mount
   * @default true
   */
  fetchOnMount?: boolean;
} = {}) {
  const { 
    useMockData = process.env.NODE_ENV === 'development', 
    fetchOnMount = true 
  } = options;
  
  const { toast } = useToast();
  const [selectedDataSourceId, setSelectedDataSourceId] = useState<string | null>(null);
  
  // Use the fetch hook for getting all data sources
  const {
    data: dataSources,
    isLoading: isLoadingDataSources,
    error: dataSourcesError,
    fetchData: fetchDataSources,
    updateData: updateDataSources,
  } = useFetch<DataSource[]>('GET', '/data-sources', {
    initialData: useMockData ? mockDataSources : undefined,
    fetchOnMount: !useMockData && fetchOnMount,
  });
  
  // Get a single data source by ID
  const {
    data: selectedDataSource,
    isLoading: isLoadingSelectedDataSource,
    error: selectedDataSourceError,
    fetchData: fetchSelectedDataSource,
  } = useFetch<DataSource>('GET', selectedDataSourceId ? `/data-sources/${selectedDataSourceId}` : '', {
    fetchOnMount: !useMockData && !!selectedDataSourceId,
  });
  
  // Select a data source by ID
  const selectDataSource = useCallback((id: string) => {
    setSelectedDataSourceId(id);
    
    if (useMockData) {
      // If using mock data, find the data source in the local array
      const dataSource = mockDataSources.find(ds => ds.id === id);
      if (dataSource) {
        return Promise.resolve(dataSource);
      }
      return Promise.reject(new Error('Data source not found'));
    }
    
    // Otherwise fetch from API
    return fetchSelectedDataSource();
  }, [useMockData, fetchSelectedDataSource]);
  
  // Create a new data source
  const createDataSource = useCallback(async (input: CreateDataSourceInput) => {
    if (useMockData) {
      // Create a new mock data source
      const newDataSource: DataSource = {
        id: `mock-${Date.now()}`,
        name: input.name,
        type: input.type,
        connectionDetails: input.connectionDetails,
        description: input.description,
        size: '0 KB', // New data source starts empty
        lastUpdated: new Date().toISOString().split('T')[0],
        status: 'processing', // New data sources start in processing
        createdBy: 'Current User',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      
      // Add to mock data
      const updatedDataSources = [...(dataSources || []), newDataSource];
      updateDataSources(updatedDataSources);
      
      toast({
        title: 'Data source created',
        description: `${newDataSource.name} has been created successfully.`,
      });
      
      // Simulate processing completion after 2 seconds
      setTimeout(() => {
        const completedDataSources = updatedDataSources.map(ds => {
          if (ds.id === newDataSource.id) {
            return { 
              ...ds, 
              status: 'active' as DataSourceStatus,
              size: '10 MB', // Give it some initial size
              updatedAt: new Date().toISOString() 
            };
          }
          return ds;
        });
        
        updateDataSources(completedDataSources);
        
        toast({
          title: 'Data source ready',
          description: `${newDataSource.name} is now active and ready to use.`,
        });
      }, 2000);
      
      return newDataSource;
    }
    
    // Otherwise use the API
    try {
      const result = await apiEndpoints.createDataSource(input);
      // Refresh the data sources list
      fetchDataSources();
      
      toast({
        title: 'Data source created',
        description: `${result.name} has been created successfully.`,
      });
      
      return result;
    } catch (error: any) {
      toast({
        title: 'Failed to create data source',
        description: error.message || 'An unexpected error occurred',
        variant: 'destructive',
      });
      throw error;
    }
  }, [useMockData, dataSources, updateDataSources, fetchDataSources, toast]);
  
  // Update an existing data source
  const updateDataSource = useCallback(async (input: UpdateDataSourceInput) => {
    if (useMockData) {
      // Update the mock data source
      const updatedDataSources = (dataSources || []).map(ds => {
        if (ds.id === input.id) {
          return { 
            ...ds, 
            ...input, 
            lastUpdated: new Date().toISOString().split('T')[0],
            updatedAt: new Date().toISOString() 
          };
        }
        return ds;
      });
      
      updateDataSources(updatedDataSources);
      
      toast({
        title: 'Data source updated',
        description: `The data source has been updated successfully.`,
      });
      
      return updatedDataSources.find(ds => ds.id === input.id);
    }
    
    // Otherwise use the API
    try {
      const result = await apiEndpoints.updateDataSource(input.id, input);
      // Refresh the data sources list
      fetchDataSources();
      
      // If this is the selected data source, refresh it too
      if (selectedDataSourceId === input.id) {
        fetchSelectedDataSource();
      }
      
      toast({
        title: 'Data source updated',
        description: `The data source has been updated successfully.`,
      });
      
      return result;
    } catch (error: any) {
      toast({
        title: 'Failed to update data source',
        description: error.message || 'An unexpected error occurred',
        variant: 'destructive',
      });
      throw error;
    }
  }, [useMockData, dataSources, updateDataSources, fetchDataSources, selectedDataSourceId, fetchSelectedDataSource, toast]);
  
  // Delete a data source
  const deleteDataSource = useCallback(async (id: string) => {
    if (useMockData) {
      // Delete from mock data
      const updatedDataSources = (dataSources || []).filter(ds => ds.id !== id);
      updateDataSources(updatedDataSources);
      
      toast({
        title: 'Data source deleted',
        description: 'The data source has been deleted successfully.',
      });
      
      return true;
    }
    
    // Otherwise use the API
    try {
      await apiEndpoints.deleteDataSource(id);
      // Refresh the data sources list
      fetchDataSources();
      
      toast({
        title: 'Data source deleted',
        description: 'The data source has been deleted successfully.',
      });
      
      return true;
    } catch (error: any) {
      toast({
        title: 'Failed to delete data source',
        description: error.message || 'An unexpected error occurred',
        variant: 'destructive',
      });
      throw error;
    }
  }, [useMockData, dataSources, updateDataSources, fetchDataSources, toast]);
  
  // Refresh a data source (re-sync with source)
  const refreshDataSource = useCallback(async (id: string) => {
    if (useMockData) {
      // Update the mock data source to simulate refresh
      const updatedDataSources = (dataSources || []).map(ds => {
        if (ds.id === id) {
          return { 
            ...ds, 
            status: 'processing' as DataSourceStatus,
            lastUpdated: new Date().toISOString().split('T')[0],
            updatedAt: new Date().toISOString() 
          };
        }
        return ds;
      });
      
      updateDataSources(updatedDataSources);
      
      toast({
        title: 'Refreshing data source',
        description: 'The data source refresh has been initiated.',
      });
      
      // Simulate refresh completion after 1.5 seconds
      setTimeout(() => {
        const completedDataSources = updatedDataSources.map(ds => {
          if (ds.id === id) {
            // Increase size slightly to simulate new data
            const currentSize = parseFloat(ds.size.split(' ')[0]);
            const unit = ds.size.split(' ')[1];
            const newSize = (currentSize * 1.1).toFixed(1);
            
            return { 
              ...ds, 
              status: 'active' as DataSourceStatus,
              size: `${newSize} ${unit}`,
              updatedAt: new Date().toISOString() 
            };
          }
          return ds;
        });
        
        updateDataSources(completedDataSources);
        
        toast({
          title: 'Data source refreshed',
          description: 'The data source has been refreshed successfully.',
        });
      }, 1500);
      
      return true;
    }
    
    // Otherwise use the API
    try {
      await apiRequest('POST', `/data-sources/${id}/refresh`);
      // Refresh the data sources list
      fetchDataSources();
      
      toast({
        title: 'Refreshing data source',
        description: 'The data source refresh has been initiated.',
      });
      
      return true;
    } catch (error: any) {
      toast({
        title: 'Failed to refresh data source',
        description: error.message || 'An unexpected error occurred',
        variant: 'destructive',
      });
      throw error;
    }
  }, [useMockData, dataSources, updateDataSources, fetchDataSources, toast]);
  
  // Get schema for a data source
  const getDataSourceSchema = useCallback(async (id: string) => {
    if (useMockData) {
      // Return a mock schema
      const dataSource = mockDataSources.find(ds => ds.id === id);
      
      // Generate a mock schema based on the data source type
      let mockSchema: Record<string, any> = {};
      
      switch (dataSource?.type) {
        case 'SQL Database':
          mockSchema = {
            tables: [
              {
                name: 'customers',
                columns: [
                  { name: 'id', type: 'INTEGER', primaryKey: true },
                  { name: 'name', type: 'VARCHAR(255)' },
                  { name: 'email', type: 'VARCHAR(255)' },
                  { name: 'created_at', type: 'TIMESTAMP' },
                ]
              },
              {
                name: 'orders',
                columns: [
                  { name: 'id', type: 'INTEGER', primaryKey: true },
                  { name: 'customer_id', type: 'INTEGER', foreignKey: 'customers.id' },
                  { name: 'amount', type: 'DECIMAL(10,2)' },
                  { name: 'created_at', type: 'TIMESTAMP' },
                ]
              }
            ]
          };
          break;
          
        case 'JSON API':
          mockSchema = {
            endpoints: [
              {
                path: '/products',
                method: 'GET',
                parameters: [
                  { name: 'page', type: 'integer', required: false },
                  { name: 'limit', type: 'integer', required: false },
                  { name: 'category', type: 'string', required: false },
                ],
                response: {
                  type: 'array',
                  items: {
                    type: 'object',
                    properties: {
                      id: { type: 'integer' },
                      name: { type: 'string' },
                      price: { type: 'number' },
                      category: { type: 'string' },
                    }
                  }
                }
              }
            ]
          };
          break;
          
        case 'CSV Files':
          mockSchema = {
            files: [
              {
                name: 'sales_2025_03.csv',
                columns: [
                  { name: 'transaction_id', type: 'string' },
                  { name: 'date', type: 'date' },
                  { name: 'product_id', type: 'string' },
                  { name: 'quantity', type: 'integer' },
                  { name: 'price', type: 'decimal' },
                ]
              }
            ]
          };
          break;
          
        default:
          mockSchema = {
            message: 'Schema information not available for this data source type'
          };
      }
      
      return mockSchema;
    }
    
    // Otherwise use the API
    try {
      const result = await apiRequest('GET', `/data-sources/${id}/schema`);
      return result;
    } catch (error: any) {
      toast({
        title: 'Failed to fetch schema',
        description: error.message || 'An unexpected error occurred',
        variant: 'destructive',
      });
      throw error;
    }
  }, [useMockData, toast]);
  
  return {
    // Data
    dataSources: dataSources || [],
    selectedDataSource,
    
    // Loading states
    isLoadingDataSources,
    isLoadingSelectedDataSource,
    
    // Errors
    dataSourcesError,
    selectedDataSourceError,
    
    // Actions
    fetchDataSources,
    selectDataSource,
    createDataSource,
    updateDataSource,
    deleteDataSource,
    refreshDataSource,
    getDataSourceSchema,
  };
}

export default useDataSources;