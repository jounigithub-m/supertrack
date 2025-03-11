import api, { ApiError, RequestConfig } from '@/lib/api-client';
import { handleError } from '@/lib/error-handler';

/**
 * Types for batch operations
 */

// A single batch operation with method, path, and optional body
export interface BatchOperation<T = any> {
  id: string;
  method: 'get' | 'post' | 'put' | 'patch' | 'delete';
  path: string;
  body?: any;
  config?: RequestConfig;
  onSuccess?: (data: T) => void;
  onError?: (error: ApiError) => void;
}

// Response format for a batch operation
export interface BatchOperationResult<T = any> {
  id: string;
  status: number;
  statusText: string;
  data?: T;
  error?: ApiError;
}

// Options for the batch service
export interface BatchOptions {
  // Maximum time to wait before sending the batch (in ms)
  maxWaitTime?: number;
  
  // Maximum number of operations in a single batch
  maxBatchSize?: number;
  
  // Whether to automatically send batches when full or timing out
  autoSend?: boolean;
  
  // Whether to continue processing remaining operations if some fail
  continueOnError?: boolean;
}

/**
 * Service for batching multiple API requests into a single HTTP request.
 * This helps reduce network overhead and improve performance for multiple related operations.
 */
export class BatchService {
  private queue: BatchOperation[] = [];
  private timeoutId: ReturnType<typeof setTimeout> | null = null;
  private isSending = false;
  
  private options: Required<BatchOptions> = {
    maxWaitTime: 50, // 50ms default wait time
    maxBatchSize: 10, // 10 operations per batch
    autoSend: true,
    continueOnError: true,
  };
  
  constructor(options?: BatchOptions) {
    if (options) {
      this.options = { ...this.options, ...options };
    }
  }
  
  /**
   * Add an operation to the batch queue
   */
  public add<T = any>(operation: Omit<BatchOperation<T>, 'id'>): string {
    const id = this.generateId();
    const fullOperation: BatchOperation<T> = {
      ...operation,
      id,
    };
    
    this.queue.push(fullOperation);
    
    // Start timeout if autoSend is enabled and there's no active timeout
    if (this.options.autoSend && !this.timeoutId && !this.isSending) {
      this.startTimeout();
    }
    
    // Send immediately if we've reached the max batch size
    if (this.options.autoSend && this.queue.length >= this.options.maxBatchSize && !this.isSending) {
      this.clearTimeout();
      this.send();
    }
    
    return id;
  }
  
  /**
   * Send the current batch of operations
   */
  public async send(): Promise<BatchOperationResult[]> {
    if (this.queue.length === 0 || this.isSending) {
      return [];
    }
    
    this.clearTimeout();
    this.isSending = true;
    
    // Take operations from the queue
    const operations = [...this.queue];
    this.queue = [];
    
    try {
      // If there's only one operation, send it directly
      if (operations.length === 1) {
        const op = operations[0];
        try {
          const response = await api[op.method](op.path, op.method === 'get' ? undefined : op.body, op.config);
          
          const result: BatchOperationResult = {
            id: op.id,
            status: response.status,
            statusText: response.statusText,
            data: response.data,
          };
          
          if (op.onSuccess) {
            op.onSuccess(response.data);
          }
          
          this.isSending = false;
          return [result];
        } catch (error) {
          const apiError = error as ApiError;
          
          if (op.onError) {
            op.onError(apiError);
          } else {
            handleError(apiError, { context: 'batchOperation', operation: op });
          }
          
          const result: BatchOperationResult = {
            id: op.id,
            status: apiError.status || 500,
            statusText: apiError.message,
            error: apiError,
          };
          
          this.isSending = false;
          return [result];
        }
      }
      
      // For multiple operations, send them as a batch
      const batchOperations = operations.map(op => ({
        id: op.id,
        method: op.method,
        path: op.path,
        body: op.method === 'get' ? undefined : op.body,
      }));
      
      // Send the batch request
      const { data } = await api.post<BatchOperationResult[]>(
        '/api/v1/batch',
        { operations: batchOperations },
        { retry: true, retryCount: 3 }
      );
      
      // Process the results
      data.forEach(result => {
        const operation = operations.find(op => op.id === result.id);
        if (!operation) return;
        
        if (result.error) {
          if (operation.onError) {
            operation.onError(result.error);
          } else {
            handleError(result.error, { context: 'batchOperation', operation });
          }
        } else if (operation.onSuccess) {
          operation.onSuccess(result.data);
        }
      });
      
      this.isSending = false;
      
      // If we have more operations in the queue, start the timeout again
      if (this.options.autoSend && this.queue.length > 0) {
        this.startTimeout();
      }
      
      return data;
    } catch (error) {
      // Handle batch request failure
      const apiError = error as ApiError;
      handleError(apiError, { context: 'batchRequest' });
      
      // If the entire batch failed, call onError for each operation
      operations.forEach(op => {
        if (op.onError) {
          op.onError(apiError);
        }
      });
      
      this.isSending = false;
      
      // If we have more operations in the queue, start the timeout again
      if (this.options.autoSend && this.queue.length > 0) {
        this.startTimeout();
      }
      
      // Return failure for all operations
      return operations.map(op => ({
        id: op.id,
        status: apiError.status || 500,
        statusText: apiError.message,
        error: apiError,
      }));
    }
  }
  
  /**
   * Start the timeout for auto-sending the batch
   */
  private startTimeout(): void {
    this.clearTimeout();
    this.timeoutId = setTimeout(() => {
      this.timeoutId = null;
      if (this.queue.length > 0 && !this.isSending) {
        this.send();
      }
    }, this.options.maxWaitTime);
  }
  
  /**
   * Clear the timeout
   */
  private clearTimeout(): void {
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }
  }
  
  /**
   * Generate a unique ID for the operation
   */
  private generateId(): string {
    return Math.random().toString(36).substring(2, 15) + 
           Math.random().toString(36).substring(2, 15);
  }
  
  /**
   * Get the current queue length
   */
  public getQueueLength(): number {
    return this.queue.length;
  }
  
  /**
   * Clear the queue without sending
   */
  public clearQueue(): void {
    this.clearTimeout();
    this.queue = [];
  }
}

// Create a default instance with default options
const batchService = new BatchService();

export default batchService;