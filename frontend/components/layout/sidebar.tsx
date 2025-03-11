'use client';

import Link from 'next/link';
import { useEffect } from 'react';
import { cn } from '@/lib/utils';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { navigationItems } from './navigation-config';

interface SidebarProps {
  isOpen: boolean;
  isMobile: boolean;
  closeSidebar: () => void;
  currentPath: string;
}

export function Sidebar({ isOpen, isMobile, closeSidebar, currentPath }: SidebarProps) {
  // Close sidebar on route change for mobile
  useEffect(() => {
    if (isMobile) {
      closeSidebar();
    }
  }, [currentPath, isMobile, closeSidebar]);

  // Handle clicks outside sidebar on mobile
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (isMobile && isOpen) {
        const sidebar = document.getElementById('sidebar');
        if (sidebar && !sidebar.contains(e.target as Node)) {
          closeSidebar();
        }
      }
    };

    document.addEventListener('mousedown', handleOutsideClick);
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
    };
  }, [isMobile, isOpen, closeSidebar]);

  if (!isOpen) {
    return null;
  }

  return (
    <aside
      id="sidebar"
      className={cn(
        'fixed inset-y-0 left-0 z-20 flex w-[280px] flex-col border-r bg-background pt-16 transition-transform duration-300',
        isMobile ? 'shadow-xl' : 'lg:translate-x-0',
        isOpen ? 'translate-x-0' : '-translate-x-full'
      )}
    >
      {isMobile && (
        <Button
          variant="ghost"
          size="icon"
          className="absolute right-4 top-4"
          onClick={closeSidebar}
        >
          <X className="h-5 w-5" />
        </Button>
      )}

      <div className="flex-1 overflow-auto py-4">
        <nav className="space-y-1 px-2">
          {navigationItems.map((group) => (
            <div key={group.title} className="py-2">
              <h3 className="px-3 pb-1 pt-3 text-xs font-medium uppercase text-muted-foreground">
                {group.title}
              </h3>
              <div className="space-y-1">
                {group.items.map((item) => {
                  const isActive = currentPath === item.href;
                  return (
                    <Link key={item.name} href={item.href}>
                      <div
                        className={cn(
                          'group flex items-center rounded-md px-3 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground',
                          isActive
                            ? 'bg-accent text-accent-foreground'
                            : 'text-foreground/70'
                        )}
                      >
                        {item.icon && (
                          <item.icon
                            className={cn(
                              'mr-3 h-5 w-5',
                              isActive
                                ? 'text-accent-foreground'
                                : 'text-muted-foreground group-hover:text-accent-foreground'
                            )}
                          />
                        )}
                        {item.name}
                      </div>
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </div>

      <div className="mt-auto border-t p-4">
        <div className="rounded-md bg-accent/50 px-3 py-4">
          <h4 className="mb-1 text-sm font-medium">Need help?</h4>
          <p className="mb-3 text-xs text-muted-foreground">
            Check out our documentation or contact support.
          </p>
          <Button variant="outline" size="sm" className="w-full">
            View Documentation
          </Button>
        </div>
      </div>
    </aside>
  );
}