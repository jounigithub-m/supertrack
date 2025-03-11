'use client';

import React from 'react';
import { usePathname } from 'next/navigation';

import Sidebar from '@/components/layout/sidebar';
import Navbar from '@/components/layout/navbar';
import { MainNav } from '@/components/layout/main-nav';
import { navigationItems } from '@/components/layout/navigation-config';
import { OfflineIndicator } from '@/components/ui/offline-indicator';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const pathname = usePathname();
  
  // Filter navigation items based on user roles and permissions
  // In a real app, we'd get these from the auth context
  const userRoles = ['user'];
  const userHasAdminAccess = false;
  
  const filteredNavItems = navigationItems.filter(item => {
    // Skip items that require admin access if user doesn't have it
    if (item.requiresAdmin && !userHasAdminAccess) return false;
    
    // Check if role-based access is needed and if user has required role
    if (item.roles && item.roles.length > 0) {
      return item.roles.some(role => userRoles.includes(role));
    }
    
    return true;
  });

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar for navigation */}
      <Sidebar navigationItems={filteredNavItems} />
      
      {/* Main content area */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Top navbar */}
        <Navbar>
          <MainNav items={filteredNavItems} currentPath={pathname} />
          <div className="ml-auto flex items-center space-x-4">
            <OfflineIndicator />
            {/* Other navbar items would go here */}
          </div>
        </Navbar>
        
        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}