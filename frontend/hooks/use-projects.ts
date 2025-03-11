import { useFetch } from './use-fetch';
import { useState, useCallback } from 'react';
import { apiEndpoints } from '@/lib/api';
import { useToast } from '@/components/ui/use-toast';
import { AIModel } from './use-models';

// Define project types
export type ProjectStatus = 'active' | 'completed' | 'on-hold' | 'planned';

export interface ProjectMember {
  id: string;
  name: string;
  role: string;
  avatar?: string;
}

export interface ProjectModel {
  id: string;
  name: string;
  type: string;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  status: ProjectStatus;
  progress: number;
  startDate: string;
  endDate?: string;
  members: ProjectMember[];
  models: ProjectModel[];
  tags: string[];
  createdAt?: string;
  updatedAt?: string;
}

export interface CreateProjectInput {
  name: string;
  description: string;
  status: ProjectStatus;
  startDate: string;
  endDate?: string;
  memberIds?: string[];
  modelIds?: string[];
  tags?: string[];
}

export interface UpdateProjectInput extends Partial<CreateProjectInput> {
  id: string;
  progress?: number;
}

// Mock data for fallback or development
const mockProjects: Project[] = [
  {
    id: '1',
    name: 'Customer Churn Prediction',
    description: 'Develop an AI system to predict potential customer churn and provide intervention strategies.',
    status: 'active',
    progress: 75,
    startDate: '2025-01-15',
    endDate: '2025-04-30',
    members: [
      { id: '1', name: 'Alex Wong', role: 'Project Lead', avatar: '/avatars/alex.jpg' },
      { id: '2', name: 'Sarah Chen', role: 'Data Scientist', avatar: '/avatars/sarah.jpg' },
      { id: '3', name: 'Michael Brown', role: 'ML Engineer', avatar: '/avatars/michael.jpg' }
    ],
    models: [
      { id: '1', name: 'Customer Churn Predictor', type: 'classification' }
    ],
    tags: ['customer-retention', 'prediction', 'classification']
  },
  {
    id: '2',
    name: 'Document Classification System',
    description: 'Build an automated system for categorizing and organizing internal documents.',
    status: 'active',
    progress: 40,
    startDate: '2025-02-10',
    members: [
      { id: '4', name: 'Emily Taylor', role: 'Project Lead', avatar: '/avatars/emily.jpg' },
      { id: '5', name: 'David Johnson', role: 'NLP Specialist', avatar: '/avatars/david.jpg' }
    ],
    models: [
      { id: '2', name: 'Document Classifier', type: 'nlp' }
    ],
    tags: ['nlp', 'classification', 'automation']
  },
  {
    id: '3',
    name: 'Demand Forecasting',
    description: 'Create a forecasting system to predict product demand and optimize inventory management.',
    status: 'on-hold',
    progress: 30,
    startDate: '2025-01-05',
    endDate: '2025-05-15',
    members: [
      { id: '6', name: 'James Wilson', role: 'Project Lead', avatar: '/avatars/james.jpg' },
      { id: '7', name: 'Maria Garcia', role: 'Data Analyst', avatar: '/avatars/maria.jpg' }
    ],
    models: [
      { id: '3', name: 'Product Demand Forecast', type: 'time-series' }
    ],
    tags: ['forecasting', 'inventory', 'optimization']
  },
  {
    id: '4',
    name: 'Customer Segmentation',
    description: 'Segment customers based on purchasing behavior to enable targeted marketing campaigns.',
    status: 'completed',
    progress: 100,
    startDate: '2024-11-01',
    endDate: '2025-02-28',
    members: [
      { id: '8', name: 'Lisa Chen', role: 'Marketing Analyst', avatar: '/avatars/lisa.jpg' },
      { id: '2', name: 'Sarah Chen', role: 'Data Scientist', avatar: '/avatars/sarah.jpg' }
    ],
    models: [],
    tags: ['marketing', 'segmentation', 'clustering']
  },
  {
    id: '5',
    name: 'Predictive Maintenance',
    description: 'Implement a predictive maintenance system for manufacturing equipment.',
    status: 'planned',
    progress: 0,
    startDate: '2025-04-01',
    members: [
      { id: '9', name: 'Robert Kim', role: 'IoT Specialist', avatar: '/avatars/robert.jpg' },
      { id: '3', name: 'Michael Brown', role: 'ML Engineer', avatar: '/avatars/michael.jpg' }
    ],
    models: [],
    tags: ['iot', 'maintenance', 'manufacturing']
  },
  {
    id: '6',
    name: 'Sentiment Analysis Dashboard',
    description: 'Build a real-time dashboard to analyze customer sentiment from various feedback channels.',
    status: 'active',
    progress: 60,
    startDate: '2025-02-01',
    endDate: '2025-05-01',
    members: [
      { id: '10', name: 'Jessica Lee', role: 'UX Designer', avatar: '/avatars/jessica.jpg' },
      { id: '5', name: 'David Johnson', role: 'NLP Specialist', avatar: '/avatars/david.jpg' }
    ],
    models: [
      { id: '6', name: 'Sentiment Analyzer', type: 'nlp' }
    ],
    tags: ['sentiment-analysis', 'dashboard', 'feedback']
  }
];

/**
 * Custom hook for managing projects data
 * 
 * @param options Options to customize the behavior
 */
export function useProjects(options: {
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
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  
  // Use the fetch hook for getting all projects
  const {
    data: projects,
    isLoading: isLoadingProjects,
    error: projectsError,
    fetchData: fetchProjects,
    updateData: updateProjects,
  } = useFetch<Project[]>('GET', '/projects', {
    initialData: useMockData ? mockProjects : undefined,
    fetchOnMount: !useMockData && fetchOnMount,
  });
  
  // Get a single project by ID
  const {
    data: selectedProject,
    isLoading: isLoadingSelectedProject,
    error: selectedProjectError,
    fetchData: fetchSelectedProject,
  } = useFetch<Project>('GET', selectedProjectId ? `/projects/${selectedProjectId}` : '', {
    fetchOnMount: !useMockData && !!selectedProjectId,
  });
  
  // Select a project by ID
  const selectProject = useCallback((id: string) => {
    setSelectedProjectId(id);
    
    if (useMockData) {
      // If using mock data, find the project in the local array
      const project = mockProjects.find(p => p.id === id);
      if (project) {
        return Promise.resolve(project);
      }
      return Promise.reject(new Error('Project not found'));
    }
    
    // Otherwise fetch from API
    return fetchSelectedProject();
  }, [useMockData, fetchSelectedProject]);
  
  // Create a new project
  const createProject = useCallback(async (input: CreateProjectInput) => {
    if (useMockData) {
      // Create a new mock project
      const newProject: Project = {
        id: `mock-${Date.now()}`,
        name: input.name,
        description: input.description,
        status: input.status,
        progress: input.status === 'completed' ? 100 : 0,
        startDate: input.startDate,
        endDate: input.endDate,
        members: [], // We would need to fetch members by IDs in a real implementation
        models: [], // We would need to fetch models by IDs in a real implementation
        tags: input.tags || [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      
      // Add to mock data
      const updatedProjects = [...(projects || []), newProject];
      updateProjects(updatedProjects);
      
      toast({
        title: 'Project created',
        description: `${newProject.name} has been created successfully.`,
      });
      
      return newProject;
    }
    
    // Otherwise use the API
    try {
      const result = await apiEndpoints.createProject(input);
      // Refresh the projects list
      fetchProjects();
      
      toast({
        title: 'Project created',
        description: `${result.name} has been created successfully.`,
      });
      
      return result;
    } catch (error: any) {
      toast({
        title: 'Failed to create project',
        description: error.message || 'An unexpected error occurred',
        variant: 'destructive',
      });
      throw error;
    }
  }, [useMockData, projects, updateProjects, fetchProjects, toast]);
  
  // Update an existing project
  const updateProject = useCallback(async (input: UpdateProjectInput) => {
    if (useMockData) {
      // Update the mock project
      const updatedProjects = (projects || []).map(project => {
        if (project.id === input.id) {
          return { ...project, ...input, updatedAt: new Date().toISOString() };
        }
        return project;
      });
      
      updateProjects(updatedProjects);
      
      toast({
        title: 'Project updated',
        description: `The project has been updated successfully.`,
      });
      
      return updatedProjects.find(p => p.id === input.id);
    }
    
    // Otherwise use the API
    try {
      const result = await apiEndpoints.updateProject(input.id, input);
      // Refresh the projects list
      fetchProjects();
      
      // If this is the selected project, refresh it too
      if (selectedProjectId === input.id) {
        fetchSelectedProject();
      }
      
      toast({
        title: 'Project updated',
        description: `The project has been updated successfully.`,
      });
      
      return result;
    } catch (error: any) {
      toast({
        title: 'Failed to update project',
        description: error.message || 'An unexpected error occurred',
        variant: 'destructive',
      });
      throw error;
    }
  }, [useMockData, projects, updateProjects, fetchProjects, selectedProjectId, fetchSelectedProject, toast]);
  
  // Delete a project
  const deleteProject = useCallback(async (id: string) => {
    if (useMockData) {
      // Delete from mock data
      const updatedProjects = (projects || []).filter(project => project.id !== id);
      updateProjects(updatedProjects);
      
      toast({
        title: 'Project deleted',
        description: 'The project has been deleted successfully.',
      });
      
      return true;
    }
    
    // Otherwise use the API
    try {
      await apiEndpoints.deleteProject(id);
      // Refresh the projects list
      fetchProjects();
      
      toast({
        title: 'Project deleted',
        description: 'The project has been deleted successfully.',
      });
      
      return true;
    } catch (error: any) {
      toast({
        title: 'Failed to delete project',
        description: error.message || 'An unexpected error occurred',
        variant: 'destructive',
      });
      throw error;
    }
  }, [useMockData, projects, updateProjects, fetchProjects, toast]);
  
  // Add a model to a project
  const addModelToProject = useCallback(async (projectId: string, modelId: string, modelData?: AIModel) => {
    if (useMockData) {
      // Update the mock project
      const updatedProjects = (projects || []).map(project => {
        if (project.id === projectId) {
          // Check if model already exists in the project
          if (project.models.some(m => m.id === modelId)) {
            return project;
          }
          
          // Create model data if not provided
          const modelToAdd: ProjectModel = modelData 
            ? { id: modelData.id, name: modelData.name, type: modelData.type }
            : { id: modelId, name: `Model ${modelId}`, type: 'unknown' };
          
          return { 
            ...project, 
            models: [...project.models, modelToAdd],
            updatedAt: new Date().toISOString() 
          };
        }
        return project;
      });
      
      updateProjects(updatedProjects);
      
      toast({
        title: 'Model added',
        description: `The model has been added to the project successfully.`,
      });
      
      return updatedProjects.find(p => p.id === projectId);
    }
    
    // Otherwise use the API
    try {
      const result = await apiRequest('POST', `/projects/${projectId}/models`, { modelId });
      
      // Refresh the projects list
      fetchProjects();
      
      // If this is the selected project, refresh it too
      if (selectedProjectId === projectId) {
        fetchSelectedProject();
      }
      
      toast({
        title: 'Model added',
        description: `The model has been added to the project successfully.`,
      });
      
      return result;
    } catch (error: any) {
      toast({
        title: 'Failed to add model',
        description: error.message || 'An unexpected error occurred',
        variant: 'destructive',
      });
      throw error;
    }
  }, [useMockData, projects, updateProjects, fetchProjects, selectedProjectId, fetchSelectedProject, toast]);
  
  // Add a member to a project
  const addMemberToProject = useCallback(async (
    projectId: string, 
    userId: string, 
    role: string,
    userData?: { name: string, avatar?: string }
  ) => {
    if (useMockData) {
      // Update the mock project
      const updatedProjects = (projects || []).map(project => {
        if (project.id === projectId) {
          // Check if member already exists in the project
          if (project.members.some(m => m.id === userId)) {
            return project;
          }
          
          // Create member data if not provided
          const memberToAdd: ProjectMember = userData 
            ? { id: userId, name: userData.name, role, avatar: userData.avatar }
            : { id: userId, name: `User ${userId}`, role };
          
          return { 
            ...project, 
            members: [...project.members, memberToAdd],
            updatedAt: new Date().toISOString() 
          };
        }
        return project;
      });
      
      updateProjects(updatedProjects);
      
      toast({
        title: 'Member added',
        description: `The member has been added to the project successfully.`,
      });
      
      return updatedProjects.find(p => p.id === projectId);
    }
    
    // Otherwise use the API
    try {
      const result = await apiRequest('POST', `/projects/${projectId}/members`, { userId, role });
      
      // Refresh the projects list
      fetchProjects();
      
      // If this is the selected project, refresh it too
      if (selectedProjectId === projectId) {
        fetchSelectedProject();
      }
      
      toast({
        title: 'Member added',
        description: `The member has been added to the project successfully.`,
      });
      
      return result;
    } catch (error: any) {
      toast({
        title: 'Failed to add member',
        description: error.message || 'An unexpected error occurred',
        variant: 'destructive',
      });
      throw error;
    }
  }, [useMockData, projects, updateProjects, fetchProjects, selectedProjectId, fetchSelectedProject, toast]);
  
  return {
    // Data
    projects: projects || [],
    selectedProject,
    
    // Loading states
    isLoadingProjects,
    isLoadingSelectedProject,
    
    // Errors
    projectsError,
    selectedProjectError,
    
    // Actions
    fetchProjects,
    selectProject,
    createProject,
    updateProject,
    deleteProject,
    addModelToProject,
    addMemberToProject,
  };
}

export default useProjects;