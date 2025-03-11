import { useFetch } from './use-fetch';
import { useState, useCallback } from 'react';
import { apiEndpoints } from '@/lib/api';
import { useToast } from '@/components/ui/use-toast';

// Define model types
export type ModelType = 'classification' | 'regression' | 'nlp' | 'computer-vision' | 'time-series';
export type ModelStatus = 'active' | 'training' | 'inactive' | 'error';

export interface AIModel {
  id: string;
  name: string;
  type: ModelType;
  framework: string;
  version: string;
  accuracy: number;
  status: ModelStatus;
  lastTrained: string;
  createdBy: string;
  description?: string;
  dataSources?: string[];
  createdAt?: string;
  updatedAt?: string;
}

export interface CreateModelInput {
  name: string;
  type: ModelType;
  framework: string;
  version: string;
  dataSourceIds: string[];
  description?: string;
}

export interface UpdateModelInput extends Partial<CreateModelInput> {
  id: string;
  status?: ModelStatus;
}

// Mock data for fallback or development
const mockModels: AIModel[] = [
  {
    id: '1',
    name: 'Customer Churn Predictor',
    type: 'classification',
    framework: 'PyTorch',
    version: '2.1',
    accuracy: 0.91,
    status: 'active',
    lastTrained: '2025-03-08',
    createdBy: 'Sarah Chen'
  },
  {
    id: '2',
    name: 'Document Classifier',
    type: 'nlp',
    framework: 'Hugging Face',
    version: '1.0',
    accuracy: 0.86,
    status: 'active',
    lastTrained: '2025-03-05',
    createdBy: 'David Johnson'
  },
  {
    id: '3',
    name: 'Product Demand Forecast',
    type: 'time-series',
    framework: 'TensorFlow',
    version: '3.2',
    accuracy: 0.79,
    status: 'training',
    lastTrained: '2025-03-10',
    createdBy: 'Maria Garcia'
  },
  {
    id: '4',
    name: 'Image Recognition System',
    type: 'computer-vision',
    framework: 'PyTorch',
    version: '1.5',
    accuracy: 0.94,
    status: 'active',
    lastTrained: '2025-03-01',
    createdBy: 'Alex Wong'
  },
  {
    id: '5',
    name: 'Price Optimizer',
    type: 'regression',
    framework: 'Scikit-learn',
    version: '2.0',
    accuracy: 0.82,
    status: 'inactive',
    lastTrained: '2025-02-20',
    createdBy: 'Emily Taylor'
  },
  {
    id: '6',
    name: 'Sentiment Analyzer',
    type: 'nlp',
    framework: 'BERT',
    version: '1.2',
    accuracy: 0.88,
    status: 'error',
    lastTrained: '2025-03-09',
    createdBy: 'James Wilson'
  }
];

/**
 * Custom hook for managing AI models data
 * 
 * @param options Options to customize the behavior
 */
export function useModels(options: {
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
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null);
  
  // Use the fetch hook for getting all models
  const {
    data: models,
    isLoading: isLoadingModels,
    error: modelsError,
    fetchData: fetchModels,
    updateData: updateModels,
  } = useFetch<AIModel[]>('GET', '/models', {
    initialData: useMockData ? mockModels : undefined,
    fetchOnMount: !useMockData && fetchOnMount,
  });
  
  // Get a single model by ID
  const {
    data: selectedModel,
    isLoading: isLoadingSelectedModel,
    error: selectedModelError,
    fetchData: fetchSelectedModel,
  } = useFetch<AIModel>('GET', selectedModelId ? `/models/${selectedModelId}` : '', {
    fetchOnMount: !useMockData && !!selectedModelId,
  });
  
  // Select a model by ID
  const selectModel = useCallback((id: string) => {
    setSelectedModelId(id);
    
    if (useMockData) {
      // If using mock data, find the model in the local array
      const model = mockModels.find(m => m.id === id);
      if (model) {
        return Promise.resolve(model);
      }
      return Promise.reject(new Error('Model not found'));
    }
    
    // Otherwise fetch from API
    return fetchSelectedModel();
  }, [useMockData, fetchSelectedModel]);
  
  // Create a new model
  const createModel = useCallback(async (input: CreateModelInput) => {
    if (useMockData) {
      // Create a new mock model
      const newModel: AIModel = {
        id: `mock-${Date.now()}`,
        name: input.name,
        type: input.type,
        framework: input.framework,
        version: input.version,
        accuracy: 0.75, // Default value for new models
        status: 'training', // New models start in training
        lastTrained: new Date().toISOString().split('T')[0],
        createdBy: 'Current User',
        description: input.description,
        dataSources: input.dataSourceIds,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      
      // Add to mock data
      const updatedModels = [...(models || []), newModel];
      updateModels(updatedModels);
      
      toast({
        title: 'Model created',
        description: `${newModel.name} has been created successfully.`,
      });
      
      return newModel;
    }
    
    // Otherwise use the API
    try {
      const result = await apiEndpoints.createModel(input);
      // Refresh the models list
      fetchModels();
      
      toast({
        title: 'Model created',
        description: `${result.name} has been created successfully.`,
      });
      
      return result;
    } catch (error: any) {
      toast({
        title: 'Failed to create model',
        description: error.message || 'An unexpected error occurred',
        variant: 'destructive',
      });
      throw error;
    }
  }, [useMockData, models, updateModels, fetchModels, toast]);
  
  // Update an existing model
  const updateModel = useCallback(async (input: UpdateModelInput) => {
    if (useMockData) {
      // Update the mock model
      const updatedModels = (models || []).map(model => {
        if (model.id === input.id) {
          return { ...model, ...input, updatedAt: new Date().toISOString() };
        }
        return model;
      });
      
      updateModels(updatedModels);
      
      toast({
        title: 'Model updated',
        description: `The model has been updated successfully.`,
      });
      
      return updatedModels.find(m => m.id === input.id);
    }
    
    // Otherwise use the API
    try {
      const result = await apiEndpoints.updateModel(input.id, input);
      // Refresh the models list
      fetchModels();
      
      // If this is the selected model, refresh it too
      if (selectedModelId === input.id) {
        fetchSelectedModel();
      }
      
      toast({
        title: 'Model updated',
        description: `The model has been updated successfully.`,
      });
      
      return result;
    } catch (error: any) {
      toast({
        title: 'Failed to update model',
        description: error.message || 'An unexpected error occurred',
        variant: 'destructive',
      });
      throw error;
    }
  }, [useMockData, models, updateModels, fetchModels, selectedModelId, fetchSelectedModel, toast]);
  
  // Delete a model
  const deleteModel = useCallback(async (id: string) => {
    if (useMockData) {
      // Delete from mock data
      const updatedModels = (models || []).filter(model => model.id !== id);
      updateModels(updatedModels);
      
      toast({
        title: 'Model deleted',
        description: 'The model has been deleted successfully.',
      });
      
      return true;
    }
    
    // Otherwise use the API
    try {
      await apiEndpoints.deleteModel(id);
      // Refresh the models list
      fetchModels();
      
      toast({
        title: 'Model deleted',
        description: 'The model has been deleted successfully.',
      });
      
      return true;
    } catch (error: any) {
      toast({
        title: 'Failed to delete model',
        description: error.message || 'An unexpected error occurred',
        variant: 'destructive',
      });
      throw error;
    }
  }, [useMockData, models, updateModels, fetchModels, toast]);
  
  // Start training a model
  const trainModel = useCallback(async (id: string) => {
    if (useMockData) {
      // Update status in mock data
      const updatedModels = (models || []).map(model => {
        if (model.id === id) {
          return { ...model, status: 'training' as ModelStatus, updatedAt: new Date().toISOString() };
        }
        return model;
      });
      
      updateModels(updatedModels);
      
      toast({
        title: 'Training started',
        description: 'The model training has been initiated.',
      });
      
      // Simulate training completion after 3 seconds
      setTimeout(() => {
        const completedModels = (updatedModels).map(model => {
          if (model.id === id) {
            return { 
              ...model, 
              status: 'active' as ModelStatus, 
              accuracy: Math.min(0.99, model.accuracy + 0.05),
              lastTrained: new Date().toISOString().split('T')[0],
              updatedAt: new Date().toISOString()
            };
          }
          return model;
        });
        
        updateModels(completedModels);
        
        toast({
          title: 'Training completed',
          description: 'The model training has finished successfully.',
        });
      }, 3000);
      
      return true;
    }
    
    // Otherwise use the API
    try {
      await apiRequest('POST', `/models/${id}/train`);
      // Refresh the models list
      fetchModels();
      
      toast({
        title: 'Training started',
        description: 'The model training has been initiated.',
      });
      
      return true;
    } catch (error: any) {
      toast({
        title: 'Failed to start training',
        description: error.message || 'An unexpected error occurred',
        variant: 'destructive',
      });
      throw error;
    }
  }, [useMockData, models, updateModels, fetchModels, toast]);
  
  return {
    // Data
    models: models || [],
    selectedModel,
    
    // Loading states
    isLoadingModels,
    isLoadingSelectedModel,
    
    // Errors
    modelsError,
    selectedModelError,
    
    // Actions
    fetchModels,
    selectModel,
    createModel,
    updateModel,
    deleteModel,
    trainModel,
  };
}

export default useModels;