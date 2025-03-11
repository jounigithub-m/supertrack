import { openDB, IDBPDatabase, DBSchema } from 'idb';

/**
 * Schema definition for our IndexedDB database
 */
interface SupertrackDBSchema extends DBSchema {
  // Store for pending API operations (offline queue)
  pendingOperations: {
    key: string;
    value: {
      id: string;
      timestamp: number;
      method: string;
      url: string;
      body?: any;
      headers?: Record<string, string>;
      priority: number; // Higher number = higher priority
      retryCount: number;
      lastRetry?: number;
    };
    indexes: {
      'by-timestamp': number;
      'by-priority': number;
    };
  };
  
  // Cache for API responses
  responseCache: {
    key: string; // URL + query params as key
    value: {
      data: any;
      timestamp: number;
      expires: number; // Timestamp when cache expires
      headers?: Record<string, string>;
    };
    indexes: {
      'by-expiry': number;
    };
  };
  
  // Store for offline data (models, projects, data sources)
  models: {
    key: string; // model ID
    value: any;
    indexes: {
      'by-status': string;
      'by-updated': number;
    };
  };
  
  projects: {
    key: string; // project ID
    value: any;
    indexes: {
      'by-status': string;
      'by-updated': number;
    };
  };
  
  dataSources: {
    key: string; // data source ID
    value: any;
    indexes: {
      'by-status': string;
      'by-updated': number;
    };
  };
  
  // Store for user data and settings
  userData: {
    key: string;
    value: any;
  };
}

/**
 * Service for offline storage using IndexedDB
 * This provides a simplified interface to work with IndexedDB for offline support
 */
class OfflineStorage {
  private dbName = 'supertrack-offline-db';
  private dbVersion = 1;
  private db: IDBPDatabase<SupertrackDBSchema> | null = null;
  
  /**
   * Initialize the database
   */
  async init(): Promise<void> {
    if (typeof window === 'undefined') {
      console.warn('OfflineStorage: IndexedDB is not available in server environment');
      return;
    }
    
    try {
      this.db = await openDB<SupertrackDBSchema>(this.dbName, this.dbVersion, {
        upgrade: (db, oldVersion, newVersion, transaction) => {
          // Create stores if they don't exist
          
          // Pending operations store
          if (!db.objectStoreNames.contains('pendingOperations')) {
            const pendingStore = db.createObjectStore('pendingOperations', { keyPath: 'id' });
            pendingStore.createIndex('by-timestamp', 'timestamp');
            pendingStore.createIndex('by-priority', 'priority');
          }
          
          // Response cache store
          if (!db.objectStoreNames.contains('responseCache')) {
            const cacheStore = db.createObjectStore('responseCache', { keyPath: 'key' });
            cacheStore.createIndex('by-expiry', 'expires');
          }
          
          // Data stores
          if (!db.objectStoreNames.contains('models')) {
            const modelsStore = db.createObjectStore('models', { keyPath: 'id' });
            modelsStore.createIndex('by-status', 'status');
            modelsStore.createIndex('by-updated', 'updatedAt');
          }
          
          if (!db.objectStoreNames.contains('projects')) {
            const projectsStore = db.createObjectStore('projects', { keyPath: 'id' });
            projectsStore.createIndex('by-status', 'status');
            projectsStore.createIndex('by-updated', 'updatedAt');
          }
          
          if (!db.objectStoreNames.contains('dataSources')) {
            const dataSourcesStore = db.createObjectStore('dataSources', { keyPath: 'id' });
            dataSourcesStore.createIndex('by-status', 'status');
            dataSourcesStore.createIndex('by-updated', 'updatedAt');
          }
          
          // User data store
          if (!db.objectStoreNames.contains('userData')) {
            db.createObjectStore('userData', { keyPath: 'key' });
          }
        },
      });
      
      console.log('OfflineStorage: Database initialized');
    } catch (error) {
      console.error('OfflineStorage: Failed to initialize database', error);
      throw error;
    }
  }
  
  /**
   * Get the database instance, initializing if necessary
   */
  async getDb(): Promise<IDBPDatabase<SupertrackDBSchema>> {
    if (!this.db) {
      await this.init();
    }
    
    if (!this.db) {
      throw new Error('OfflineStorage: Database is not available');
    }
    
    return this.db;
  }
  
  /**
   * Add a pending operation to the queue
   */
  async addPendingOperation(operation: Omit<SupertrackDBSchema['pendingOperations']['value'], 'id' | 'timestamp' | 'retryCount'>): Promise<string> {
    const db = await this.getDb();
    const id = crypto.randomUUID();
    
    const pendingOp: SupertrackDBSchema['pendingOperations']['value'] = {
      ...operation,
      id,
      timestamp: Date.now(),
      retryCount: 0,
      priority: operation.priority || 1,
    };
    
    await db.add('pendingOperations', pendingOp);
    return id;
  }
  
  /**
   * Get all pending operations
   */
  async getPendingOperations(): Promise<SupertrackDBSchema['pendingOperations']['value'][]> {
    const db = await this.getDb();
    return db.getAllFromIndex('pendingOperations', 'by-timestamp');
  }
  
  /**
   * Get pending operations by priority
   */
  async getPendingOperationsByPriority(): Promise<SupertrackDBSchema['pendingOperations']['value'][]> {
    const db = await this.getDb();
    return db.getAllFromIndex('pendingOperations', 'by-priority');
  }
  
  /**
   * Remove a pending operation
   */
  async removePendingOperation(id: string): Promise<void> {
    const db = await this.getDb();
    await db.delete('pendingOperations', id);
  }
  
  /**
   * Update a pending operation
   */
  async updatePendingOperation(operation: SupertrackDBSchema['pendingOperations']['value']): Promise<void> {
    const db = await this.getDb();
    await db.put('pendingOperations', operation);
  }
  
  /**
   * Add a response to the cache
   */
  async cacheResponse(key: string, data: any, ttlSeconds: number = 300, headers?: Record<string, string>): Promise<void> {
    const db = await this.getDb();
    const now = Date.now();
    
    await db.put('responseCache', {
      key,
      data,
      timestamp: now,
      expires: now + (ttlSeconds * 1000),
      headers,
    });
  }
  
  /**
   * Get a cached response
   */
  async getCachedResponse(key: string): Promise<any | null> {
    const db = await this.getDb();
    try {
      const cachedResponse = await db.get('responseCache', key);
      
      if (!cachedResponse) {
        return null;
      }
      
      // Check if expired
      if (cachedResponse.expires < Date.now()) {
        // Expired, remove from cache
        await db.delete('responseCache', key);
        return null;
      }
      
      return cachedResponse.data;
    } catch (error) {
      console.error('OfflineStorage: Failed to get cached response', error);
      return null;
    }
  }
  
  /**
   * Remove a cached response
   */
  async removeCachedResponse(key: string): Promise<void> {
    const db = await this.getDb();
    await db.delete('responseCache', key);
  }
  
  /**
   * Clear expired cache entries
   */
  async clearExpiredCache(): Promise<void> {
    const db = await this.getDb();
    const now = Date.now();
    
    const expiredKeys = await db.getAllKeysFromIndex('responseCache', 'by-expiry', IDBKeyRange.upperBound(now));
    
    for (const key of expiredKeys) {
      await db.delete('responseCache', key);
    }
  }
  
  /**
   * Store models for offline access
   */
  async storeModels(models: any[]): Promise<void> {
    const db = await this.getDb();
    
    const tx = db.transaction('models', 'readwrite');
    for (const model of models) {
      await tx.store.put(model);
    }
    await tx.done;
  }
  
  /**
   * Get all models from offline storage
   */
  async getModels(): Promise<any[]> {
    const db = await this.getDb();
    return db.getAll('models');
  }
  
  /**
   * Store projects for offline access
   */
  async storeProjects(projects: any[]): Promise<void> {
    const db = await this.getDb();
    
    const tx = db.transaction('projects', 'readwrite');
    for (const project of projects) {
      await tx.store.put(project);
    }
    await tx.done;
  }
  
  /**
   * Get all projects from offline storage
   */
  async getProjects(): Promise<any[]> {
    const db = await this.getDb();
    return db.getAll('projects');
  }
  
  /**
   * Store data sources for offline access
   */
  async storeDataSources(dataSources: any[]): Promise<void> {
    const db = await this.getDb();
    
    const tx = db.transaction('dataSources', 'readwrite');
    for (const dataSource of dataSources) {
      await tx.store.put(dataSource);
    }
    await tx.done;
  }
  
  /**
   * Get all data sources from offline storage
   */
  async getDataSources(): Promise<any[]> {
    const db = await this.getDb();
    return db.getAll('dataSources');
  }
  
  /**
   * Store user data
   */
  async storeUserData(key: string, data: any): Promise<void> {
    const db = await this.getDb();
    await db.put('userData', { key, value: data });
  }
  
  /**
   * Get user data
   */
  async getUserData(key: string): Promise<any | null> {
    const db = await this.getDb();
    const data = await db.get('userData', key);
    return data ? data.value : null;
  }
  
  /**
   * Clear all data from the database
   */
  async clearAll(): Promise<void> {
    const db = await this.getDb();
    
    const tx = db.transaction([
      'pendingOperations',
      'responseCache',
      'models',
      'projects',
      'dataSources',
      'userData'
    ], 'readwrite');
    
    await Promise.all([
      tx.objectStore('pendingOperations').clear(),
      tx.objectStore('responseCache').clear(),
      tx.objectStore('models').clear(),
      tx.objectStore('projects').clear(),
      tx.objectStore('dataSources').clear(),
      tx.objectStore('userData').clear(),
    ]);
    
    await tx.done;
  }
}

// Create a singleton instance
const offlineStorage = typeof window !== 'undefined' ? new OfflineStorage() : null;

// Initialize the database when in browser environment
if (typeof window !== 'undefined') {
  // Initialize in the background
  offlineStorage?.init().catch(error => {
    console.error('Failed to initialize offline storage:', error);
  });
}

export default offlineStorage;