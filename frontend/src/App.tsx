import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './context/AuthContext';
import { HouseholdProvider } from './context/HouseholdContext';
import { AppLayout } from './components/layout/AppLayout';

// Lazy-loaded routes for optimal bundle code-splitting
const DashboardPage = React.lazy(() =>
  import('./pages/dashboard/DashboardPage').then((m) => ({ default: m.DashboardPage }))
);
const ReceiptsListPage = React.lazy(() =>
  import('./pages/receipts/ReceiptsListPage').then((m) => ({ default: m.ReceiptsListPage }))
);
const ProductsPage = React.lazy(() =>
  import('./pages/products/ProductsPage').then((m) => ({ default: m.ProductsPage }))
);
const ShoppingListPage = React.lazy(() =>
  import('./pages/shopping/ShoppingListPage').then((m) => ({ default: m.ShoppingListPage }))
);
const ImportsPage = React.lazy(() =>
  import('./pages/imports/ImportsPage').then((m) => ({ default: m.ImportsPage }))
);
const GoogleCallbackPage = React.lazy(() =>
  import('./pages/imports/GoogleCallbackPage').then((m) => ({ default: m.GoogleCallbackPage }))
);
const SettingsPage = React.lazy(() =>
  import('./pages/settings/SettingsPage').then((m) => ({ default: m.SettingsPage }))
);
const AdminDashboardPage = React.lazy(() =>
  import('./pages/admin/AdminDashboardPage').then((m) => ({ default: m.AdminDashboardPage }))
);
const LoginPage = React.lazy(() =>
  import('./pages/auth/LoginPage').then((m) => ({ default: m.LoginPage }))
);
const RegisterPage = React.lazy(() =>
  import('./pages/auth/RegisterPage').then((m) => ({ default: m.RegisterPage }))
);
const SetupWizardPage = React.lazy(() =>
  import('./pages/auth/SetupWizardPage').then((m) => ({ default: m.SetupWizardPage }))
);

const PageLoader: React.FC = () => (
  <div className="min-h-screen flex items-center justify-center bg-slate-50">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
  </div>
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

// Guard component that redirects to /setup if initial setup is pending, or /login if not authenticated
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading, needsSetup } = useAuth();

  if (isLoading) {
    return <PageLoader />;
  }

  if (needsSetup) {
    return <Navigate to="/setup" replace />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

// Route for Login/Register: redirects to /setup if setup is pending, or / if already authenticated
const PublicAuthRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { needsSetup, isAuthenticated } = useAuth();
  if (needsSetup) {
    return <Navigate to="/setup" replace />;
  }
  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
};

// Route for First-Run Web Setup Wizard
const SetupRoute: React.FC = () => {
  const { needsSetup, isAuthenticated } = useAuth();
  if (!needsSetup) {
    return <Navigate to={isAuthenticated ? '/' : '/login'} replace />;
  }
  return <SetupWizardPage />;
};

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <HouseholdProvider>
          <BrowserRouter>
            <Suspense fallback={<PageLoader />}>
              <Routes>
                {/* First-Run Web Setup Wizard */}
                <Route path="/setup" element={<SetupRoute />} />

                {/* Public Auth Routes */}
                <Route
                  path="/login"
                  element={
                    <PublicAuthRoute>
                      <LoginPage />
                    </PublicAuthRoute>
                  }
                />
                <Route
                  path="/register"
                  element={
                    <PublicAuthRoute>
                      <RegisterPage />
                    </PublicAuthRoute>
                  }
                />
                <Route path="/integrations/google/callback" element={<GoogleCallbackPage />} />

                {/* Protected App Routes */}
                <Route
                  path="/"
                  element={
                    <ProtectedRoute>
                      <AppLayout />
                    </ProtectedRoute>
                  }
                >
                  <Route index element={<DashboardPage />} />
                  <Route path="receipts" element={<ReceiptsListPage />} />
                  <Route path="products" element={<ProductsPage />} />
                  <Route path="shopping-list" element={<ShoppingListPage />} />
                  <Route path="imports" element={<ImportsPage />} />
                  <Route path="settings" element={<SettingsPage />} />
                  <Route path="admin" element={<AdminDashboardPage />} />
                </Route>

                {/* Catch-all redirect */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </BrowserRouter>
        </HouseholdProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
};

export default App;
