'use client';

import React, { useState } from 'react';
import { Plus, Search, Filter, Download, ChevronRight, MoreHorizontal, Calendar, Users, Bot } from 'lucide-react';
import Link from 'next/link';
import DashboardLayout from '@/components/layout/dashboard-layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '@/components/ui/table';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Spinner } from '@/components/ui/spinner';
import { useToast } from '@/components/ui/use-toast';
import { useProjects, ProjectStatus } from '@/hooks/use-projects';
import { useModels } from '@/hooks/use-models';

const statusLabelMap: Record<ProjectStatus, string> = {
  'active': 'Active',
  'completed': 'Completed',
  'paused': 'Paused',
  'planning': 'Planning',
};

const statusColorMap: Record<ProjectStatus, string> = {
  'active': 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300',
  'completed': 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300',
  'paused': 'bg-amber-100 text-amber-800 dark:bg-amber-900/20 dark:text-amber-300',
  'planning': 'bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-300',
};

const ProjectStatusBadge = ({ status }: { status: ProjectStatus }) => {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColorMap[status]}`}>
      {statusLabelMap[status]}
    </span>
  );
};

function getProgressColor(progress: number) {
  if (progress < 25) return 'bg-red-500';
  if (progress < 50) return 'bg-amber-500';
  if (progress < 75) return 'bg-blue-500';
  return 'bg-green-500';
}

const ProgressBar = ({ progress }: { progress: number }) => {
  const color = getProgressColor(progress);
  
  return (
    <div className="w-full bg-gray-200 rounded-full h-2 dark:bg-gray-700">
      <div 
        className={`${color} h-2 rounded-full`} 
        style={{ width: `${progress}%` }}
      />
    </div>
  );
};

const ProjectsPage = () => {
  // Get the projects data using our hook
  const { 
    projects, 
    isLoadingProjects, 
    fetchProjects, 
    createProject, 
    updateProject
  } = useProjects();
  
  const { models, isLoadingModels, fetchModels } = useModels();
  const { toast } = useToast();
  
  // State for UI
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedProjects, setSelectedProjects] = useState<string[]>([]);
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('all');
  
  // Form state for creating a new project
  const [newProject, setNewProject] = useState({
    name: '',
    description: '',
    status: 'planning' as ProjectStatus,
    startDate: '',
    endDate: '',
    modelIds: [] as string[],
    tags: [] as string[],
  });
  
  // Load models when opening the create project dialog
  React.useEffect(() => {
    if (isAddDialogOpen && !models.length && !isLoadingModels) {
      fetchModels();
    }
  }, [isAddDialogOpen, models.length, isLoadingModels, fetchModels]);
  
  // Filter projects based on search query and active tab
  const filteredProjects = projects.filter((project) => {
    // Filter by search query
    const matchesSearch = 
      project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      project.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (project.tags && project.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase())));
    
    // Filter by tab
    if (activeTab === 'all') return matchesSearch;
    if (activeTab === 'active') return matchesSearch && project.status === 'active';
    if (activeTab === 'planning') return matchesSearch && project.status === 'planning';
    if (activeTab === 'completed') return matchesSearch && project.status === 'completed';
    
    return matchesSearch;
  });

  const toggleProjectSelection = (id: string) => {
    setSelectedProjects((current) =>
      current.includes(id)
        ? current.filter((projectId) => projectId !== id)
        : [...current, id]
    );
  };

  const toggleSelectAll = () => {
    if (selectedProjects.length === filteredProjects.length) {
      setSelectedProjects([]);
    } else {
      setSelectedProjects(filteredProjects.map((project) => project.id));
    }
  };
  
  const handleCreateProject = async () => {
    // Validate form
    if (!newProject.name || !newProject.status || !newProject.startDate) {
      toast({
        title: 'Validation Error',
        description: 'Please fill in all required fields.',
        variant: 'destructive',
      });
      return;
    }
    
    try {
      await createProject({
        name: newProject.name,
        description: newProject.description,
        status: newProject.status,
        startDate: new Date(newProject.startDate).toISOString(),
        endDate: newProject.endDate ? new Date(newProject.endDate).toISOString() : undefined,
        modelIds: newProject.modelIds,
        tags: newProject.tags,
      });
      
      // Reset form and close dialog
      setNewProject({
        name: '',
        description: '',
        status: 'planning',
        startDate: '',
        endDate: '',
        modelIds: [],
        tags: [],
      });
      
      setIsAddDialogOpen(false);
    } catch (error) {
      console.error('Failed to create project:', error);
    }
  };

  // Format date to locale string
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric'
    });
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <h1 className="text-3xl font-semibold">Projects</h1>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm">
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
            <Button onClick={() => setIsAddDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              New Project
            </Button>
          </div>
        </div>

        <Tabs defaultValue="all" className="w-full" onValueChange={setActiveTab}>
          <TabsList className="grid grid-cols-4 mb-4">
            <TabsTrigger value="all">All Projects</TabsTrigger>
            <TabsTrigger value="active">Active</TabsTrigger>
            <TabsTrigger value="planning">Planning</TabsTrigger>
            <TabsTrigger value="completed">Completed</TabsTrigger>
          </TabsList>
          
          <TabsContent value="all" className="mt-0">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle>Project Management</CardTitle>
                <CardDescription>View and manage your AI projects</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-col md:flex-row justify-between mb-4 gap-4">
                  <div className="relative w-full md:w-96">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search projects..."
                      className="pl-9 w-full"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                  </div>
                  <Button variant="outline" size="sm">
                    <Filter className="h-4 w-4 mr-2" />
                    Filters
                  </Button>
                </div>
                
                {isLoadingProjects ? (
                  <div className="flex justify-center items-center h-64">
                    <Spinner size="lg" text="Loading projects..." />
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredProjects.length > 0 ? (
                      filteredProjects.map((project) => (
                        <Card key={project.id} className="h-full flex flex-col">
                          <CardHeader className="pb-2">
                            <div className="flex justify-between items-start">
                              <ProjectStatusBadge status={project.status} />
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <Button variant="ghost" size="icon" className="h-8 w-8">
                                    <MoreHorizontal className="h-4 w-4" />
                                    <span className="sr-only">Menu</span>
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                  <DropdownMenuItem>Edit</DropdownMenuItem>
                                  <DropdownMenuItem>View Details</DropdownMenuItem>
                                  <DropdownMenuItem>Archive</DropdownMenuItem>
                                </DropdownMenuContent>
                              </DropdownMenu>
                            </div>
                            <CardTitle className="text-lg mt-2">{project.name}</CardTitle>
                            <CardDescription className="line-clamp-2">{project.description}</CardDescription>
                          </CardHeader>
                          <CardContent className="pb-2 flex-grow">
                            <div className="space-y-4">
                              <div>
                                <div className="flex justify-between text-sm mb-1">
                                  <span className="text-muted-foreground">Progress</span>
                                  <span className="font-medium">{project.progress}%</span>
                                </div>
                                <ProgressBar progress={project.progress} />
                              </div>
                              
                              <div className="flex justify-between items-center">
                                <div className="flex items-center gap-1 text-sm text-muted-foreground">
                                  <Calendar className="h-3.5 w-3.5" />
                                  <span>{formatDate(project.startDate)}</span>
                                </div>
                                
                                <div className="flex -space-x-2">
                                  {project.members && project.members.slice(0, 3).map((member, index) => (
                                    <Avatar key={index} className="border-2 border-background h-7 w-7">
                                      <AvatarImage src={member.avatar} alt={member.name} />
                                      <AvatarFallback>{member.name.charAt(0)}</AvatarFallback>
                                    </Avatar>
                                  ))}
                                  {project.members && project.members.length > 3 && (
                                    <div className="flex items-center justify-center h-7 w-7 rounded-full border-2 border-background bg-muted text-xs font-medium">
                                      +{project.members.length - 3}
                                    </div>
                                  )}
                                </div>
                              </div>
                              
                              {project.tags && project.tags.length > 0 && (
                                <div className="flex flex-wrap gap-1">
                                  {project.tags.map((tag, index) => (
                                    <Badge key={index} variant="outline" className="text-xs">
                                      {tag}
                                    </Badge>
                                  ))}
                                </div>
                              )}
                              
                              {project.models && project.models.length > 0 && (
                                <div className="flex flex-wrap gap-1">
                                  {project.models.map((model, index) => (
                                    <Badge key={index} variant="secondary" className="text-xs flex items-center">
                                      <Bot className="h-3 w-3 mr-1" />
                                      {model.name}
                                    </Badge>
                                  ))}
                                </div>
                              )}
                            </div>
                          </CardContent>
                          <CardFooter className="pt-0">
                            <Button asChild variant="ghost" size="sm" className="w-full justify-between">
                              <Link href={`/projects/${project.id}`}>
                                View Details
                                <ChevronRight className="h-4 w-4" />
                              </Link>
                            </Button>
                          </CardFooter>
                        </Card>
                      ))
                    ) : (
                      <div className="col-span-full flex justify-center items-center h-64 border rounded-md">
                        <div className="text-center">
                          <p className="text-muted-foreground mb-4">
                            {searchQuery ? 'No projects found matching your search.' : 'No projects available.'}
                          </p>
                          <Button onClick={() => setIsAddDialogOpen(true)}>
                            <Plus className="h-4 w-4 mr-2" />
                            Create Project
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="active" className="mt-0">
            {/* Same content as "all" but filtered for active projects */}
          </TabsContent>
          
          <TabsContent value="planning" className="mt-0">
            {/* Same content as "all" but filtered for planning projects */}
          </TabsContent>
          
          <TabsContent value="completed" className="mt-0">
            {/* Same content as "all" but filtered for completed projects */}
          </TabsContent>
        </Tabs>

        {/* Add Project Dialog */}
        <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
          <DialogContent className="sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle>Create New Project</DialogTitle>
              <DialogDescription>
                Configure and create a new AI project
              </DialogDescription>
            </DialogHeader>

            <div className="grid gap-6 py-4">
              <div className="grid grid-cols-1 gap-4">
                <div className="flex flex-col gap-2">
                  <label htmlFor="name" className="text-sm font-medium">
                    Project Name
                  </label>
                  <Input 
                    id="name" 
                    placeholder="Enter project name" 
                    value={newProject.name}
                    onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                  />
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <label htmlFor="description" className="text-sm font-medium">
                  Description
                </label>
                <Input 
                  id="description" 
                  placeholder="Describe the project purpose and goals" 
                  value={newProject.description}
                  onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-2">
                  <label htmlFor="status" className="text-sm font-medium">
                    Status
                  </label>
                  <Select
                    value={newProject.status}
                    onValueChange={(value) => setNewProject({ ...newProject, status: value as ProjectStatus })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="planning">Planning</SelectItem>
                      <SelectItem value="active">Active</SelectItem>
                      <SelectItem value="paused">Paused</SelectItem>
                      <SelectItem value="completed">Completed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex flex-col gap-2">
                  <label htmlFor="tags" className="text-sm font-medium">
                    Tags
                  </label>
                  <Input 
                    id="tags" 
                    placeholder="Enter comma-separated tags" 
                    value={newProject.tags.join(', ')}
                    onChange={(e) => setNewProject({ 
                      ...newProject, 
                      tags: e.target.value.split(',').map(tag => tag.trim()).filter(Boolean)
                    })}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-2">
                  <label htmlFor="startDate" className="text-sm font-medium">
                    Start Date
                  </label>
                  <Input 
                    id="startDate" 
                    type="date"
                    value={newProject.startDate}
                    onChange={(e) => setNewProject({ ...newProject, startDate: e.target.value })}
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <label htmlFor="endDate" className="text-sm font-medium">
                    End Date
                  </label>
                  <Input 
                    id="endDate" 
                    type="date"
                    value={newProject.endDate}
                    onChange={(e) => setNewProject({ ...newProject, endDate: e.target.value })}
                  />
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <label htmlFor="models" className="text-sm font-medium">
                  Associated Models
                </label>
                <Select
                  disabled={isLoadingModels || models.length === 0}
                  value={newProject.modelIds[0]} // For simplicity, we're just handling a single model
                  onValueChange={(value) => setNewProject({ ...newProject, modelIds: [value] })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={
                      isLoadingModels 
                        ? "Loading models..." 
                        : models.length === 0 
                          ? "No models available" 
                          : "Select model"
                    } />
                  </SelectTrigger>
                  <SelectContent>
                    {models.map((model) => (
                      <SelectItem key={model.id} value={model.id}>{model.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setIsAddDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreateProject}>
                <Plus className="h-4 w-4 mr-2" />
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