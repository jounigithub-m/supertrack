import { useState, useCallback } from 'react';
import useFetch from './use-fetch';
import API_ENDPOINTS from '@/lib/api-config';
import { handleError } from '@/lib/error-handler';

// Type definitions
export type ModelType = 'classification' | 'regression' | 'nlp' | 'computer-vision' | 'time-series';
export type ModelStatus = 'active' | 'training' | 'inactive' | 'error';

export interface AIModel {
  id: string;
  name: string;
  type: ModelType;
  framework: string;
  version: string;
  description?: string;
  accuracy: number;
  status: ModelStatus;
  lastTrained: string;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  dataSourceIds?: string[];
  metrics?: {
    accuracy: number;
    precision: number;
    recall: number;
    f1Score: number;
  };
}

export interface CreateModelInput {
  name: string;
  type: ModelType;
  framework: string;
  version: string;
  description?: string;
  dataSourceIds?: string[];
}

export interface UpdateModelInput {
  name?: string;
  type?: ModelType;
  framework?: string;
  version?: string;
  description?: string;
  status?: ModelStatus;
  dataSourceIds?: string[];
}

// Mock data for development and testing
// This will be used until the API is fully implemented
const MOCK_MODELS: AIModel[] = [
  {
    id: 'model-001',
    name: 'Customer Churn Predictor',
    type: 'classification',
    framework: 'TensorFlow',
    version: '2.5',
    description: 'Predicts customer churn based on historical behavior and demographics',
    accuracy: 0.89,
    status: 'active',
    lastTrained: '2024-01-15T08:30:00Z',
    createdBy: 'user-001',
    createdAt: '2023-12-10T14:22:33Z',
    updatedAt: '2024-01-15T08:30:00Z',
    dataSourceIds: ['ds-001', 'ds-003'],
    metrics: {
      accuracy: 0.89,
      precision: 0.82,
      recall: 0.91,
      f1Score: 0.86
    }
  },
  {
    id: 'model-002',
    name: 'Sales Forecasting',
    type: 'regression',
    framework: 'PyTorch',
    version: '1.10',
    description: 'Predicts future sales based on historical data and seasonal patterns',
    accuracy: 0.92,
    status: 'active',
    lastTrained: '2024-02-01T10:15:22Z',
    createdBy: 'user-002',
    createdAt: '2023-11-05T09:12:45Z',
    updatedAt: '2024-02-01T10:15:22Z',
    dataSourceIds: ['ds-002'],
    metrics: {
      accuracy: 0.92,
      precision: 0.88,
      recall: 0.90,
      f1Score: 0.89
    }
  },
  {
    id: 'model-003',
    name: 'Sentiment Analyzer',
    type: 'nlp',
    framework: 'BERT',
    version: '1.0',
    description: 'Analyzes sentiment in customer feedback and social media mentions',
    accuracy: 0.78,
    status: 'training',
    lastTrained: '2024-02-28T13:45:10Z',
    createdBy: 'user-001',
    createdAt: '2024-01-20T11:33:21Z',
    updatedAt: '2024-02-28T13:45:10Z',
    dataSourceIds: ['ds-004'],
    metrics: {
      accuracy: 0.78,
      precision: 0.75,
      recall: 0.79,
      f1Score: 0.77
    }
  },
  {
    id: 'model-004',
    name: 'Fraud Detection System',
    type: 'classification',
    framework: 'TensorFlow',
    version: '2.6',
    description: 'Identifies potentially fraudulent transactions in real-time',
    accuracy: 0.96,
    status: 'active',
    lastTrained: '2024-02-10T09:20:15Z',
    createdBy: 'user-003',
    createdAt: '2023-10-12T16:44:30Z',
    updatedAt: '2024-02-10T09:20:15Z',
    dataSourceIds: ['ds-001', 'ds-005'],
    metrics: {
      accuracy: 0.96,
      precision: 0.94,
      recall: 0.92,
      f1Score: 0.93
    }
  },
  {
    id: 'model-005',
    name: 'Object Recognition',
    type: 'computer-vision',
    framework: 'PyTorch',
    version: '1.11',
    description: 'Detects and classifies objects in images and video streams',
    accuracy: 0.85,
    status: 'inactive',
    lastTrained: '2023-12-05T14:22:33Z',
    createdBy: 'user-002',
    createdAt: '2023-09-18T08:55:42Z',
    updatedAt: '2023-12-05T14:22:33Z',
    dataSourceIds: ['ds-006'],
    metrics: {
      accuracy: 0.85,
      precision: 0.83,
      recall: 0.81,
      f1Score: 0.82
    }
  },
  {
    id: 'model-006',
    name: 'Supply Chain Forecaster',
    type: 'time-series',
    framework: 'Scikit-learn',
    version: '1.0',
    description: 'Predicts inventory requirements based on historical sales and seasonal patterns',
    accuracy: 0.82,
    status: 'error',
    lastTrained: '2024-02-20T11:10:05Z',
    createdBy: 'user-001',
    createdAt: '2023-11-30T10:40:15Z',
    updatedAt: '2024-02-20T11:10:05Z',
    dataSourceIds: ['ds-002', 'ds-007'],
    metrics: {
      accuracy: 0.82,
      precision: 0.79,
      recall: 0.81,
      f1Score: 0.80
    }
  }
];

// Feature flag to control whether to use real or mock data
const USE_MOCK_DATA = !process.env.NEXT_PUBLIC_API_URL;

/**
 * Hook for managing AI models
 */
export const useModels = () => {
  // State for the selected model
  const [selectedModel, setSelectedModel] = useState<AIModel | null>(null);

  // Use our fetch hook for API requests
  const {
    data: models = USE_MOCK_DATA ? MOCK_MODELS : [],
    isLoading: isLoadingModels,
    error: modelsError,
    fetch: fetchModelsFromApi,
    invalidateCache,
  } = useFetch<AIModel[]>(
    'get',
    API_ENDPOINTS.MODELS.LIST.path,
    undefined,
    {
      fetchOnMount: !USE_MOCK_DATA,
      shouldCache: true,
      cacheTTL: 60, // 1 minute
    }
  );

  // Fetch models
  const fetchModels = useCallback(async () => {
    if (USE_MOCK_DATA) {
      return MOCK_MODELS;
    }
    return await fetchModelsFromApi();
  }, [fetchModelsFromApi]);

  // Fetch a specific model
  const fetchModel = useCallback(async (id: string) => {
    if (USE_MOCK_DATA) {
      const model = MOCK_MODELS.find(m => m.id === id) || null;
      setSelectedModel(model);
      return model;
    }

    try {
      const endpoint = API_ENDPOINTS.MODELS.GET(id);
      const { data: fetchedModel } = await fetch(endpoint.path);
      setSelectedModel(fetchedModel || null);
      return fetchedModel;
    } catch (error) {
      handleError(error, { context: 'fetchModel', modelId: id });
      return null;
    }
  }, []);

  // Create a new model
  const createModel = useCallback(async (input: CreateModelInput) => {
    if (USE_MOCK_DATA) {
      // Generate a mock model from the input
      const newId = `model-${Math.floor(Math.random() * 1000)}`;
      const newModel: AIModel = {
        id: newId,
        name: input.name,
        type: input.type,
        framework: input.framework,
        version: input.version,
        description: input.description,
        accuracy: 0,
        status: 'inactive',
        lastTrained: new Date().toISOString(),
        createdBy: 'current-user',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        dataSourceIds: input.dataSourceIds,
        metrics: {
          accuracy: 0,
          precision: 0,
          recall: 0,
          f1Score: 0
        }
      };
      
      // In a real app, we would push this to the server
      // For mock purposes, we'll just return the new model
      invalidateCache(); // Invalidate the models cache
      return newModel;
    }

    try {
      const { data } = await fetch(API_ENDPOINTS.MODELS.CREATE.path, {
        method: 'post',
        body: JSON.stringify(input),
      });
      
      // Invalidate the models cache to refresh the list
      invalidateCache();
      
      return data;
    } catch (error) {
      handleError(error, { context: 'createModel', input });
      throw error;
    }
  }, [invalidateCache]);

  // Update an existing model
  const updateModel = useCallback(async (id: string, input: UpdateModelInput) => {
    if (USE_MOCK_DATA) {
      // For mock purposes, return a success status
      invalidateCache(); // Invalidate the models cache
      return { success: true };
    }

    try {
      const endpoint = API_ENDPOINTS.MODELS.UPDATE(id);
      const { data } = await fetch(endpoint.path, {
        method: 'put',
        body: JSON.stringify(input),
      });
      
      // Invalidate the models cache to refresh the list
      invalidateCache();
      
      // If this was the selected model, update it
      if (selectedModel && selectedModel.id === id) {
        fetchModel(id);
      }
      
      return data;
    } catch (error) {
      handleError(error, { context: 'updateModel', modelId: id, input });
      throw error;
    }
  }, [fetchModel, invalidateCache, selectedModel]);

  // Delete a model
  const deleteModel = useCallback(async (id: string) => {
    if (USE_MOCK_DATA) {
      // For mock purposes, return a success status
      invalidateCache(); // Invalidate the models cache
      return { success: true };
    }

    try {
      const endpoint = API_ENDPOINTS.MODELS.DELETE(id);
      const { data } = await fetch(endpoint.path, {
        method: 'delete',
      });
      
      // Invalidate the models cache to refresh the list
      invalidateCache();
      
      // If this was the selected model, clear it
      if (selectedModel && selectedModel.id === id) {
        setSelectedModel(null);
      }
      
      return data;
    } catch (error) {
      handleError(error, { context: 'deleteModel', modelId: id });
      throw error;
    }
  }, [invalidateCache, selectedModel]);

  // Start training a model
  const trainModel = useCallback(async (id: string) => {
    if (USE_MOCK_DATA) {
      // Mock updating the model status
      const modelIndex = MOCK_MODELS.findIndex(m => m.id === id);
      if (modelIndex >= 0) {
        MOCK_MODELS[modelIndex] = {
          ...MOCK_MODELS[modelIndex],
          status: 'training',
          updatedAt: new Date().toISOString(),
        };
      }
      invalidateCache(); // Invalidate the models cache
      return { success: true };
    }

    try {
      const endpoint = API_ENDPOINTS.MODELS.TRAIN(id);
      const { data } = await fetch(endpoint.path, {
        method: 'post',
      });
      
      // Invalidate the models cache to refresh the list
      invalidateCache();
      
      // If this was the selected model, update it
      if (selectedModel && selectedModel.id === id) {
        fetchModel(id);
      }
      
      return data;
    } catch (error) {
      handleError(error, { context: 'trainModel', modelId: id });
      throw error;
    }
  }, [fetchModel, invalidateCache, selectedModel]);

  return {
    models,
    selectedModel,
    isLoadingModels,
    modelsError,
    fetchModels,
    fetchModel,
    createModel,
    updateModel,
    deleteModel,
    trainModel,
  };
};

export default useModels;