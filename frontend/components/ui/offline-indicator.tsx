'use client';

import React, { useState, useEffect } from 'react';
import { WifiOff, Wifi } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import offlineService from '@/services/offline-service';

interface OfflineIndicatorProps {
  className?: string;
}

/**
 * Component that displays the current network status and pending operations
 */
export function OfflineIndicator({ className = '' }: OfflineIndicatorProps) {
  const [isOnline, setIsOnline] = useState<boolean>(true);
  const [pendingCount, setPendingCount] = useState<number>(0);
  
  useEffect(() => {
    // Update initial status
    if (typeof navigator !== 'undefined') {
      setIsOnline(navigator.onLine);
    }
    
    // Function to update status from online/offline events
    const updateOnlineStatus = () => {
      if (typeof navigator !== 'undefined') {
        setIsOnline(navigator.onLine);
      }
    };
    
    // Add event listeners
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    
    // Function to update pending operations count
    const updatePendingCount = async () => {
      try {
        const storage = await import('@/services/offline-storage').then(mod => mod.default);
        if (storage) {
          const operations = await storage.getPendingOperations();
          setPendingCount(operations.length);
        }
      } catch (error) {
        console.error('Error fetching pending operations count:', error);
      }
    };
    
    // Update pending count initially and periodically
    updatePendingCount();
    const intervalId = setInterval(updatePendingCount, 5000); // Update every 5 seconds
    
    // Clean up
    return () => {
      window.removeEventListener('online', updateOnlineStatus);
      window.removeEventListener('offline', updateOnlineStatus);
      clearInterval(intervalId);
    };
  }, []);
  
  // Trigger manual sync
  const handleSync = async () => {
    if (isOnline && offlineService) {
      try {
        await offlineService.syncPendingOperations();
        // Update pending count after sync
        const storage = await import('@/services/offline-storage').then(mod => mod.default);
        if (storage) {
          const operations = await storage.getPendingOperations();
          setPendingCount(operations.length);
        }
      } catch (error) {
        console.error('Error syncing pending operations:', error);
      }
    }
  };
  
  // If online and no pending operations, don't show anything
  if (isOnline && pendingCount === 0) {
    return null;
  }
  
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            onClick={handleSync}
            className={`flex items-center space-x-1 rounded-md px-2 py-1 text-sm 
            ${isOnline 
              ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/20 dark:text-amber-300' 
              : 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-300'
            } ${className}`}
            disabled={!isOnline}
          >
            {isOnline ? (
              <>
                <Wifi className="h-4 w-4" />
                <span>{pendingCount} pending</span>
              </>
            ) : (
              <>
                <WifiOff className="h-4 w-4" />
                <span>Offline</span>
                {pendingCount > 0 && <span>({pendingCount})</span>}
              </>
            )}
          </button>
        </TooltipTrigger>
        <TooltipContent>
          {isOnline ? (
            <>
              <p>You have {pendingCount} operations waiting to sync</p>
              <p className="text-xs text-muted-foreground">Click to sync now</p>
            </>
          ) : (
            <>
              <p>You are currently offline</p>
              {pendingCount > 0 && <p>There are {pendingCount} operations pending</p>}
              <p className="text-xs text-muted-foreground">Changes will sync when you reconnect</p>
            </>
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export default OfflineIndicator;