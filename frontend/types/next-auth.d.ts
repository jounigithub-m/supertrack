import NextAuth, { DefaultSession } from 'next-auth';
import { JWT } from 'next-auth/jwt';

declare module 'next-auth' {
  /**
   * Extend the built-in session types
   */
  interface Session {
    accessToken: string;
    idToken: string;
    user: {
      roles: string[];
    } & DefaultSession['user'];
  }

  /**
   * Extend the built-in user types
   */
  interface User {
    roles?: string[];
  }
}

declare module 'next-auth/jwt' {
  /**
   * Extend the built-in JWT types
   */
  interface JWT {
    accessToken?: string;
    idToken?: string;
    roles?: string[];
  }
}