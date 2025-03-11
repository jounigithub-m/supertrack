'use client';

import React, { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { FileJson, FileCode, Download } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

export default function ApiDocsPage() {
  const [activeTab, setActiveTab] = useState<string>('html');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  // Function to download documentation in different formats
  const handleDownload = (format: string) => {
    const filename = format === 'openapi' 
      ? 'supertrack-api-openapi.json'
      : 'supertrack-api-docs.json';
      
    window.open(`/api/documentation?format=${format}`, '_blank');
  };
  
  return (
    <div className="container mx-auto py-6">
      <div className="flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold tracking-tight">API Documentation</h1>
          <div className="flex items-center gap-2">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => handleDownload('json')}
            >
              <FileJson className="h-4 w-4 mr-2" />
              JSON
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => handleDownload('openapi')}
            >
              <FileCode className="h-4 w-4 mr-2" />
              OpenAPI
            </Button>
          </div>
        </div>
        
        <Card>
          <CardHeader>
            <CardTitle>Supertrack API</CardTitle>
            <CardDescription>
              Complete documentation for the Supertrack API, including endpoints, parameters, and response formats.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="html" className="w-full" onValueChange={setActiveTab}>
              <TabsList className="mb-4">
                <TabsTrigger value="html">HTML View</TabsTrigger>
                <TabsTrigger value="interactive">Interactive</TabsTrigger>
              </TabsList>
              
              <TabsContent value="html" className="mt-0">
                <div className="bg-white dark:bg-black rounded-md border p-0 overflow-hidden w-full h-[calc(100vh-300px)]">
                  <iframe 
                    src="/api/documentation?format=html" 
                    className="w-full h-full"
                    title="API Documentation"
                  />
                </div>
              </TabsContent>
              
              <TabsContent value="interactive" className="mt-0">
                <div className="flex flex-col items-center justify-center p-12 text-center gap-4">
                  <FileCode size={48} className="text-primary" />
                  <h3 className="text-xl font-semibold">Interactive Documentation</h3>
                  <p className="text-muted-foreground max-w-md">
                    We're working on an interactive API documentation experience.
                    Check back soon for a fully interactive API explorer!
                  </p>
                  
                  <Alert className="mt-4">
                    <AlertTitle>Developer Note</AlertTitle>
                    <AlertDescription>
                      The current documentation is available in HTML format. For a more interactive experience,
                      you can download the OpenAPI specification and import it into tools like Postman or Swagger UI.
                    </AlertDescription>
                  </Alert>
                  
                  <Button 
                    variant="outline" 
                    className="mt-4"
                    onClick={() => handleDownload('openapi')}
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Download OpenAPI Spec
                  </Button>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>API Usage Guidelines</CardTitle>
            <CardDescription>
              Important information for using the Supertrack API effectively.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-semibold">Authentication</h3>
                <p className="text-muted-foreground">
                  All API endpoints require authentication using a Bearer token. 
                  You can generate an API token in your account settings.
                </p>
              </div>
              
              <div>
                <h3 className="text-lg font-semibold">Rate Limiting</h3>
                <p className="text-muted-foreground">
                  API requests are limited to 100 requests per minute per user.
                  If you exceed this limit, you'll receive a 429 Too Many Requests response.
                </p>
              </div>
              
              <div>
                <h3 className="text-lg font-semibold">Batch Requests</h3>
                <p className="text-muted-foreground">
                  To optimize performance and reduce network overhead, you can use the batch API 
                  endpoint to combine multiple operations into a single HTTP request.
                </p>
                <pre className="bg-muted p-4 rounded-md mt-2 overflow-x-auto">
                  <code>{`// Example batch request
POST /api/v1/batch
{
  "operations": [
    {
      "id": "getModels",
      "method": "get",
      "path": "/api/v1/models"
    },
    {
      "id": "createModel",
      "method": "post",
      "path": "/api/v1/models",
      "body": {
        "name": "New Model",
        "type": "classification"
      }
    }
  ]
}`}</code>
                </pre>
              </div>
              
              <div>
                <h3 className="text-lg font-semibold">Offline Support</h3>
                <p className="text-muted-foreground">
                  The Supertrack API client supports offline operations. When offline, 
                  write operations are queued and synchronized when connectivity is restored.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}