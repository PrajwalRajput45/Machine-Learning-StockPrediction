import { useAuth } from '@clerk/clerk-react';
import { useCallback } from 'react';

export function useUserId() {
  const { isLoaded, userId } = useAuth();
  return isLoaded ? userId : null;
}

export function useClerkUser() {
  const { isLoaded, userId, user, isSignedIn } = useAuth();
  return {
    isLoaded,
    isSignedIn,
    userId,
    user,
  };
}