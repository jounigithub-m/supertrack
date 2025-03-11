import { ApiError } from '@/lib/api-client';
import { handleError } from '@/lib/error-handler';
import offlineStorage from './offline-storage';
import batchService from './batch-service';
import { useToast } from '@/components/ui/use-toast';

/**
 * Types for offline operations
 */
export interface OfflineOperation {
  method: string;
  url: string;
  body?: any;
  headers?: Record<string, string>;
  priority?: number;
}

export interface OfflineOptions {
  // Whether to enable offline support
  enabled?: boolean;
  
  // Sync interval in milliseconds (how often to check for connection and sync)
  syncInterval?: number;
  
  // Maximum number of sync attempts for an operation
  maxSyncAttempts?: number;
  
  // Backoff strategy for retries (linear, exponential)
  backoffStrategy?: 'linear' | 'exponential';
  
  // Base delay for backoff in milliseconds
  baseBackoffDelay?: number;
}

/**
 * Service for managing offline operations
 * This handles queueing operations when offline and syncing when back online
 */
class OfflineService {
  private isOnline = typeof navigator !== 'undefined' ? navigator.onLine : true;
  private isSyncing = false;
  private syncIntervalId: ReturnType<typeof setInterval> | null = null;
  
  private options: Required<OfflineOptions> = {
    enabled: true,
    syncInterval: 30000, // 30 seconds
    maxSyncAttempts: 5,
    backoffStrategy: 'exponential',
    baseBackoffDelay: 1000, // 1 second
  };
  
  constructor(options?: OfflineOptions) {
    if (options) {
      this.options = { ...this.options, ...options };
    }
    
    // Initialize event listeners for online/offline events
    if (typeof window !== 'undefined') {
      window.addEventListener('online', this.handleOnline);
      window.addEventListener('offline', this.handleOffline);
      
      // Start the sync interval
      this.startSyncInterval();
    }
  }
  
  /**
   * Get the current online status
   */
  public getIsOnline(): boolean {
    return this.isOnline;
  }
  
  /**
   * Handler for online event
   */
  private handleOnline = (): void => {
    if (!this.isOnline) {
      this.isOnline = true;
      
      // Notify user
      if (typeof window !== 'undefined') {
        const { toast } = useToast();
        toast({
          title: 'You are online',
          description: 'Your changes will be synchronized.',
          variant: 'default',
        });
      }
      
      // Start syncing pending operations
      this.syncPendingOperations();
    }
  };
  
  /**
   * Handler for offline event
   */
  private handleOffline = (): void => {
    this.isOnline = false;
    
    // Notify user
    if (typeof window !== 'undefined') {
      const { toast } = useToast();
      toast({
        title: 'You are offline',
        description: 'Changes will be saved and synchronized when you reconnect.',
        variant: 'warning',
      });
    }
  };
  
  /**
   * Start the sync interval
   */
  private startSyncInterval(): void {
    if (this.syncIntervalId) {
      clearInterval(this.syncIntervalId);
    }
    
    this.syncIntervalId = setInterval(() => {
      // Check if we're online and sync if needed
      if (this.isOnline && !this.isSyncing) {
        this.syncPendingOperations();
      }
      
      // Clear expired cache
      offlineStorage?.clearExpiredCache();
    }, this.options.syncInterval);
  }
  
  /**
   * Stop the sync interval
   */
  private stopSyncInterval(): void {
    if (this.syncIntervalId) {
      clearInterval(this.syncIntervalId);
      this.syncIntervalId = null;
    }
  }
  
  /**
   * Queue an operation for offline processing
   */
  public async queueOperation(operation: OfflineOperation): Promise<string | null> {
    if (!this.options.enabled || !offlineStorage) {
      return null;
    }
    
    try {
      const id = await offlineStorage.addPendingOperation({
        method: operation.method,
        url: operation.url,
        body: operation.body,
        headers: operation.headers,
        priority: operation.priority || 1,
      });
      
      return id;
    } catch (error) {
      console.error('Failed to queue offline operation:', error);
      return null;
    }
  }
  
  /**
   * Sync pending operations
   */
  public async syncPendingOperations(): Promise<void> {
    if (!this.options.enabled || !this.isOnline || this.isSyncing || !offlineStorage) {
      return;
    }
    
    this.isSyncing = true;
    
    try {
      // Get pending operations sorted by priority (highest first)
      const pendingOperations = await offlineStorage.getPendingOperationsByPriority();
      
      if (pendingOperations.length === 0) {
        this.isSyncing = false;
        return;
      }
      
      console.log(`Syncing ${pendingOperations.length} pending operations`);
      
      // Process operations in batches where possible
      const batchableOperations = pendingOperations.filter(op => {
        // Determine which operations can be batched
        // For example, GET requests or operations with specific requirements might not be batchable
        return op.method.toLowerCase() !== 'get' && op.retryCount < this.options.maxSyncAttempts;
      });
      
      const nonBatchableOperations = pendingOperations.filter(op => {
        return op.method.toLowerCase() === 'get' || op.retryCount >= this.options.maxSyncAttempts;
      });
      
      // First, process operations in a batch if possible
      if (batchableOperations.length > 0) {
        const batchResults = await this.processBatch(batchableOperations);
        
        // Handle batch results
        for (const result of batchResults) {
          const operation = batchableOperations.find(op => op.id === result.id);
          if (!operation) continue;
          
          if (result.status >= 200 && result.status < 300) {
            // Success - remove from pending operations
            await offlineStorage.removePendingOperation(operation.id);
          } else {
            // Error - update retry count
            operation.retryCount += 1;
            operation.lastRetry = Date.now();
            
            if (operation.retryCount >= this.options.maxSyncAttempts) {
              // Too many retries - remove from pending operations
              await offlineStorage.removePendingOperation(operation.id);
              
              // Log error
              const error = result.error || { message: 'Max retry attempts reached' };
              handleError(error as ApiError, { 
                context: 'offlineSync', 
                operation: operation 
              });
            } else {
              // Update operation for later retry
              await offlineStorage.updatePendingOperation(operation);
            }
          }
        }
      }
      
      // Process non-batchable operations individually
      for (const operation of nonBatchableOperations) {
        try {
          // Process the operation
          const response = await fetch(operation.url, {
            method: operation.method,
            headers: {
              'Content-Type': 'application/json',
              ...operation.headers,
            },
            body: operation.method.toLowerCase() !== 'get' && operation.body 
              ? JSON.stringify(operation.body)
              : undefined,
          });
          
          if (response.ok) {
            // Success - remove from pending operations
            await offlineStorage.removePendingOperation(operation.id);
          } else {
            // Error - update retry count
            operation.retryCount += 1;
            operation.lastRetry = Date.now();
            
            if (operation.retryCount >= this.options.maxSyncAttempts) {
              // Too many retries - remove from pending operations
              await offlineStorage.removePendingOperation(operation.id);
              
              // Log error
              const errorData = await response.json().catch(() => ({ message: 'Error processing operation' }));
              handleError({ 
                message: errorData.message || 'Operation failed',
                status: response.status,
                code: `HTTP_${response.status}`,
                originalError: errorData,
              }, { 
                context: 'offlineSync', 
                operation: operation 
              });
            } else {
              // Update operation for later retry
              await offlineStorage.updatePendingOperation(operation);
            }
          }
        } catch (error) {
          // Network or other error
          operation.retryCount += 1;
          operation.lastRetry = Date.now();
          
          if (operation.retryCount >= this.options.maxSyncAttempts) {
            // Too many retries - remove from pending operations
            await offlineStorage.removePendingOperation(operation.id);
            
            // Log error
            handleError(error as ApiError, { 
              context: 'offlineSync', 
              operation: operation 
            });
          } else {
            // Update operation for later retry
            await offlineStorage.updatePendingOperation(operation);
          }
        }
      }
      
      // Check if there are still pending operations
      const remainingOperations = await offlineStorage.getPendingOperations();
      if (remainingOperations.length > 0) {
        console.log(`${remainingOperations.length} operations still pending`);
      } else {
        console.log('All pending operations synced');
      }
    } catch (error) {
      console.error('Error syncing pending operations:', error);
    } finally {
      this.isSyncing = false;
    }
  }
  
  /**
   * Process a batch of operations
   */
  private async processBatch(operations: any[]): Promise<any[]> {
    // Use the batch service to send operations in a batch
    const batchOperations = operations.map(op => ({
      id: op.id,
      method: op.method.toLowerCase(),
      path: op.url,
      body: op.method.toLowerCase() !== 'get' ? op.body : undefined,
    }));
    
    // Clear batch service queue
    batchService.clearQueue();
    
    // Add operations to batch
    batchOperations.forEach(op => {
      batchService.add({
        method: op.method as any,
        path: op.path,
        body: op.body,
      });
    });
    
    // Send the batch
    return await batchService.send();
  }
  
  /**
   * Calculate backoff delay based on retry count
   */
  private calculateBackoffDelay(retryCount: number): number {
    if (this.options.backoffStrategy === 'linear') {
      return this.options.baseBackoffDelay * retryCount;
    } else {
      // Exponential backoff with jitter
      const exponentialDelay = this.options.baseBackoffDelay * Math.pow(2, retryCount);
      // Add some random jitter (0-20% of the delay)
      const jitter = Math.random() * 0.2 * exponentialDelay;
      return exponentialDelay + jitter;
    }
  }
  
  /**
   * Ensure offline data is available
   * This preloads essential data for offline use
   */
  public async ensureOfflineData(): Promise<void> {
    if (!this.options.enabled || !offlineStorage) {
      return;
    }
    
    // Only sync data when online
    if (!this.isOnline) {
      return;
    }
    
    try {
      // TODO: Implement actual data fetching from API endpoints
      // For now, this is a placeholder
      
      // For example, fetch models
      // const models = await apiService.getModels();
      // await offlineStorage.storeModels(models);
      
      // Fetch projects
      // const projects = await apiService.getProjects();
      // await offlineStorage.storeProjects(projects);
      
      // Fetch data sources
      // const dataSources = await apiService.getDataSources();
      // await offlineStorage.storeDataSources(dataSources);
      
      console.log('Offline data synchronized');
    } catch (error) {
      console.error('Error ensuring offline data:', error);
    }
  }
  
  /**
   * Clean up event listeners
   */
  public destroy(): void {
    if (typeof window !== 'undefined') {
      window.removeEventListener('online', this.handleOnline);
      window.removeEventListener('offline', this.handleOffline);
    }
    
    this.stopSyncInterval();
  }
}

// Create a singleton instance
const offlineService = typeof window !== 'undefined' ? new OfflineService() : null;

export default offlineService;