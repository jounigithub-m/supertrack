import { useState, useEffect, useCallback } from 'react';
import { useSession, signIn, signOut } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { toast } from '@/components/ui/use-toast';

export interface UseAuthProps {
  /**
   * The path to redirect to after successful login
   */
  redirectTo?: string;
  /**
   * The path to redirect to after logout
   */
  redirectAfterLogout?: string;
}

/**
 * Custom hook for handling authentication in the application
 */
export const useAuth = ({
  redirectTo = '/dashboard',
  redirectAfterLogout = '/signin',
}: UseAuthProps = {}) => {
  const { data: session, status } = useSession();
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const router = useRouter();

  // Check if the user is authenticated
  const isAuthenticated = status === 'authenticated' && !!session;
  
  // Determine if the session is still loading
  const isSessionLoading = status === 'loading';

  // Handle login with email and password
  const login = useCallback(
    async (email: string, password: string) => {
      setIsLoading(true);
      
      try {
        const result = await signIn('credentials', {
          email,
          password,
          redirect: false,
        });

        if (result?.error) {
          toast({
            title: 'Login failed',
            description: result.error,
            variant: 'destructive',
          });
          return false;
        }

        // Successful login
        toast({
          title: 'Welcome back!',
          description: 'You have successfully logged in.',
        });
        
        router.push(redirectTo);
        return true;
      } catch (error) {
        console.error('Login error:', error);
        toast({
          title: 'Login failed',
          description: 'An unexpected error occurred. Please try again.',
          variant: 'destructive',
        });
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    [router, redirectTo]
  );

  // Handle third-party authentication (Google, Microsoft, etc.)
  const loginWithProvider = useCallback(
    async (provider: string) => {
      setIsLoading(true);
      
      try {
        await signIn(provider, {
          callbackUrl: redirectTo,
        });
        
        return true;
      } catch (error) {
        console.error(`${provider} login error:`, error);
        toast({
          title: 'Login failed',
          description: `Could not sign in with ${provider}. Please try again.`,
          variant: 'destructive',
        });
        setIsLoading(false);
        return false;
      }
    },
    [redirectTo]
  );

  // Handle logout
  const logout = useCallback(async () => {
    setIsLoading(true);
    
    try {
      await signOut({ redirect: false });
      
      // Clear any auth-related data from local storage
      localStorage.removeItem('authState');
      
      toast({
        title: 'Logged out',
        description: 'You have been successfully logged out.',
      });
      
      router.push(redirectAfterLogout);
    } catch (error) {
      console.error('Logout error:', error);
      toast({
        title: 'Logout failed',
        description: 'An error occurred during logout. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  }, [router, redirectAfterLogout]);

  // Check if the user has a specific role
  const hasRole = useCallback(
    (role: string): boolean => {
      if (!session || !session.user?.roles) {
        return false;
      }
      
      return session.user.roles.includes(role);
    },
    [session]
  );

  // Effect to update loading state based on session status
  useEffect(() => {
    if (status !== 'loading') {
      setIsLoading(false);
    }
  }, [status]);

  return {
    isAuthenticated,
    isLoading: isLoading || isSessionLoading,
    user: session?.user,
    session,
    login,
    loginWithProvider,
    logout,
    hasRole,
  };
};

export default useAuth;