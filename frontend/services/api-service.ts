import api, { ApiError, RequestConfig } from '@/lib/api-client';
import API_ENDPOINTS from '@/lib/api-config';
import { handleError } from '@/lib/error-handler';
import { AIModel, CreateModelInput, UpdateModelInput } from '@/hooks/use-models';
import { Project, CreateProjectInput, UpdateProjectInput, AddProjectModelInput, AddProjectMemberInput } from '@/hooks/use-projects';
import { DataSource, CreateDataSourceInput, UpdateDataSourceInput } from '@/hooks/use-data-sources';

/**
 * Centralized API service that provides type-safe methods for all API interactions.
 * This service abstracts away the details of API calls and provides a consistent interface.
 */
export class ApiService {
  /**
   * MODELS API
   */
  
  // Get all models
  async getModels(config?: RequestConfig): Promise<AIModel[]> {
    try {
      const { data } = await api.get<AIModel[]>(API_ENDPOINTS.MODELS.LIST.path, undefined, config);
      return data;
    } catch (error) {
      handleError(error as ApiError, { context: 'getModels' });
      throw error;
    }
  }
  
  // Get a specific model by ID
  async getModel(id: string, config?: RequestConfig): Promise<AIModel> {
    try {
      const endpoint = API_ENDPOINTS.MODELS.GET(id);
      const { data } = await api.get<AIModel>(endpoint.path, undefined, config);
      return data;
    } catch (error) {
      handleError(error as ApiError, { context: 'getModel', modelId: id });
      throw error;
    }
  }
  
  // Create a new model
  async createModel(input: CreateModelInput, config?: RequestConfig): Promise<AIModel> {
    try {
      const { data } = await api.post<AIModel>(API_ENDPOINTS.MODELS.CREATE.path, input, config);
      return data;
    } catch (error) {
      handleError(error as ApiError, { context: 'createModel', input });
      throw error;
    }
  }
  
  // Update an existing model
  async updateModel(id: string, input: UpdateModelInput, config?: RequestConfig): Promise<AIModel> {
    try {
      const endpoint = API_ENDPOINTS.MODELS.UPDATE(id);
      const { data } = await api.put<AIModel>(endpoint.path, input, config);
      return data;
    } catch (error) {
      handleError(error as ApiError, { context: 'updateModel', modelId: id, input });
      throw error;
    }
  }
  
  // Delete a model
  async deleteModel(id: string, config?: RequestConfig): Promise<void> {
    try {
      const endpoint = API_ENDPOINTS.MODELS.DELETE(id);
      await api.delete(endpoint.path, config);
    } catch (error) {
      handleError(error as ApiError, { context: 'deleteModel', modelId: id });
      throw error;
    }
  }
  
  // Train a model
  async trainModel(id: string, config?: RequestConfig): Promise<{ jobId: string }> {
    try {
      const endpoint = API_ENDPOINTS.MODELS.TRAIN(id);
      const { data } = await api.post<{ jobId: string }>(endpoint.path, {}, config);
      return data;
    } catch (error) {
      handleError(error as ApiError, { context: 'trainModel', modelId: id });
      throw error;
    }
  }
  
  // Get model metrics
  async getModelMetrics(id: string, config?: RequestConfig): Promise<any> {
    try {
      const endpoint = API_ENDPOINTS.MODELS.METRICS(id);
      const { data } = await api.get<any>(endpoint.path, undefined, config);
      return data;
    } catch (error) {
      handleError(error as ApiError, { context: 'getModelMetrics', modelId: id });
      throw error;
    }
  }
  
  /**
   * PROJECTS API
   */
  
  // Get all projects
  async getProjects(config?: RequestConfig): Promise<Project[]> {
    try {
      const { data } = await api.get<Project[]>(API_ENDPOINTS.PROJECTS.LIST.path, undefined, config);
      return data;
    } catch (error) {
      handleError(error as ApiError, { context: 'getProjects' });
      throw error;
    }
  }
  
  // Get a specific project by ID
  async getProject(id: string, config?: RequestConfig): Promise<Project> {
    try {
      const endpoint = API_ENDPOINTS.PROJECTS.GET(id);
      const { data } = await api.get<Project>(endpoint.path, undefined, config);
      return data;
    } catch (error) {
      handleError(error as ApiError, { context: 'getProject', projectId: id });
      throw error;
    }
  }
  
  // Create a new project
  async createProject(input: CreateProjectInput, config?: RequestConfig): Promise<Project> {
    try {
      const { data } = await api.post<Project>(API_ENDPOINTS.PROJECTS.CREATE.path, input, config);
      return data;
    } catch (error) {
      handleError(error as ApiError, { context: 'createProject', input });
      throw error;
    }
  }
  
  // Update an existing project
  async updateProject(id: string, input: UpdateProjectInput, config?: RequestConfig): Promise<Project> {
    try {
      const endpoint = API_ENDPOINTS.PROJECTS.UPDATE(id);
      const { data } = await api.put<Project>(endpoint.path, input, config);
      return data;
    } catch (error) {
      handleError(error as ApiError, { context: 'updateProject', projectId: id, input });
      throw error;
    }
  }
  
  // Delete a project
  async deleteProject(id: string, config?: RequestConfig): Promise<void> {
    try {
      const endpoint = API_ENDPOINTS.PROJECTS.DELETE(id);
      await api.delete(endpoint.path, config);
    } catch (error) {
      handleError(error as ApiError, { context: 'deleteProject', projectId: id });
      throw error;
    }
  }
  
  // Add a model to a project
  async addModelToProject(projectId: string, input: AddProjectModelInput, config?: RequestConfig): Promise<void> {
    try {
      const endpoint = API_ENDPOINTS.PROJECTS.ADD_MODEL(projectId);
      await api.post(endpoint.path, input, config);
    } catch (error) {
      handleError(error as ApiError, { context: 'addModelToProject', projectId, input });
      throw error;
    }
  }
  
  // Add a member to a project
  async addMemberToProject(projectId: string, input: AddProjectMemberInput, config?: RequestConfig): Promise<void> {
    try {
      const endpoint = API_ENDPOINTS.PROJECTS.ADD_MEMBER(projectId);
      await api.post(endpoint.path, input, config);
    } catch (error) {
      handleError(error as ApiError, { context: 'addMemberToProject', projectId, input });
      throw error;
    }
  }
  
  /**
   * DATA SOURCES API
   */
  
  // Get all data sources
  async getDataSources(config?: RequestConfig): Promise<DataSource[]> {
    try {
      const { data } = await api.get<DataSource[]>(API_ENDPOINTS.DATA_SOURCES.LIST.path, undefined, config);
      return data;
    } catch (error) {
      handleError(error as ApiError, { context: 'getDataSources' });
      throw error;
    }
  }
  
  // Get a specific data source by ID
  async getDataSource(id: string, config?: RequestConfig): Promise<DataSource> {
    try {
      const endpoint = API_ENDPOINTS.DATA_SOURCES.GET(id);
      const { data } = await api.get<DataSource>(endpoint.path, undefined, config);
      return data;
    } catch (error) {
      handleError(error as ApiError, { context: 'getDataSource', dataSourceId: id });
      throw error;
    }
  }
  
  // Create a new data source
  async createDataSource(input: CreateDataSourceInput, config?: RequestConfig): Promise<DataSource> {
    try {
      const { data } = await api.post<DataSource>(API_ENDPOINTS.DATA_SOURCES.CREATE.path, input, config);
      return data;
    } catch (error) {
      handleError(error as ApiError, { context: 'createDataSource', input });
      throw error;
    }
  }
  
  // Update an existing data source
  async updateDataSource(id: string, input: UpdateDataSourceInput, config?: RequestConfig): Promise<DataSource> {
    try {
      const endpoint = API_ENDPOINTS.DATA_SOURCES.UPDATE(id);
      const { data } = await api.put<DataSource>(endpoint.path, input, config);
      return data;
    } catch (error) {
      handleError(error as ApiError, { context: 'updateDataSource', dataSourceId: id, input });
      throw error;
    }
  }
  
  // Delete a data source
  async deleteDataSource(id: string, config?: RequestConfig): Promise<void> {
    try {
      const endpoint = API_ENDPOINTS.DATA_SOURCES.DELETE(id);
      await api.delete(endpoint.path, config);
    } catch (error) {
      handleError(error as ApiError, { context: 'deleteDataSource', dataSourceId: id });
      throw error;
    }
  }
  
  // Refresh a data source
  async refreshDataSource(id: string, config?: RequestConfig): Promise<void> {
    try {
      const endpoint = API_ENDPOINTS.DATA_SOURCES.REFRESH(id);
      await api.post(endpoint.path, {}, config);
    } catch (error) {
      handleError(error as ApiError, { context: 'refreshDataSource', dataSourceId: id });
      throw error;
    }
  }
  
  // Get schema for a data source
  async getDataSourceSchema(id: string, config?: RequestConfig): Promise<any> {
    try {
      const endpoint = API_ENDPOINTS.DATA_SOURCES.SCHEMA(id);
      const { data } = await api.get<any>(endpoint.path, undefined, config);
      return data;
    } catch (error) {
      handleError(error as ApiError, { context: 'getDataSourceSchema', dataSourceId: id });
      throw error;
    }
  }
  
  // Get a preview of the data source
  async getDataSourcePreview(id: string, config?: RequestConfig): Promise<any> {
    try {
      const endpoint = API_ENDPOINTS.DATA_SOURCES.PREVIEW(id);
      const { data } = await api.get<any>(endpoint.path, undefined, config);
      return data;
    } catch (error) {
      handleError(error as ApiError, { context: 'getDataSourcePreview', dataSourceId: id });
      throw error;
    }
  }
  
  /**
   * USER API
   */
  
  // Get current user profile
  async getCurrentUser(config?: RequestConfig): Promise<any> {
    try {
      const { data } = await api.get<any>(API_ENDPOINTS.USERS.ME.path, undefined, config);
      return data;
    } catch (error) {
      handleError(error as ApiError, { context: 'getCurrentUser' });
      throw error;
    }
  }
  
  // Update current user profile
  async updateCurrentUser(input: any, config?: RequestConfig): Promise<any> {
    try {
      const { data } = await api.put<any>(API_ENDPOINTS.USERS.UPDATE_PROFILE.path, input, config);
      return data;
    } catch (error) {
      handleError(error as ApiError, { context: 'updateCurrentUser', input });
      throw error;
    }
  }
  
  /**
   * ANALYTICS API
   */
  
  // Get dashboard analytics
  async getDashboardAnalytics(config?: RequestConfig): Promise<any> {
    try {
      const { data } = await api.get<any>(API_ENDPOINTS.ANALYTICS.DASHBOARD.path, undefined, config);
      return data;
    } catch (error) {
      handleError(error as ApiError, { context: 'getDashboardAnalytics' });
      throw error;
    }
  }
}

// Create a singleton instance
const apiService = new ApiService();

export default apiService;