'use client';

import React, { useState } from 'react';
import { Plus, Search, Filter, Calendar, Users, Bot, ArrowUpRight, BriefcaseBusiness, Star, Clock, MoreHorizontal, Folder, FileText } from 'lucide-react';
import DashboardLayout from '@/components/layout/dashboard-layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Avatar } from '@/components/ui/avatar';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

type ProjectStatus = 'active' | 'completed' | 'on-hold' | 'planned';

interface ProjectMember {
  id: string;
  name: string;
  role: string;
  avatar?: string;
}

interface ProjectModel {
  id: string;
  name: string;
  type: string;
}

interface Project {
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
}

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

const ProjectCard = ({ project }: { project: Project }) => {
  const getStatusColor = (status: ProjectStatus) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300';
      case 'completed':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300';
      case 'on-hold':
        return 'bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-300';
      case 'planned':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-300';
      default:
        return '';
    }
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <CardTitle className="text-xl">{project.name}</CardTitle>
            <div className="flex items-center gap-2">
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(project.status)}`}>
                {project.status === 'on-hold' ? 'On Hold' : project.status.charAt(0).toUpperCase() + project.status.slice(1)}
              </span>
              <span className="text-sm text-muted-foreground">
                {project.progress}% complete
              </span>
            </div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Actions</DropdownMenuLabel>
              <DropdownMenuItem>View Details</DropdownMenuItem>
              <DropdownMenuItem>Edit Project</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem>Archive Project</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent className="flex-grow">
        <p className="text-sm text-muted-foreground mb-4">{project.description}</p>
        
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">
              {project.startDate} {project.endDate ? `- ${project.endDate}` : '(ongoing)'}
            </span>
          </div>
          
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Users className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Team</span>
            </div>
            <div className="flex -space-x-2 overflow-hidden">
              {project.members.map((member) => (
                <div key={member.id} className="inline-block rounded-full ring-2 ring-background" title={`${member.name} (${member.role})`}>
                  <Avatar className="h-8 w-8">
                    <div className="bg-primary/10 h-full w-full flex items-center justify-center rounded-full text-xs font-medium">
                      {member.name.split(' ').map(n => n[0]).join('')}
                    </div>
                  </Avatar>
                </div>
              ))}
              {project.members.length > 3 && (
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-xs font-medium">
                  +{project.members.length - 3}
                </span>
              )}
            </div>
          </div>
          
          {project.models.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Bot className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">AI Models</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {project.models.map((model) => (
                  <Badge key={model.id} variant="secondary" className="flex items-center gap-1">
                    <Bot className="h-3 w-3" />
                    {model.name}
                  </Badge>
                ))}
              </div>
            </div>
          )}
          
          <div className="flex flex-wrap gap-1 mt-2">
            {project.tags.map((tag, index) => (
              <Badge key={index} variant="outline" className="text-xs bg-muted/50">
                #{tag}
              </Badge>
            ))}
          </div>
        </div>
      </CardContent>
      <CardFooter className="pt-0 border-t">
        <Button variant="outline" size="sm" className="w-full">
          <ArrowUpRight className="h-4 w-4 mr-2" />
          View Project
        </Button>
      </CardFooter>
    </Card>
  );
};

const ProjectsPage = () => {
  const [projects, setProjects] = useState<Project[]>(mockProjects);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState('all');
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);

  // Filter projects based on search query and active tab
  const filteredProjects = projects.filter((project) => {
    // Filter by search query
    const matchesSearch = project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      project.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      project.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
    
    // Filter by tab
    if (activeTab === 'all') return matchesSearch;
    if (activeTab === 'active') return matchesSearch && project.status === 'active';
    if (activeTab === 'completed') return matchesSearch && project.status === 'completed';
    if (activeTab === 'on-hold') return matchesSearch && project.status === 'on-hold';
    if (activeTab === 'planned') return matchesSearch && project.status === 'planned';
    
    return matchesSearch;
  });

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <h1 className="text-3xl font-semibold">Projects</h1>
          <Button onClick={() => setIsCreateDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New Project
          </Button>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
          <div className="relative flex-grow max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search projects..."
              className="pl-9 w-full"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm">
              <Filter className="h-4 w-4 mr-2" />
              Filters
            </Button>
            <Button variant="outline" size="sm">
              <BriefcaseBusiness className="h-4 w-4 mr-2" />
              My Projects
            </Button>
          </div>
        </div>

        <Tabs defaultValue="all" className="w-full" onValueChange={setActiveTab}>
          <TabsList className="grid grid-cols-5 mb-4">
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="active">Active</TabsTrigger>
            <TabsTrigger value="completed">Completed</TabsTrigger>
            <TabsTrigger value="on-hold">On Hold</TabsTrigger>
            <TabsTrigger value="planned">Planned</TabsTrigger>
          </TabsList>
          
          <TabsContent value="all" className="mt-0">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredProjects.length > 0 ? (
                filteredProjects.map((project) => (
                  <ProjectCard key={project.id} project={project} />
                ))
              ) : (
                <div className="col-span-3 h-40 flex items-center justify-center border rounded-md bg-muted/10">
                  <p className="text-muted-foreground">No projects found matching your criteria.</p>
                </div>
              )}
            </div>
          </TabsContent>
          
          {/* Other tabs content will be generated automatically by filtering */}
          <TabsContent value="active" className="mt-0">
            {/* Content for active projects - handled by filteredProjects */}
          </TabsContent>
          
          <TabsContent value="completed" className="mt-0">
            {/* Content for completed projects - handled by filteredProjects */}
          </TabsContent>
          
          <TabsContent value="on-hold" className="mt-0">
            {/* Content for on-hold projects - handled by filteredProjects */}
          </TabsContent>
          
          <TabsContent value="planned" className="mt-0">
            {/* Content for planned projects - handled by filteredProjects */}
          </TabsContent>
        </Tabs>

        {/* Create Project Dialog */}
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogContent className="sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle>Create New Project</DialogTitle>
              <DialogDescription>
                Start a new AI project and configure its basic settings
              </DialogDescription>
            </DialogHeader>

            <div className="grid gap-6 py-4">
              <div className="grid grid-cols-1 gap-4">
                <div className="flex flex-col gap-2">
                  <label htmlFor="name" className="text-sm font-medium">
                    Project Name
                  </label>
                  <Input id="name" placeholder="Enter project name" />
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <label htmlFor="description" className="text-sm font-medium">
                  Description
                </label>
                <Input id="description" placeholder="Describe the purpose and goals of this project" />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-2">
                  <label htmlFor="status" className="text-sm font-medium">
                    Status
                  </label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="Select status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="planned">Planned</SelectItem>
                      <SelectItem value="active">Active</SelectItem>
                      <SelectItem value="on-hold">On Hold</SelectItem>
                      <SelectItem value="completed">Completed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex flex-col gap-2">
                  <label htmlFor="start-date" className="text-sm font-medium">
                    Start Date
                  </label>
                  <Input id="start-date" type="date" />
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <label htmlFor="tags" className="text-sm font-medium">
                  Tags (comma separated)
                </label>
                <Input id="tags" placeholder="E.g., classification, customer-retention, nlp" />
              </div>

              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">Initial Team Members</label>
                  <Button variant="outline" size="sm" className="h-8">
                    <Plus className="h-3 w-3 mr-1" />
                    Add Member
                  </Button>
                </div>
                <div className="border rounded-md p-3 bg-muted/20">
                  <p className="text-sm text-muted-foreground">You will be added as the project owner automatically.</p>
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={() => setIsCreateDialogOpen(false)}>
                <Folder className="h-4 w-4 mr-2" />
                Create Project
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </DashboardLayout>
  );
};

export default ProjectsPage;