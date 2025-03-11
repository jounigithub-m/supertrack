'use client';

import { useState, useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { Header } from './header';
import { Sidebar } from './sidebar';
import { ProtectedRoute } from '@/components/auth/protected-route';
import { cn } from '@/lib/utils';

interface DashboardLayoutProps {
  children: React.ReactNode;
  requiredRoles?: string[];
}

export function DashboardLayout({
  children,
  requiredRoles = [],
}: DashboardLayoutProps) {
  const pathname = usePathname();
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);

  // Handle responsive layout
  useEffect(() => {
    const checkScreenSize = () => {
      setIsMobile(window.innerWidth < 1024);
      setIsSidebarOpen(window.innerWidth >= 1024);
    };

    checkScreenSize();
    window.addEventListener('resize', checkScreenSize);

    return () => {
      window.removeEventListener('resize', checkScreenSize);
    };
  }, []);

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  return (
    <ProtectedRoute requiredRoles={requiredRoles}>
      <div className="flex h-screen flex-col bg-background">
        <Header
          isSidebarOpen={isSidebarOpen}
          toggleSidebar={toggleSidebar}
          isMobile={isMobile}
        />
        <div className="flex flex-1 overflow-hidden">
          <Sidebar
            isOpen={isSidebarOpen}
            isMobile={isMobile}
            closeSidebar={() => setIsSidebarOpen(false)}
            currentPath={pathname}
          />
          <main
            className={cn(
              'flex-1 overflow-auto p-4 transition-all duration-300 md:p-6 lg:p-8',
              isSidebarOpen && !isMobile ? 'lg:ml-[280px]' : ''
            )}
          >
            {children}
          </main>
        </div>
      </div>
    </ProtectedRoute>
  );
}