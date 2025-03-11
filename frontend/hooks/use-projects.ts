import { useState, useCallback } from 'react';
import useFetch from './use-fetch';
import API_ENDPOINTS from '@/lib/api-config';
import { handleError } from '@/lib/error-handler';
import { AIModel } from './use-models';

// Type definitions
export type ProjectStatus = 'active' | 'completed' | 'paused' | 'planning';

export interface ProjectMember {
  id: string;
  name: string;
  email: string;
  role: string;
  avatar?: string;
  joinedAt: string;
}

export interface ProjectModel {
  id: string;
  name: string;
  type: string;
  status: string;
  addedAt: string;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  status: ProjectStatus;
  progress: number;
  startDate: string;
  endDate?: string;
  members?: ProjectMember[];
  models?: ProjectModel[];
  tags?: string[];
  createdAt: string;
  updatedAt: string;
  createdBy: string;
}

export interface CreateProjectInput {
  name: string;
  description: string;
  status: ProjectStatus;
  startDate: string;
  endDate?: string;
  modelIds?: string[];
  tags?: string[];
}

export interface UpdateProjectInput {
  name?: string;
  description?: string;
  status?: ProjectStatus;
  progress?: number;
  startDate?: string;
  endDate?: string;
  tags?: string[];
}

export interface AddProjectModelInput {
  modelId: string;
}

export interface AddProjectMemberInput {
  userId: string;
  role: string;
}

// Mock data for development and testing
// This will be used until the API is fully implemented
const MOCK_PROJECTS: Project[] = [
  {
    id: 'proj-001',
    name: 'Customer Retention Initiative',
    description: 'Project aimed at reducing customer churn through predictive analytics and targeted interventions',
    status: 'active',
    progress: 65,
    startDate: '2024-01-10T00:00:00Z',
    endDate: '2024-06-30T00:00:00Z',
    members: [
      {
        id: 'user-001',
        name: 'Alex Johnson',
        email: 'alex.johnson@example.com',
        role: 'Project Manager',
        avatar: 'https://randomuser.me/api/portraits/men/1.jpg',
        joinedAt: '2024-01-10T00:00:00Z'
      },
      {
        id: 'user-002',
        name: 'Sarah Williams',
        email: 'sarah.williams@example.com',
        role: 'Data Scientist',
        avatar: 'https://randomuser.me/api/portraits/women/2.jpg',
        joinedAt: '2024-01-15T00:00:00Z'
      },
      {
        id: 'user-003',
        name: 'Michael Brown',
        email: 'michael.brown@example.com',
        role: 'ML Engineer',
        avatar: 'https://randomuser.me/api/portraits/men/3.jpg',
        joinedAt: '2024-01-20T00:00:00Z'
      }
    ],
    models: [
      {
        id: 'model-001',
        name: 'Customer Churn Predictor',
        type: 'Classification',
        status: 'active',
        addedAt: '2024-01-25T00:00:00Z'
      }
    ],
    tags: ['retention', 'predictive', 'high-priority'],
    createdAt: '2024-01-10T00:00:00Z',
    updatedAt: '2024-02-15T10:30:00Z',
    createdBy: 'user-001'
  },
  {
    id: 'proj-002',
    name: 'Sales Forecasting System',
    description: 'Implementation of advanced forecasting models to predict quarterly sales across product lines',
    status: 'active',
    progress: 80,
    startDate: '2023-11-15T00:00:00Z',
    endDate: '2024-04-15T00:00:00Z',
    members: [
      {
        id: 'user-001',
        name: 'Alex Johnson',
        email: 'alex.johnson@example.com',
        role: 'Project Manager',
        avatar: 'https://randomuser.me/api/portraits/men/1.jpg',
        joinedAt: '2023-11-15T00:00:00Z'
      },
      {
        id: 'user-004',
        name: 'Emily Davis',
        email: 'emily.davis@example.com',
        role: 'Business Analyst',
        avatar: 'https://randomuser.me/api/portraits/women/4.jpg',
        joinedAt: '2023-11-20T00:00:00Z'
      }
    ],
    models: [
      {
        id: 'model-002',
        name: 'Sales Forecasting',
        type: 'Regression',
        status: 'active',
        addedAt: '2023-12-05T00:00:00Z'
      }
    ],
    tags: ['sales', 'forecasting', 'regression'],
    createdAt: '2023-11-15T00:00:00Z',
    updatedAt: '2024-02-10T14:45:00Z',
    createdBy: 'user-001'
  },
  {
    id: 'proj-003',
    name: 'Customer Feedback Analysis',
    description: 'Sentiment analysis of customer feedback from multiple channels to identify improvement areas',
    status: 'planning',
    progress: 15,
    startDate: '2024-03-01T00:00:00Z',
    endDate: '2024-08-31T00:00:00Z',
    members: [
      {
        id: 'user-002',
        name: 'Sarah Williams',
        email: 'sarah.williams@example.com',
        role: 'Data Scientist',
        avatar: 'https://randomuser.me/api/portraits/women/2.jpg',
        joinedAt: '2024-02-20T00:00:00Z'
      }
    ],
    models: [
      {
        id: 'model-003',
        name: 'Sentiment Analyzer',
        type: 'NLP',
        status: 'training',
        addedAt: '2024-02-25T00:00:00Z'
      }
    ],
    tags: ['sentiment-analysis', 'customer-feedback', 'nlp'],
    createdAt: '2024-02-20T00:00:00Z',
    updatedAt: '2024-02-28T09:15:00Z',
    createdBy: 'user-002'
  },
  {
    id: 'proj-004',
    name: 'Fraud Detection Enhancement',
    description: 'Upgrading the existing fraud detection system with advanced machine learning techniques',
    status: 'active',
    progress: 40,
    startDate: '2024-01-05T00:00:00Z',
    endDate: '2024-05-31T00:00:00Z',
    members: [
      {
        id: 'user-003',
        name: 'Michael Brown',
        email: 'michael.brown@example.com',
        role: 'ML Engineer',
        avatar: 'https://randomuser.me/api/portraits/men/3.jpg',
        joinedAt: '2024-01-05T00:00:00Z'
      },
      {
        id: 'user-005',
        name: 'David Wilson',
        email: 'david.wilson@example.com',
        role: 'Security Specialist',
        avatar: 'https://randomuser.me/api/portraits/men/5.jpg',
        joinedAt: '2024-01-10T00:00:00Z'
      }
    ],
    models: [
      {
        id: 'model-004',
        name: 'Fraud Detection System',
        type: 'Classification',
        status: 'active',
        addedAt: '2024-01-15T00:00:00Z'
      }
    ],
    tags: ['fraud', 'security', 'classification'],
    createdAt: '2024-01-05T00:00:00Z',
    updatedAt: '2024-02-20T16:20:00Z',
    createdBy: 'user-003'
  },
  {
    id: 'proj-005',
    name: 'Product Recommendation Engine',
    description: 'Development of an AI-powered recommendation system to increase cross-selling and upselling opportunities',
    status: 'paused',
    progress: 50,
    startDate: '2023-10-01T00:00:00Z',
    endDate: '2024-03-31T00:00:00Z',
    members: [
      {
        id: 'user-002',
        name: 'Sarah Williams',
        email: 'sarah.williams@example.com',
        role: 'Data Scientist',
        avatar: 'https://randomuser.me/api/portraits/women/2.jpg',
        joinedAt: '2023-10-01T00:00:00Z'
      },
      {
        id: 'user-006',
        name: 'Jennifer Lee',
        email: 'jennifer.lee@example.com',
        role: 'Frontend Developer',
        avatar: 'https://randomuser.me/api/portraits/women/6.jpg',
        joinedAt: '2023-10-15T00:00:00Z'
      }
    ],
    models: [],
    tags: ['recommendation', 'marketing', 'e-commerce'],
    createdAt: '2023-10-01T00:00:00Z',
    updatedAt: '2024-01-15T11:10:00Z',
    createdBy: 'user-002'
  },
  {
    id: 'proj-006',
    name: 'Supply Chain Optimization',
    description: 'Using advanced analytics to optimize inventory levels and reduce stockouts',
    status: 'completed',
    progress: 100,
    startDate: '2023-07-01T00:00:00Z',
    endDate: '2023-12-31T00:00:00Z',
    members: [
      {
        id: 'user-001',
        name: 'Alex Johnson',
        email: 'alex.johnson@example.com',
        role: 'Project Manager',
        avatar: 'https://randomuser.me/api/portraits/men/1.jpg',
        joinedAt: '2023-07-01T00:00:00Z'
      },
      {
        id: 'user-007',
        name: 'Robert Smith',
        email: 'robert.smith@example.com',
        role: 'Supply Chain Specialist',
        avatar: 'https://randomuser.me/api/portraits/men/7.jpg',
        joinedAt: '2023-07-05T00:00:00Z'
      }
    ],
    models: [
      {
        id: 'model-006',
        name: 'Supply Chain Forecaster',
        type: 'Time Series',
        status: 'active',
        addedAt: '2023-08-01T00:00:00Z'
      }
    ],
    tags: ['supply-chain', 'inventory', 'optimization'],
    createdAt: '2023-07-01T00:00:00Z',
    updatedAt: '2023-12-31T23:59:59Z',
    createdBy: 'user-001'
  }
];

// Feature flag to control whether to use real or mock data
const USE_MOCK_DATA = !process.env.NEXT_PUBLIC_API_URL;

/**
 * Hook for managing projects
 */
export const useProjects = () => {
  // State for the selected project
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);

  // Use our fetch hook for API requests
  const {
    data: projects = USE_MOCK_DATA ? MOCK_PROJECTS : [],
    isLoading: isLoadingProjects,
    error: projectsError,
    fetch: fetchProjectsFromApi,
    invalidateCache,
  } = useFetch<Project[]>(
    'get',
    API_ENDPOINTS.PROJECTS.LIST.path,
    undefined,
    {
      fetchOnMount: !USE_MOCK_DATA,
      shouldCache: true,
      cacheTTL: 60, // 1 minute
    }
  );

  // Fetch projects
  const fetchProjects = useCallback(async () => {
    if (USE_MOCK_DATA) {
      return MOCK_PROJECTS;
    }
    return await fetchProjectsFromApi();
  }, [fetchProjectsFromApi]);

  // Fetch a specific project
  const fetchProject = useCallback(async (id: string) => {
    if (USE_MOCK_DATA) {
      const project = MOCK_PROJECTS.find(p => p.id === id) || null;
      setSelectedProject(project);
      return project;
    }

    try {
      const endpoint = API_ENDPOINTS.PROJECTS.GET(id);
      const response = await fetch(endpoint.path);
      const fetchedProject = response.json();
      setSelectedProject(fetchedProject || null);
      return fetchedProject;
    } catch (error) {
      handleError(error, { context: 'fetchProject', projectId: id });
      return null;
    }
  }, []);

  // Create a new project
  const createProject = useCallback(async (input: CreateProjectInput) => {
    if (USE_MOCK_DATA) {
      // Generate a mock project from the input
      const newId = `proj-${Math.floor(Math.random() * 1000)}`;
      const newProject: Project = {
        id: newId,
        name: input.name,
        description: input.description,
        status: input.status,
        progress: 0,
        startDate: input.startDate,
        endDate: input.endDate,
        tags: input.tags,
        models: [],
        members: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        createdBy: 'current-user',
      };
      
      // In a real app, we would push this to the server
      // For mock purposes, we'll just return the new project
      invalidateCache(); // Invalidate the projects cache
      return newProject;
    }

    try {
      const response = await fetch(API_ENDPOINTS.PROJECTS.CREATE.path, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(input),
      });
      
      const data = await response.json();
      
      // Invalidate the projects cache to refresh the list
      invalidateCache();
      
      return data;
    } catch (error) {
      handleError(error, { context: 'createProject', input });
      throw error;
    }
  }, [invalidateCache]);

  // Update an existing project
  const updateProject = useCallback(async (id: string, input: UpdateProjectInput) => {
    if (USE_MOCK_DATA) {
      // For mock purposes, return a success status
      invalidateCache(); // Invalidate the projects cache
      return { success: true };
    }

    try {
      const endpoint = API_ENDPOINTS.PROJECTS.UPDATE(id);
      const response = await fetch(endpoint.path, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(input),
      });
      
      const data = await response.json();
      
      // Invalidate the projects cache to refresh the list
      invalidateCache();
      
      // If this was the selected project, update it
      if (selectedProject && selectedProject.id === id) {
        fetchProject(id);
      }
      
      return data;
    } catch (error) {
      handleError(error, { context: 'updateProject', projectId: id, input });
      throw error;
    }
  }, [fetchProject, invalidateCache, selectedProject]);

  // Delete a project
  const deleteProject = useCallback(async (id: string) => {
    if (USE_MOCK_DATA) {
      // For mock purposes, return a success status
      invalidateCache(); // Invalidate the projects cache
      return { success: true };
    }

    try {
      const endpoint = API_ENDPOINTS.PROJECTS.DELETE(id);
      const response = await fetch(endpoint.path, {
        method: 'DELETE',
      });
      
      const data = await response.json();
      
      // Invalidate the projects cache to refresh the list
      invalidateCache();
      
      // If this was the selected project, clear it
      if (selectedProject && selectedProject.id === id) {
        setSelectedProject(null);
      }
      
      return data;
    } catch (error) {
      handleError(error, { context: 'deleteProject', projectId: id });
      throw error;
    }
  }, [invalidateCache, selectedProject]);

  // Add a model to a project
  const addModelToProject = useCallback(async (projectId: string, input: AddProjectModelInput) => {
    if (USE_MOCK_DATA) {
      // For mock purposes, return a success status
      invalidateCache(); // Invalidate the projects cache
      return { success: true };
    }

    try {
      const endpoint = API_ENDPOINTS.PROJECTS.ADD_MODEL(projectId);
      const response = await fetch(endpoint.path, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(input),
      });
      
      const data = await response.json();
      
      // Invalidate the projects cache to refresh the list
      invalidateCache();
      
      // If this was the selected project, update it
      if (selectedProject && selectedProject.id === projectId) {
        fetchProject(projectId);
      }
      
      return data;
    } catch (error) {
      handleError(error, { context: 'addModelToProject', projectId, input });
      throw error;
    }
  }, [fetchProject, invalidateCache, selectedProject]);

  // Add a member to a project
  const addMemberToProject = useCallback(async (projectId: string, input: AddProjectMemberInput) => {
    if (USE_MOCK_DATA) {
      // For mock purposes, return a success status
      invalidateCache(); // Invalidate the projects cache
      return { success: true };
    }

    try {
      const endpoint = API_ENDPOINTS.PROJECTS.ADD_MEMBER(projectId);
      const response = await fetch(endpoint.path, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(input),
      });
      
      const data = await response.json();
      
      // Invalidate the projects cache to refresh the list
      invalidateCache();
      
      // If this was the selected project, update it
      if (selectedProject && selectedProject.id === projectId) {
        fetchProject(projectId);
      }
      
      return data;
    } catch (error) {
      handleError(error, { context: 'addMemberToProject', projectId, input });
      throw error;
    }
  }, [fetchProject, invalidateCache, selectedProject]);

  return {
    projects,
    selectedProject,
    isLoadingProjects,
    projectsError,
    fetchProjects,
    fetchProject,
    createProject,
    updateProject,
    deleteProject,
    addModelToProject,
    addMemberToProject,
  };
};

export default useProjects;