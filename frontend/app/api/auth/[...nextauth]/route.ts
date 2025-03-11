import NextAuth from 'next-auth';
import AzureADB2CProvider from 'next-auth/providers/azure-ad-b2c';

// For more information on each option, visit:
// https://next-auth.js.org/configuration/options
const handler = NextAuth({
  providers: [
    AzureADB2CProvider({
      tenantId: process.env.AZURE_AD_B2C_TENANT_NAME,
      clientId: process.env.AZURE_AD_B2C_CLIENT_ID || '',
      clientSecret: process.env.AZURE_AD_B2C_CLIENT_SECRET || '',
      primaryUserFlow: process.env.AZURE_AD_B2C_PRIMARY_USER_FLOW || 'signupsignin',
      authorization: { params: { scope: 'offline_access openid' } },
    }),
  ],
  callbacks: {
    async jwt({ token, account, profile }) {
      // Persist the OAuth access_token and or the user id to the token right after signin
      if (account) {
        token.accessToken = account.access_token;
        token.idToken = account.id_token;
        if (profile) {
          token.roles = (profile as any).roles || [];
          token.name = profile.name;
          token.email = profile.email;
        }
      }
      return token;
    },
    async session({ session, token }) {
      // Send properties to the client, like an access_token and user id from a provider.
      session.accessToken = token.accessToken as string;
      session.idToken = token.idToken as string;
      session.user.roles = (token.roles as string[]) || [];
      
      return session;
    },
  },
  session: {
    strategy: 'jwt',
    maxAge: 24 * 60 * 60, // 24 hours
  },
  pages: {
    signIn: '/auth/signin',
    signOut: '/auth/signout',
    error: '/auth/error',
  },
});

export { handler as GET, handler as POST };