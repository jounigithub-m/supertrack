'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { useSession, signIn, signOut } from 'next-auth/react';
import { useRouter, usePathname } from 'next/navigation';

type AuthContextType = {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: any;
  roles: string[];
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
  hasRole: (role: string) => boolean;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { data: session, status } = useSession();
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    if (status === 'loading') {
      setIsLoading(true);
      return;
    }

    setIsLoading(false);
    setIsAuthenticated(status === 'authenticated');

    // Redirect to login if not authenticated and not on a public page
    if (status === 'unauthenticated' && !isPublicRoute(pathname)) {
      router.push('/auth/signin');
    }
  }, [status, pathname, router]);

  const isPublicRoute = (path: string) => {
    const publicRoutes = ['/auth/signin', '/auth/signup', '/auth/error'];
    return publicRoutes.includes(path);
  };

  const handleSignIn = async () => {
    await signIn('azure-ad-b2c');
  };

  const handleSignOut = async () => {
    await signOut({ callbackUrl: '/auth/signin' });
  };

  const hasRole = (role: string) => {
    if (!session?.user.roles) return false;
    return session.user.roles.includes(role);
  };

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        isLoading,
        user: session?.user,
        roles: session?.user.roles || [],
        signIn: handleSignIn,
        signOut: handleSignOut,
        hasRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}