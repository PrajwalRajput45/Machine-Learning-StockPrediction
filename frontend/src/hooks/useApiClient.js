import { useEffect } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { setClerkUserId, setClerkToken, clearClerkToken } from '../services/apiClient';

/**
 * Hook that syncs Clerk authentication state with the API client.
 * Call this once at the app root level to ensure all API requests
 * include the authenticated user's ID.
 */
export function useApiClient() {
  const { isLoaded, isSignedIn, userId, getToken } = useAuth();

  useEffect(() => {
    if (!isLoaded) return;

    if (isSignedIn && userId) {
      // Set the Clerk user ID for user-specific API requests
      setClerkUserId(userId);

      // Optionally get and set the Clerk session token for JWT validation
      // Uncomment if backend needs to validate Clerk tokens
      // getToken().then(token => {
      //   if (token) setClerkToken(token);
      // });
    } else {
      // Clear auth state when user signs out
      clearClerkToken();
    }
  }, [isLoaded, isSignedIn, userId, getToken]);

  return { isLoaded, isSignedIn, userId };
}