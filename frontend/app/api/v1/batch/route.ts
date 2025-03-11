import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/app/api/auth/[...nextauth]/route';

interface BatchOperation {
  id: string;
  method: string;
  path: string;
  body?: any;
}

interface BatchOperationResult {
  id: string;
  status: number;
  statusText: string;
  data?: any;
  error?: {
    message: string;
    code?: string;
    status?: number;
  };
}

/**
 * Process a batch of API operations in a single request
 * This endpoint accepts multiple operations and processes them sequentially
 */
export async function POST(req: NextRequest) {
  try {
    // Check authentication
    const session = await getServerSession(authOptions);
    if (!session) {
      return NextResponse.json(
        { error: 'Authentication required' },
        { status: 401 }
      );
    }
    
    // Parse the request body
    const body = await req.json();
    
    if (!body.operations || !Array.isArray(body.operations)) {
      return NextResponse.json(
        { error: 'Invalid request format. Expected array of operations.' },
        { status: 400 }
      );
    }
    
    const operations: BatchOperation[] = body.operations;
    
    // Validate operations
    const invalidOps = operations.filter(op => {
      return !op.id || !op.method || !op.path || 
        !['get', 'post', 'put', 'patch', 'delete'].includes(op.method.toLowerCase());
    });
    
    if (invalidOps.length > 0) {
      return NextResponse.json(
        { 
          error: 'Invalid operations found', 
          invalidOperations: invalidOps.map(op => op.id) 
        },
        { status: 400 }
      );
    }
    
    // Process operations sequentially
    const results: BatchOperationResult[] = [];
    
    for (const operation of operations) {
      try {
        // Normalize path (remove /api prefix if present)
        let path = operation.path;
        if (path.startsWith('/api/')) {
          path = path.substring(4);
        }
        if (!path.startsWith('/')) {
          path = '/' + path;
        }
        
        // Construct the URL
        const url = new URL(path, process.env.NEXT_PUBLIC_API_URL || req.nextUrl.origin);
        
        // Build the request options
        const options: RequestInit = {
          method: operation.method.toUpperCase(),
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${session.accessToken}`,
          },
        };
        
        // Add body for non-GET requests
        if (operation.method.toLowerCase() !== 'get' && operation.body) {
          options.body = JSON.stringify(operation.body);
        }
        
        // Execute the request
        const response = await fetch(url.toString(), options);
        
        // Parse the response
        let data: any = null;
        let error: any = null;
        
        try {
          if (response.status !== 204) { // No content
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
              data = await response.json();
            } else {
              data = await response.text();
            }
          }
        } catch (e) {
          console.error('Error parsing response:', e);
          error = {
            message: 'Error parsing response',
            code: 'PARSE_ERROR',
          };
        }
        
        // If the response is not successful, treat data as error
        if (!response.ok && data && !error) {
          error = {
            message: data.message || data.error || 'Operation failed',
            code: data.code || `HTTP_${response.status}`,
            status: response.status,
          };
          data = null;
        }
        
        // Add the result
        results.push({
          id: operation.id,
          status: response.status,
          statusText: response.statusText,
          data: data,
          error: error,
        });
      } catch (error) {
        // Handle request error
        console.error(`Error processing operation ${operation.id}:`, error);
        
        results.push({
          id: operation.id,
          status: 500,
          statusText: 'Internal Server Error',
          error: {
            message: error instanceof Error ? error.message : 'Unknown error',
            code: 'BATCH_PROCESSING_ERROR',
          },
        });
      }
    }
    
    return NextResponse.json(results);
  } catch (error) {
    console.error('Batch processing error:', error);
    
    return NextResponse.json(
      { error: 'Error processing batch request' },
      { status: 500 }
    );
  }
}