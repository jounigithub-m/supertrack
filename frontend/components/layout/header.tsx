'use client';

import Link from 'next/link';
import { Menu, Search, Bell, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { UserDropdown } from './user-dropdown';
import { useAuth } from '@/components/auth/auth-provider';
import { Input } from '@/components/ui/input';
import { useState } from 'react';

interface HeaderProps {
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  isMobile: boolean;
}

export function Header({ isSidebarOpen, toggleSidebar, isMobile }: HeaderProps) {
  const { user } = useAuth();
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  return (
    <header className="sticky top-0 z-10 flex h-16 items-center border-b bg-background px-4 shadow-sm">
      <div className="flex w-full items-center justify-between gap-4">
        {/* Left section with logo and menu */}
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            aria-label="Toggle navigation"
          >
            <Menu className="h-5 w-5" />
          </Button>
          
          <Link href="/dashboard" className="hidden items-center gap-2 md:flex">
            <span className="text-xl font-bold text-primary">
              Supertrack
            </span>
            <span className="rounded-md bg-primary/10 px-1.5 py-0.5 text-xs font-medium text-primary">
              AI
            </span>
          </Link>
        </div>

        {/* Center section with search */}
        <div className={`${isSearchOpen ? 'flex flex-1' : 'hidden md:flex'} max-w-xl flex-1`}>
          <div className="relative w-full">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search..."
              className="w-full pl-9"
            />
          </div>
        </div>

        {/* Mobile search toggle button */}
        {isMobile && !isSearchOpen && (
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setIsSearchOpen(true)}
          >
            <Search className="h-5 w-5" />
          </Button>
        )}

        {/* Right section with notifications and user */}
        <div className="flex items-center gap-2">
          {isSearchOpen && isMobile && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsSearchOpen(false)}
            >
              Cancel
            </Button>
          )}
          
          {!isSearchOpen && (
            <>
              <Button variant="ghost" size="icon" aria-label="Notifications">
                <Bell className="h-5 w-5" />
              </Button>
              <UserDropdown />
            </>
          )}
        </div>
      </div>
    </header>
  );
}