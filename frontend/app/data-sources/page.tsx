'use client';

import React, { useState } from 'react';
import { Plus, Search, Filter, Download, ChevronRight, MoreHorizontal, Database, RefreshCcw, File, Table as TableIcon, PieChart, BarChart } from 'lucide-react';
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
import { Spinner } from '@/components/ui/spinner';
import { useToast } from '@/components/ui/use-toast';
import { useDataSources, DataSourceType, DataSourceStatus } from '@/hooks/use-data-sources';

// Map for data source types to labels and icons
const typeIconMap: Record<DataSourceType, React.ReactNode> = {
  'database': <Database className="h-4 w-4" />,
  'csv': <File className="h-4 w-4" />,
  'api': <TableIcon className="h-4 w-4" />,
  'warehouse': <PieChart className="h-4 w-4" />,
  'streaming': <BarChart className="h-4 w-4" />,
};

const typeLabelMap: Record<DataSourceType, string> = {
  'database': 'Database',
  'csv': 'CSV File',
  'api': 'API',
  'warehouse': 'Data Warehouse',
  'streaming': 'Streaming Data',
};

const DataSourceTypeBadge = ({ type }: { type: DataSourceType }) => {
  const colorMap: Record<DataSourceType, string> = {
    'database': 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300',
    'csv': 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300',
    'api': 'bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-300',
    'warehouse': 'bg-amber-100 text-amber-800 dark:bg-amber-900/20 dark:text-amber-300',
    'streaming': 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/20 dark:text-cyan-300',
  };
  
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorMap[type]}`}>
      {typeIconMap[type]}
      <span className="ml-1">{typeLabelMap[type]}</span>
    </span>
  );
};

const StatusBadge = ({ status }: { status: DataSourceStatus }) => {
  const statusMap: Record<DataSourceStatus, { color: string, label: string }> = {
    'connected': { color: 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300', label: 'Connected' },
    'disconnected': { color: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-300', label: 'Disconnected' },
    'pending': { color: 'bg-amber-100 text-amber-800 dark:bg-amber-900/20 dark:text-amber-300', label: 'Pending' },
    'error': { color: 'bg-rose-100 text-rose-800 dark:bg-rose-900/20 dark:text-rose-300', label: 'Error' },
  };
  
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusMap[status].color}`}>
      {statusMap[status].label}
    </span>
  );
};

const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const DataSourcesPage = () => {
  // Get the data sources data using our hook
  const { 
    dataSources, 
    isLoadingDataSources, 
    fetchDataSources, 
    createDataSource, 
    updateDataSource,
    refreshDataSource,
    getDataSourceSchema
  } = useDataSources();
  
  const { toast } = useToast();
  
  // State for UI
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDataSources, setSelectedDataSources] = useState<string[]>([]);
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('all');
  const [schemaDialogOpen, setSchemaDialogOpen] = useState(false);
  const [selectedDataSource, setSelectedDataSource] = useState<string | null>(null);
  const [schema, setSchema] = useState<Record<string, string>[]>([]);
  const [loadingSchema, setLoadingSchema] = useState(false);
  
  // Form state for creating a new data source
  const [newDataSource, setNewDataSource] = useState({
    name: '',
    type: '' as DataSourceType,
    connectionDetails: {
      host: '',
      port: '',
      username: '',
      password: '',
      database: '',
      table: '',
      filePath: '',
      apiUrl: '',
      apiKey: '',
    }
  });
  
  // Filter data sources based on search query and active tab
  const filteredDataSources = dataSources.filter((dataSource) => {
    // Filter by search query
    const matchesSearch = 
      dataSource.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      typeLabelMap[dataSource.type].toLowerCase().includes(searchQuery.toLowerCase());
    
    // Filter by tab
    if (activeTab === 'all') return matchesSearch;
    if (activeTab === 'connected') return matchesSearch && dataSource.status === 'connected';
    if (activeTab === 'disconnected') return matchesSearch && 
      (dataSource.status === 'disconnected' || dataSource.status === 'error');
    if (activeTab === 'pending') return matchesSearch && dataSource.status === 'pending';
    
    return matchesSearch;
  });

  const toggleDataSourceSelection = (id: string) => {
    setSelectedDataSources((current) =>
      current.includes(id)
        ? current.filter((sourceId) => sourceId !== id)
        : [...current, id]
    );
  };

  const toggleSelectAll = () => {
    if (selectedDataSources.length === filteredDataSources.length) {
      setSelectedDataSources([]);
    } else {
      setSelectedDataSources(filteredDataSources.map((source) => source.id));
    }
  };
  
  const handleCreateDataSource = async () => {
    // Validate form
    if (!newDataSource.name || !newDataSource.type) {
      toast({
        title: 'Validation Error',
        description: 'Please fill in all required fields.',
        variant: 'destructive',
      });
      return;
    }
    
    // Validate connection details based on type
    const { connectionDetails } = newDataSource;
    if (
      (newDataSource.type === 'database' && (!connectionDetails.host || !connectionDetails.username)) ||
      (newDataSource.type === 'csv' && !connectionDetails.filePath) ||
      (newDataSource.type === 'api' && !connectionDetails.apiUrl)
    ) {
      toast({
        title: 'Validation Error',
        description: 'Please fill in all required connection details.',
        variant: 'destructive',
      });
      return;
    }
    
    try {
      await createDataSource({
        name: newDataSource.name,
        type: newDataSource.type,
        connectionDetails: newDataSource.connectionDetails,
      });
      
      // Reset form and close dialog
      setNewDataSource({
        name: '',
        type: '' as DataSourceType,
        connectionDetails: {
          host: '',
          port: '',
          username: '',
          password: '',
          database: '',
          table: '',
          filePath: '',
          apiUrl: '',
          apiKey: '',
        }
      });
      
      setIsAddDialogOpen(false);
    } catch (error) {
      console.error('Failed to create data source:', error);
    }
  };
  
  const handleRefreshDataSource = async (id: string) => {
    try {
      await refreshDataSource(id);
      toast({
        title: 'Data refreshed',
        description: 'The data source has been refreshed successfully.',
      });
    } catch (error) {
      console.error('Failed to refresh data source:', error);
    }
  };
  
  const handleViewSchema = async (id: string) => {
    setSelectedDataSource(id);
    setLoadingSchema(true);
    setSchemaDialogOpen(true);
    
    try {
      const schemaData = await getDataSourceSchema(id);
      setSchema(schemaData);
    } catch (error) {
      console.error('Failed to get schema:', error);
      toast({
        title: 'Error',
        description: 'Failed to retrieve schema for this data source.',
        variant: 'destructive',
      });
    } finally {
      setLoadingSchema(false);
    }
  };

  // Format date to locale string
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <h1 className="text-3xl font-semibold">Data Sources</h1>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm">
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
            <Button onClick={() => setIsAddDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              New Data Source
            </Button>
          </div>
        </div>

        <Tabs defaultValue="all" className="w-full" onValueChange={setActiveTab}>
          <TabsList className="grid grid-cols-4 mb-4">
            <TabsTrigger value="all">All Sources</TabsTrigger>
            <TabsTrigger value="connected">Connected</TabsTrigger>
            <TabsTrigger value="disconnected">Disconnected</TabsTrigger>
            <TabsTrigger value="pending">Pending</TabsTrigger>
          </TabsList>
          
          <TabsContent value="all" className="mt-0">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle>Data Source Management</CardTitle>
                <CardDescription>Connect to and manage your data sources</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-col md:flex-row justify-between mb-4 gap-4">
                  <div className="relative w-full md:w-96">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search data sources..."
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
                
                {isLoadingDataSources ? (
                  <div className="flex justify-center items-center h-64">
                    <Spinner size="lg" text="Loading data sources..." />
                  </div>
                ) : (
                  <div className="rounded-md border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-12">
                            <Checkbox
                              checked={selectedDataSources.length === filteredDataSources.length && filteredDataSources.length > 0}
                              onCheckedChange={toggleSelectAll}
                            />
                          </TableHead>
                          <TableHead>Name</TableHead>
                          <TableHead className="hidden md:table-cell">Type</TableHead>
                          <TableHead className="hidden md:table-cell">Size</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead className="hidden lg:table-cell">Last Updated</TableHead>
                          <TableHead className="w-24">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {filteredDataSources.length > 0 ? (
                          filteredDataSources.map((source) => (
                            <TableRow key={source.id}>
                              <TableCell>
                                <Checkbox
                                  checked={selectedDataSources.includes(source.id)}
                                  onCheckedChange={() => toggleDataSourceSelection(source.id)}
                                />
                              </TableCell>
                              <TableCell className="font-medium">{source.name}</TableCell>
                              <TableCell className="hidden md:table-cell">
                                <DataSourceTypeBadge type={source.type} />
                              </TableCell>
                              <TableCell className="hidden md:table-cell">
                                {formatBytes(source.size)}
                              </TableCell>
                              <TableCell>
                                <StatusBadge status={source.status} />
                              </TableCell>
                              <TableCell className="hidden lg:table-cell">
                                {formatDate(source.lastUpdated)}
                              </TableCell>
                              <TableCell>
                                <div className="flex items-center gap-2">
                                  <Button 
                                    variant="ghost" 
                                    size="sm" 
                                    className="h-8 w-8 p-0"
                                    onClick={() => handleRefreshDataSource(source.id)}
                                    disabled={source.status === 'pending'}
                                  >
                                    <RefreshCcw className="h-4 w-4" />
                                    <span className="sr-only">Refresh</span>
                                  </Button>
                                  <Button 
                                    variant="ghost" 
                                    size="sm" 
                                    className="h-8 w-8 p-0"
                                    onClick={() => handleViewSchema(source.id)}
                                  >
                                    <TableIcon className="h-4 w-4" />
                                    <span className="sr-only">View Schema</span>
                                  </Button>
                                  <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                      <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                                        <MoreHorizontal className="h-4 w-4" />
                                        <span className="sr-only">More</span>
                                      </Button>
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent align="end">
                                      <DropdownMenuItem>Edit</DropdownMenuItem>
                                      <DropdownMenuItem>View Details</DropdownMenuItem>
                                      <DropdownMenuItem>Delete</DropdownMenuItem>
                                    </DropdownMenuContent>
                                  </DropdownMenu>
                                </div>
                              </TableCell>
                            </TableRow>
                          ))
                        ) : (
                          <TableRow>
                            <TableCell colSpan={7} className="h-24 text-center">
                              {searchQuery ? 'No data sources found matching your search.' : 'No data sources available.'}
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
          
          <TabsContent value="connected" className="mt-0">
            {/* Same content as "all" but filtered for connected sources */}
          </TabsContent>
          
          <TabsContent value="disconnected" className="mt-0">
            {/* Same content as "all" but filtered for disconnected sources */}
          </TabsContent>
          
          <TabsContent value="pending" className="mt-0">
            {/* Same content as "all" but filtered for pending sources */}
          </TabsContent>
        </Tabs>

        {/* Add Data Source Dialog */}
        <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
          <DialogContent className="sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle>Connect Data Source</DialogTitle>
              <DialogDescription>
                Add a new data source to your project
              </DialogDescription>
            </DialogHeader>

            <div className="grid gap-6 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-2">
                  <label htmlFor="name" className="text-sm font-medium">
                    Data Source Name
                  </label>
                  <Input 
                    id="name" 
                    placeholder="Enter name" 
                    value={newDataSource.name}
                    onChange={(e) => setNewDataSource({ ...newDataSource, name: e.target.value })}
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <label htmlFor="type" className="text-sm font-medium">
                    Data Source Type
                  </label>
                  <Select
                    value={newDataSource.type}
                    onValueChange={(value) => setNewDataSource({ ...newDataSource, type: value as DataSourceType })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="database">Database</SelectItem>
                      <SelectItem value="csv">CSV File</SelectItem>
                      <SelectItem value="api">API</SelectItem>
                      <SelectItem value="warehouse">Data Warehouse</SelectItem>
                      <SelectItem value="streaming">Streaming Data</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Dynamic connection details based on type */}
              {newDataSource.type === 'database' && (
                <div className="space-y-4">
                  <p className="text-sm font-medium">Database Connection Details</p>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="flex flex-col gap-2">
                      <label htmlFor="host" className="text-sm font-medium">
                        Host
                      </label>
                      <Input 
                        id="host" 
                        placeholder="e.g. localhost" 
                        value={newDataSource.connectionDetails.host}
                        onChange={(e) => setNewDataSource({ 
                          ...newDataSource, 
                          connectionDetails: { 
                            ...newDataSource.connectionDetails, 
                            host: e.target.value 
                          } 
                        })}
                      />
                    </div>
                    <div className="flex flex-col gap-2">
                      <label htmlFor="port" className="text-sm font-medium">
                        Port
                      </label>
                      <Input 
                        id="port" 
                        placeholder="e.g. 5432" 
                        value={newDataSource.connectionDetails.port}
                        onChange={(e) => setNewDataSource({ 
                          ...newDataSource, 
                          connectionDetails: { 
                            ...newDataSource.connectionDetails, 
                            port: e.target.value 
                          } 
                        })}
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="flex flex-col gap-2">
                      <label htmlFor="username" className="text-sm font-medium">
                        Username
                      </label>
                      <Input 
                        id="username" 
                        placeholder="Enter username" 
                        value={newDataSource.connectionDetails.username}
                        onChange={(e) => setNewDataSource({ 
                          ...newDataSource, 
                          connectionDetails: { 
                            ...newDataSource.connectionDetails, 
                            username: e.target.value 
                          } 
                        })}
                      />
                    </div>
                    <div className="flex flex-col gap-2">
                      <label htmlFor="password" className="text-sm font-medium">
                        Password
                      </label>
                      <Input 
                        id="password" 
                        type="password"
                        placeholder="Enter password" 
                        value={newDataSource.connectionDetails.password}
                        onChange={(e) => setNewDataSource({ 
                          ...newDataSource, 
                          connectionDetails: { 
                            ...newDataSource.connectionDetails, 
                            password: e.target.value 
                          } 
                        })}
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="flex flex-col gap-2">
                      <label htmlFor="database" className="text-sm font-medium">
                        Database Name
                      </label>
                      <Input 
                        id="database" 
                        placeholder="Enter database name" 
                        value={newDataSource.connectionDetails.database}
                        onChange={(e) => setNewDataSource({ 
                          ...newDataSource, 
                          connectionDetails: { 
                            ...newDataSource.connectionDetails, 
                            database: e.target.value 
                          } 
                        })}
                      />
                    </div>
                    <div className="flex flex-col gap-2">
                      <label htmlFor="table" className="text-sm font-medium">
                        Table (Optional)
                      </label>
                      <Input 
                        id="table" 
                        placeholder="Enter table name" 
                        value={newDataSource.connectionDetails.table}
                        onChange={(e) => setNewDataSource({ 
                          ...newDataSource, 
                          connectionDetails: { 
                            ...newDataSource.connectionDetails, 
                            table: e.target.value 
                          } 
                        })}
                      />
                    </div>
                  </div>
                </div>
              )}
              
              {newDataSource.type === 'csv' && (
                <div className="flex flex-col gap-2">
                  <label htmlFor="filePath" className="text-sm font-medium">
                    File Location
                  </label>
                  <Input 
                    id="filePath" 
                    placeholder="Enter file path or URL" 
                    value={newDataSource.connectionDetails.filePath}
                    onChange={(e) => setNewDataSource({ 
                      ...newDataSource, 
                      connectionDetails: { 
                        ...newDataSource.connectionDetails, 
                        filePath: e.target.value 
                      } 
                    })}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Specify a local file path, S3 URL, or Azure Blob Storage URL
                  </p>
                </div>
              )}
              
              {newDataSource.type === 'api' && (
                <div className="space-y-4">
                  <div className="flex flex-col gap-2">
                    <label htmlFor="apiUrl" className="text-sm font-medium">
                      API URL
                    </label>
                    <Input 
                      id="apiUrl" 
                      placeholder="https://api.example.com/data" 
                      value={newDataSource.connectionDetails.apiUrl}
                      onChange={(e) => setNewDataSource({ 
                        ...newDataSource, 
                        connectionDetails: { 
                          ...newDataSource.connectionDetails, 
                          apiUrl: e.target.value 
                        } 
                      })}
                    />
                  </div>
                  <div className="flex flex-col gap-2">
                    <label htmlFor="apiKey" className="text-sm font-medium">
                      API Key (Optional)
                    </label>
                    <Input 
                      id="apiKey" 
                      placeholder="Enter API key" 
                      value={newDataSource.connectionDetails.apiKey}
                      onChange={(e) => setNewDataSource({ 
                        ...newDataSource, 
                        connectionDetails: { 
                          ...newDataSource.connectionDetails, 
                          apiKey: e.target.value 
                        } 
                      })}
                    />
                  </div>
                </div>
              )}
              
              {(newDataSource.type === 'warehouse' || newDataSource.type === 'streaming') && (
                <div className="p-4 border rounded-md">
                  <p className="text-sm text-center text-muted-foreground">
                    Advanced configuration for {typeLabelMap[newDataSource.type]} will be provided after initial setup.
                  </p>
                </div>
              )}
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setIsAddDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreateDataSource}>
                <Database className="h-4 w-4 mr-2" />
                Connect
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
        
        {/* Schema Dialog */}
        <Dialog open={schemaDialogOpen} onOpenChange={setSchemaDialogOpen}>
          <DialogContent className="sm:max-w-[800px]">
            <DialogHeader>
              <DialogTitle>Data Source Schema</DialogTitle>
              <DialogDescription>
                {selectedDataSource && dataSources.find(ds => ds.id === selectedDataSource)?.name}
              </DialogDescription>
            </DialogHeader>
            
            <div className="py-4">
              {loadingSchema ? (
                <div className="flex justify-center items-center h-64">
                  <Spinner size="lg" text="Loading schema..." />
                </div>
              ) : (
                schema.length > 0 ? (
                  <div className="rounded-md border max-h-[60vh] overflow-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Field Name</TableHead>
                          <TableHead>Data Type</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {schema.map((field, index) => (
                          <TableRow key={index}>
                            <TableCell className="font-medium">{field.name}</TableCell>
                            <TableCell>{field.type}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                ) : (
                  <div className="text-center p-8 border rounded-md">
                    <p className="text-muted-foreground">No schema information available</p>
                  </div>
                )
              )}
            </div>
            
            <DialogFooter>
              <Button onClick={() => setSchemaDialogOpen(false)}>Close</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </DashboardLayout>
  );
};

export default DataSourcesPage;