import { Session } from 'next-auth';
import { getSession, signOut } from 'next-auth/react';

// Token interface
interface TokenInfo {
  accessToken: string;
  expiresAt: number; // timestamp in milliseconds
  refreshToken?: string;
}

// Cache for token information
let tokenCache: TokenInfo | null = null;

// Token expiry buffer (5 minutes in ms)
const TOKEN_EXPIRY_BUFFER = 5 * 60 * 1000;

/**
 * Check if a token is expired
 */
function isTokenExpired(expiresAt: number): boolean {
  // Token is expired if the current time + buffer is greater than expiry time
  return Date.now() + TOKEN_EXPIRY_BUFFER > expiresAt;
}

/**
 * Parse expiry from JWT token
 * Note: This is a simple implementation; in production, consider using a library like jwt-decode
 */
function getTokenExpiry(token: string): number {
  try {
    // JWT tokens are in format: header.payload.signature
    const payload = token.split('.')[1];
    // Base64 decode
    const decodedPayload = JSON.parse(atob(payload));
    // Get expiry time (exp is in seconds, convert to ms)
    return decodedPayload.exp * 1000;
  } catch (error) {
    console.error('Error parsing token expiry:', error);
    // Return a default expiry (30 minutes from now)
    return Date.now() + 30 * 60 * 1000;
  }
}

/**
 * Extract token information from the session
 */
function extractTokenFromSession(session: Session | null): TokenInfo | null {
  if (!session || !session.accessToken) {
    return null;
  }

  return {
    accessToken: session.accessToken as string,
    expiresAt: getTokenExpiry(session.accessToken as string),
    refreshToken: session.refreshToken as string | undefined,
  };
}

/**
 * Get a valid access token
 * - First tries the cache
 * - Then checks the session
 * - If token is expired, attempts to refresh it
 * - If refresh fails, forces sign out
 */
export async function getAccessToken(forceRefresh = false): Promise<string | null> {
  // Check if we have a valid token in cache
  if (!forceRefresh && tokenCache && !isTokenExpired(tokenCache.expiresAt)) {
    return tokenCache.accessToken;
  }

  // Get the session
  const session = await getSession();
  const tokenInfo = extractTokenFromSession(session);

  // If no token found, return null
  if (!tokenInfo) {
    return null;
  }

  // If token is still valid, cache and return it
  if (!isTokenExpired(tokenInfo.expiresAt)) {
    tokenCache = tokenInfo;
    return tokenInfo.accessToken;
  }

  // If we have a refresh token, try to refresh
  if (tokenInfo.refreshToken) {
    try {
      // In a real implementation, you would call your refresh token endpoint here
      // For now, we'll just simulate this by forcing a sign out
      // const newTokenInfo = await refreshToken(tokenInfo.refreshToken);
      // tokenCache = newTokenInfo;
      // return newTokenInfo.accessToken;
      
      // Since we're not implementing actual token refresh, just sign out
      await signOut({ redirect: false });
      return null;
    } catch (error) {
      console.error('Error refreshing token:', error);
      // Clear token cache
      tokenCache = null;
      
      // Sign out the user
      await signOut({ redirect: false });
      return null;
    }
  }

  // No refresh token, sign out
  await signOut({ redirect: false });
  return null;
}

/**
 * Store a new token in the cache
 * This would be called after successful login or token refresh
 */
export function storeToken(tokenInfo: TokenInfo): void {
  tokenCache = tokenInfo;
}

/**
 * Clear the token cache
 * This would be called after logout
 */
export function clearToken(): void {
  tokenCache = null;
}

/**
 * Get the token expiry as a Date object
 */
export function getTokenExpiration(): Date | null {
  if (!tokenCache) {
    return null;
  }
  
  return new Date(tokenCache.expiresAt);
}

/**
 * Check if the user is authenticated with a valid token
 */
export async function isAuthenticated(): Promise<boolean> {
  const token = await getAccessToken();
  return !!token;
}

export default {
  getAccessToken,
  storeToken,
  clearToken,
  getTokenExpiration,
  isAuthenticated,
};