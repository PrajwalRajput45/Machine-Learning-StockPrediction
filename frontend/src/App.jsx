import { Routes, Route, Navigate } from 'react-router-dom';
import { RequireAuth, RedirectIfAuthed } from './components/AuthProtection';
import AuthPage from './components/AuthPage';
import DashboardLayout from './layouts/DashboardLayout';
import DashboardHome from './pages/DashboardHome';
import PredictionPage from './pages/PredictionPage';
import TradingPage from './pages/TradingPage';
import PortfolioPage from './pages/PortfolioPage';
import SIPsPage from './pages/SIPsPage';
import DisclaimerPage from './pages/DisclaimerPage';

function App() {
  return (
    <Routes>
      {/* Public Auth Routes - redirect if already logged in */}
      <Route
        path="/sign-in"
        element={
          <RedirectIfAuthed>
            <AuthPage type="sign-in" />
          </RedirectIfAuthed>
        }
      />
      <Route
        path="/sign-up"
        element={
          <RedirectIfAuthed>
            <AuthPage type="sign-up" />
          </RedirectIfAuthed>
        }
      />

      {/* Protected App Routes - require authentication */}
      <Route
        path="/app"
        element={
          <RequireAuth>
            <DashboardLayout />
          </RequireAuth>
        }
      >
        <Route index element={<DashboardHome />} />
        <Route path="dashboard" element={<DashboardHome />} />
        <Route path="predictions" element={<PredictionPage />} />
        <Route path="trading" element={<TradingPage />} />
        <Route path="portfolio" element={<PortfolioPage />} />
        <Route path="sips" element={<SIPsPage />} />
        <Route path="disclaimer" element={<DisclaimerPage />} />
      </Route>

      {/* Legacy route redirects - for backward compatibility */}
      <Route path="/" element={<Navigate to="/app/dashboard" replace />} />
      <Route path="/dashboard" element={<Navigate to="/app/dashboard" replace />} />
      <Route path="/predictions" element={<Navigate to="/app/predictions" replace />} />
      <Route path="/trading" element={<Navigate to="/app/trading" replace />} />
      <Route path="/portfolio" element={<Navigate to="/app/portfolio" replace />} />
      <Route path="/sips" element={<Navigate to="/app/sips" replace />} />

      {/* Catch-all redirect */}
      <Route path="*" element={<Navigate to="/app/dashboard" replace />} />
    </Routes>
  );
}

export default App;