import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth/next';
import { authOptions } from '@/lib/auth-options';
import { 
  generateApiDocumentation, 
  renderHtmlDocs,
  generateOpenApiSpec
} from '@/lib/api-docs-generator';

// Add additional documentation for API endpoints
const additionalDocs = {
  '/api/v1/models': {
    description: 'API endpoints for managing AI models',
    methods: ['GET', 'POST'],
    parameters: {
      query: {
        page: {
          type: 'integer',
          description: 'Page number for pagination',
          required: false,
          example: 1,
        },
        limit: {
          type: 'integer',
          description: 'Number of items per page',
          required: false,
          example: 10,
        },
        type: {
          type: 'string',
          description: 'Filter models by type',
          required: false,
          example: 'classification',
        },
      },
      body: {
        name: {
          type: 'string',
          description: 'Name of the model',
          required: true,
          example: 'Customer Churn Predictor',
        },
        type: {
          type: 'string',
          description: 'Type of the model',
          required: true,
          example: 'classification',
        },
        description: {
          type: 'string',
          description: 'Description of the model',
          required: false,
          example: 'Predicts customer churn based on behavioral data',
        },
        framework: {
          type: 'string',
          description: 'ML framework used',
          required: false,
          example: 'tensorflow',
        },
      },
    },
    responses: {
      '200': {
        description: 'List of models or newly created model',
        schema: {
          type: 'object',
          properties: {
            data: {
              type: 'array',
              items: {
                type: 'object',
                properties: {
                  id: { type: 'string' },
                  name: { type: 'string' },
                  type: { type: 'string' },
                  description: { type: 'string' },
                  framework: { type: 'string' },
                  version: { type: 'string' },
                  accuracy: { type: 'number' },
                  status: { type: 'string' },
                  lastTrained: { type: 'string', format: 'date-time' },
                  createdBy: { type: 'string' },
                  createdAt: { type: 'string', format: 'date-time' },
                  updatedAt: { type: 'string', format: 'date-time' },
                },
              },
            },
            meta: {
              type: 'object',
              properties: {
                total: { type: 'integer' },
                page: { type: 'integer' },
                limit: { type: 'integer' },
                pages: { type: 'integer' },
              },
            },
          },
        },
        example: {
          data: [
            {
              id: 'model-123',
              name: 'Customer Churn Predictor',
              type: 'classification',
              description: 'Predicts customer churn based on behavioral data',
              framework: 'tensorflow',
              version: '1.0.0',
              accuracy: 0.92,
              status: 'active',
              lastTrained: '2023-04-15T10:30:00Z',
              createdBy: 'user-456',
              createdAt: '2023-03-20T08:15:30Z',
              updatedAt: '2023-04-15T10:30:00Z',
            },
          ],
          meta: {
            total: 1,
            page: 1,
            limit: 10,
            pages: 1,
          },
        },
      },
      '400': {
        description: 'Bad request',
        example: {
          error: 'Validation Error',
          message: 'Name and type are required',
        },
      },
    },
  },
  
  '/api/v1/models/:id': {
    description: 'API endpoint for a specific model',
    methods: ['GET', 'PUT', 'DELETE'],
    parameters: {
      path: {
        id: {
          type: 'string',
          description: 'ID of the model',
          example: 'model-123',
        },
      },
      body: {
        name: {
          type: 'string',
          description: 'Name of the model',
          required: false,
          example: 'Updated Customer Churn Predictor',
        },
        description: {
          type: 'string',
          description: 'Description of the model',
          required: false,
          example: 'Updated description for the model',
        },
      },
    },
    responses: {
      '200': {
        description: 'Model details or update confirmation',
        example: {
          id: 'model-123',
          name: 'Updated Customer Churn Predictor',
          type: 'classification',
          description: 'Updated description for the model',
          framework: 'tensorflow',
          version: '1.0.0',
          accuracy: 0.92,
          status: 'active',
          lastTrained: '2023-04-15T10:30:00Z',
          createdBy: 'user-456',
          createdAt: '2023-03-20T08:15:30Z',
          updatedAt: '2023-05-10T14:20:15Z',
        },
      },
      '404': {
        description: 'Model not found',
        example: {
          error: 'Not Found',
          message: 'Model with ID model-123 not found',
        },
      },
    },
  },
  
  '/api/v1/batch': {
    description: 'Batch API endpoint for processing multiple requests',
    methods: ['POST'],
    parameters: {
      body: {
        operations: {
          type: 'array',
          description: 'Array of operations to perform',
          required: true,
          example: [
            {
              id: 'op1',
              method: 'get',
              path: '/api/v1/models',
            },
            {
              id: 'op2',
              method: 'post',
              path: '/api/v1/models',
              body: {
                name: 'New Model',
                type: 'classification',
              },
            },
          ],
        },
      },
    },
    responses: {
      '200': {
        description: 'Results of all operations',
        example: [
          {
            id: 'op1',
            status: 200,
            statusText: 'OK',
            data: {
              data: [
                {
                  id: 'model-123',
                  name: 'Customer Churn Predictor',
                  type: 'classification',
                },
              ],
              meta: {
                total: 1,
                page: 1,
                limit: 10,
                pages: 1,
              },
            },
          },
          {
            id: 'op2',
            status: 201,
            statusText: 'Created',
            data: {
              id: 'model-456',
              name: 'New Model',
              type: 'classification',
            },
          },
        ],
      },
      '400': {
        description: 'Bad request',
        example: {
          error: 'Validation Error',
          message: 'Invalid operation format',
          invalidOperations: [
            {
              id: 'op2',
              error: 'Missing required field: method',
            },
          ],
        },
      },
    },
  },
};

// Generate API documentation
export async function GET(request: Request) {
  // Check auth - only allow authenticated users to access documentation
  const session = await getServerSession(authOptions);
  
  if (!session?.user) {
    return NextResponse.json(
      { error: 'Unauthorized', message: 'You must be logged in to access API documentation' },
      { status: 401 }
    );
  }
  
  // Parse query parameters
  const { searchParams } = new URL(request.url);
  const format = searchParams.get('format') || 'html';
  
  // Generate the API documentation
  const apiDocs = generateApiDocumentation(additionalDocs);
  
  // Return the documentation in the requested format
  switch (format) {
    case 'json':
      return NextResponse.json(apiDocs);
    
    case 'openapi':
      const openApiSpec = generateOpenApiSpec(apiDocs, {
        title: 'Supertrack API',
        version: '1.0.0',
        description: 'API documentation for the Supertrack AI Platform',
      });
      return NextResponse.json(openApiSpec);
    
    case 'html':
    default:
      const htmlDocs = renderHtmlDocs(apiDocs, 'Supertrack API Documentation');
      return new NextResponse(htmlDocs, {
        headers: {
          'Content-Type': 'text/html; charset=utf-8',
        },
      });
  }
}