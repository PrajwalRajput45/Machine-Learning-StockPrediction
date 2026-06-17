import { createRoot } from 'react-dom/client';
import { ClerkProvider, useAuth } from '@clerk/clerk-react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { useApiClient } from './hooks/useApiClient';
import './index.css';
import App from './App.jsx';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 2, // 2 minutes default for most data
      gcTime: 1000 * 60 * 10,  // 10 minutes garbage collection
      retry: 1,
      refetchOnWindowFocus: false, // Don't refetch on tab switch
    },
  },
});

// Component that initializes API client with Clerk auth
function ApiClientInitializer() {
  useApiClient();
  return null;
}

function Main() {
  return (
    <ClerkProvider publishableKey={import.meta.env.VITE_CLERK_PUBLISHABLE_KEY}>
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <ApiClientInitializer />
            <App />
          </BrowserRouter>
        </QueryClientProvider>
      </ThemeProvider>
    </ClerkProvider>
  );
}

createRoot(document.getElementById('root')).render(<Main />);