'use client';

import React, { useState, useEffect } from 'react';
import { Plus, Search, SlidersHorizontal, Download, Trash, Settings, PlayCircle, PauseCircle, Bot, Brain, Gauge, Zap } from 'lucide-react';
import DashboardLayout from '@/components/layout/dashboard-layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '@/components/ui/table';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Spinner } from '@/components/ui/spinner';
import { useToast } from '@/components/ui/use-toast';
import { useModels, ModelType, ModelStatus } from '@/hooks/use-models';
import { useDataSources } from '@/hooks/use-data-sources';

const typeLabelMap: Record<ModelType, string> = {
  'classification': 'Classification',
  'regression': 'Regression',
  'nlp': 'Natural Language Processing',
  'computer-vision': 'Computer Vision',
  'time-series': 'Time Series Forecasting'
};

const typeIconMap: Record<ModelType, React.ReactNode> = {
  'classification': <Bot className="h-4 w-4" />,
  'regression': <Gauge className="h-4 w-4" />,
  'nlp': <Brain className="h-4 w-4" />,
  'computer-vision': <Zap className="h-4 w-4" />,
  'time-series': <Settings className="h-4 w-4" />
};

const ModelTypeBadge = ({ type }: { type: ModelType }) => {
  const colorMap: Record<ModelType, string> = {
    'classification': 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300',
    'regression': 'bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-300',
    'nlp': 'bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-300',
    'computer-vision': 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300',
    'time-series': 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/20 dark:text-cyan-300'
  };
  
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorMap[type]}`}>
      {typeIconMap[type]}
      <span className="ml-1">{typeLabelMap[type]}</span>
    </span>
  );
};

const StatusBadge = ({ status }: { status: ModelStatus }) => {
  const statusMap: Record<ModelStatus, { color: string, label: string }> = {
    'active': { color: 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300', label: 'Active' },
    'training': { color: 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300', label: 'Training' },
    'inactive': { color: 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-300', label: 'Inactive' },
    'error': { color: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-300', label: 'Error' }
  };
  
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusMap[status].color}`}>
      {status === 'active' && <PlayCircle className="h-3 w-3 mr-1" />}
      {status === 'training' && <Spinner size="sm" className="mr-1" />}
      {status === 'inactive' && <PauseCircle className="h-3 w-3 mr-1" />}
      {status === 'error' && <Trash className="h-3 w-3 mr-1" />}
      {statusMap[status].label}
    </span>
  );
};

const ModelsPage = () => {
  // Get the models data using our hook
  const { models, isLoadingModels, fetchModels, createModel, updateModel, trainModel } = useModels();
  const { dataSources, isLoadingDataSources, fetchDataSources } = useDataSources();
  const { toast } = useToast();
  
  // State for UI
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('all');
  
  // Form state for creating a new model
  const [newModel, setNewModel] = useState({
    name: '',
    type: '' as ModelType,
    framework: '',
    version: '',
    description: '',
    dataSourceIds: [] as string[],
  });
  
  // Load data sources when opening the create model dialog
  useEffect(() => {
    if (isAddDialogOpen && !dataSources.length && !isLoadingDataSources) {
      fetchDataSources();
    }
  }, [isAddDialogOpen, dataSources.length, isLoadingDataSources, fetchDataSources]);
  
  // Filter models based on search query and active tab
  const filteredModels = models.filter((model) => {
    // Filter by search query
    const matchesSearch = model.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      model.framework.toLowerCase().includes(searchQuery.toLowerCase()) ||
      typeLabelMap[model.type].toLowerCase().includes(searchQuery.toLowerCase());
    
    // Filter by tab
    if (activeTab === 'all') return matchesSearch;
    if (activeTab === 'active') return matchesSearch && model.status === 'active';
    if (activeTab === 'training') return matchesSearch && model.status === 'training';
    if (activeTab === 'inactive') return matchesSearch && (model.status === 'inactive' || model.status === 'error');
    
    return matchesSearch;
  });

  const toggleModelSelection = (id: string) => {
    setSelectedModels((current) =>
      current.includes(id)
        ? current.filter((modelId) => modelId !== id)
        : [...current, id]
    );
  };

  const toggleSelectAll = () => {
    if (selectedModels.length === filteredModels.length) {
      setSelectedModels([]);
    } else {
      setSelectedModels(filteredModels.map((model) => model.id));
    }
  };
  
  const handleCreateModel = async () => {
    // Validate form
    if (!newModel.name || !newModel.type || !newModel.framework || !newModel.version) {
      toast({
        title: 'Validation Error',
        description: 'Please fill in all required fields.',
        variant: 'destructive',
      });
      return;
    }
    
    try {
      await createModel({
        name: newModel.name,
        type: newModel.type,
        framework: newModel.framework,
        version: newModel.version,
        description: newModel.description,
        dataSourceIds: newModel.dataSourceIds,
      });
      
      // Reset form and close dialog
      setNewModel({
        name: '',
        type: '' as ModelType,
        framework: '',
        version: '',
        description: '',
        dataSourceIds: [],
      });
      
      setIsAddDialogOpen(false);
    } catch (error) {
      // Error is handled by the hook, so we don't need additional handling here
      console.error('Failed to create model:', error);
    }
  };
  
  const handleTrainModel = async (id: string) => {
    try {
      await trainModel(id);
    } catch (error) {
      // Error is handled by the hook, so we don't need additional handling here
      console.error('Failed to train model:', error);
    }
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <h1 className="text-3xl font-semibold">AI Models</h1>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm">
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
            <Button onClick={() => setIsAddDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              New Model
            </Button>
          </div>
        </div>

        <Tabs defaultValue="all" className="w-full" onValueChange={setActiveTab}>
          <TabsList className="grid grid-cols-4 mb-4">
            <TabsTrigger value="all">All Models</TabsTrigger>
            <TabsTrigger value="active">Active</TabsTrigger>
            <TabsTrigger value="training">Training</TabsTrigger>
            <TabsTrigger value="inactive">Inactive</TabsTrigger>
          </TabsList>
          
          <TabsContent value="all" className="mt-0">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle>Model Management</CardTitle>
                <CardDescription>View and manage your AI models</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-col md:flex-row justify-between mb-4 gap-4">
                  <div className="relative w-full md:w-96">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search models..."
                      className="pl-9 w-full"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                  </div>
                  <Button variant="outline" size="sm">
                    <SlidersHorizontal className="h-4 w-4 mr-2" />
                    Filters
                  </Button>
                </div>
                
                {isLoadingModels ? (
                  <div className="flex justify-center items-center h-64">
                    <Spinner size="lg" text="Loading models..." />
                  </div>
                ) : (
                  <div className="rounded-md border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-12">
                            <Checkbox
                              checked={selectedModels.length === filteredModels.length && filteredModels.length > 0}
                              onCheckedChange={toggleSelectAll}
                            />
                          </TableHead>
                          <TableHead>Name</TableHead>
                          <TableHead className="hidden md:table-cell">Type</TableHead>
                          <TableHead className="hidden md:table-cell">Framework</TableHead>
                          <TableHead className="hidden lg:table-cell">Accuracy</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead className="hidden lg:table-cell">Last Trained</TableHead>
                          <TableHead className="w-24">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {filteredModels.length > 0 ? (
                          filteredModels.map((model) => (
                            <TableRow key={model.id}>
                              <TableCell>
                                <Checkbox
                                  checked={selectedModels.includes(model.id)}
                                  onCheckedChange={() => toggleModelSelection(model.id)}
                                />
                              </TableCell>
                              <TableCell className="font-medium">{model.name}</TableCell>
                              <TableCell className="hidden md:table-cell">
                                <ModelTypeBadge type={model.type} />
                              </TableCell>
                              <TableCell className="hidden md:table-cell">{model.framework} v{model.version}</TableCell>
                              <TableCell className="hidden lg:table-cell">
                                <span className="font-medium">{(model.accuracy * 100).toFixed(1)}%</span>
                              </TableCell>
                              <TableCell>
                                <StatusBadge status={model.status} />
                              </TableCell>
                              <TableCell className="hidden lg:table-cell">{model.lastTrained}</TableCell>
                              <TableCell>
                                <div className="flex items-center gap-2">
                                  <Button 
                                    variant="ghost" 
                                    size="sm" 
                                    className="h-8 w-8 p-0"
                                    onClick={() => handleTrainModel(model.id)}
                                    disabled={model.status === 'training'}
                                  >
                                    <PlayCircle className="h-4 w-4" />
                                    <span className="sr-only">Run Model</span>
                                  </Button>
                                  <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                                    <Settings className="h-4 w-4" />
                                    <span className="sr-only">Settings</span>
                                  </Button>
                                </div>
                              </TableCell>
                            </TableRow>
                          ))
                        ) : (
                          <TableRow>
                            <TableCell colSpan={8} className="h-24 text-center">
                              {searchQuery ? 'No models found matching your search.' : 'No models available.'}
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="active" className="mt-0">
            {/* Same content as "all" but filtered for active models */}
          </TabsContent>
          
          <TabsContent value="training" className="mt-0">
            {/* Same content as "all" but filtered for training models */}
          </TabsContent>
          
          <TabsContent value="inactive" className="mt-0">
            {/* Same content as "all" but filtered for inactive models */}
          </TabsContent>
        </Tabs>

        {/* Add Model Dialog */}
        <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
          <DialogContent className="sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle>Create New AI Model</DialogTitle>
              <DialogDescription>
                Configure and create a new AI model for your data
              </DialogDescription>
            </DialogHeader>

            <div className="grid gap-6 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-2">
                  <label htmlFor="name" className="text-sm font-medium">
                    Model Name
                  </label>
                  <Input 
                    id="name" 
                    placeholder="Enter model name" 
                    value={newModel.name}
                    onChange={(e) => setNewModel({ ...newModel, name: e.target.value })}
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <label htmlFor="type" className="text-sm font-medium">
                    Model Type
                  </label>
                  <Select 
                    value={newModel.type} 
                    onValueChange={(value) => setNewModel({ ...newModel, type: value as ModelType })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="classification">Classification</SelectItem>
                      <SelectItem value="regression">Regression</SelectItem>
                      <SelectItem value="nlp">Natural Language Processing</SelectItem>
                      <SelectItem value="computer-vision">Computer Vision</SelectItem>
                      <SelectItem value="time-series">Time Series Forecasting</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-2">
                  <label htmlFor="framework" className="text-sm font-medium">
                    Framework
                  </label>
                  <Select
                    value={newModel.framework}
                    onValueChange={(value) => setNewModel({ ...newModel, framework: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select framework" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="TensorFlow">TensorFlow</SelectItem>
                      <SelectItem value="PyTorch">PyTorch</SelectItem>
                      <SelectItem value="Scikit-learn">Scikit-learn</SelectItem>
                      <SelectItem value="Hugging Face">Hugging Face</SelectItem>
                      <SelectItem value="BERT">BERT</SelectItem>
                      <SelectItem value="Custom">Custom</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex flex-col gap-2">
                  <label htmlFor="version" className="text-sm font-medium">
                    Version
                  </label>
                  <Input 
                    id="version" 
                    placeholder="e.g., 1.0" 
                    value={newModel.version}
                    onChange={(e) => setNewModel({ ...newModel, version: e.target.value })}
                  />
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <label htmlFor="data-source" className="text-sm font-medium">
                  Data Source
                </label>
                <Select
                  disabled={isLoadingDataSources || dataSources.length === 0}
                  value={newModel.dataSourceIds[0]} // For simplicity, we're just handling a single data source
                  onValueChange={(value) => setNewModel({ ...newModel, dataSourceIds: [value] })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={
                      isLoadingDataSources 
                        ? "Loading data sources..." 
                        : dataSources.length === 0 
                          ? "No data sources available" 
                          : "Select data source"
                    } />
                  </SelectTrigger>
                  <SelectContent>
                    {dataSources.map((ds) => (
                      <SelectItem key={ds.id} value={ds.id}>{ds.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex flex-col gap-2">
                <label htmlFor="description" className="text-sm font-medium">
                  Description
                </label>
                <Input 
                  id="description" 
                  placeholder="Describe the purpose and functionality of this model" 
                  value={newModel.description}
                  onChange={(e) => setNewModel({ ...newModel, description: e.target.value })}
                />
              </div>

              <div className="flex flex-col gap-2">
                <label htmlFor="params" className="text-sm font-medium">
                  Advanced Parameters
                </label>
                <div className="border p-3 rounded-md bg-muted/40">
                  <div className="text-sm text-muted-foreground">
                    Advanced model configuration will be available after initial setup
                  </div>
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setIsAddDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreateModel}>
                <Bot className="h-4 w-4 mr-2" />
                Create Model
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </DashboardLayout>
  );
};

export default ModelsPage;