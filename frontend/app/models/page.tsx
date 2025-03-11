'use client';

import React, { useState } from 'react';
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

type ModelType = 'classification' | 'regression' | 'nlp' | 'computer-vision' | 'time-series';
type ModelStatus = 'active' | 'training' | 'inactive' | 'error';

interface AIModel {
  id: string;
  name: string;
  type: ModelType;
  framework: string;
  version: string;
  accuracy: number;
  status: ModelStatus;
  lastTrained: string;
  createdBy: string;
}

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
  const [models, setModels] = useState<AIModel[]>(mockModels);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('all');
  
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
                                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
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
                            No models found.
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
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
                  <Input id="name" placeholder="Enter model name" />
                </div>
                <div className="flex flex-col gap-2">
                  <label htmlFor="type" className="text-sm font-medium">
                    Model Type
                  </label>
                  <Select>
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
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="Select framework" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="tensorflow">TensorFlow</SelectItem>
                      <SelectItem value="pytorch">PyTorch</SelectItem>
                      <SelectItem value="scikit-learn">Scikit-learn</SelectItem>
                      <SelectItem value="huggingface">Hugging Face</SelectItem>
                      <SelectItem value="custom">Custom</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex flex-col gap-2">
                  <label htmlFor="data-source" className="text-sm font-medium">
                    Data Source
                  </label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="Select data source" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="customer-db">Customer Database</SelectItem>
                      <SelectItem value="product-catalog">Product Catalog</SelectItem>
                      <SelectItem value="sales-transactions">Sales Transactions</SelectItem>
                      <SelectItem value="user-activity">User Activity Logs</SelectItem>
                      <SelectItem value="inventory">Inventory Data</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <label htmlFor="description" className="text-sm font-medium">
                  Description
                </label>
                <Input id="description" placeholder="Describe the purpose and functionality of this model" />
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
              <Button onClick={() => setIsAddDialogOpen(false)}>
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