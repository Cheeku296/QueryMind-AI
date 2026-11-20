import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/useAuthStore';
import { AppShell } from './components/layout/AppShell';

// Pages
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { ForgotPassword } from './pages/ForgotPassword';
import { Dashboard } from './pages/Dashboard';
import { Assistant } from './pages/Assistant';
import { SQLWorkspace } from './pages/SQLWorkspace';
import { Connections } from './pages/Connections';
import { SchemaExplorer } from './pages/SchemaExplorer';
import { ERDiagramPage } from './pages/ERDiagramPage';
import { Analytics } from './pages/Analytics';
import { Reports } from './pages/Reports';
import { ReportDetail } from './pages/ReportDetail';
import { QueryHistory } from './pages/QueryHistory';
import { SavedQueries } from './pages/SavedQueries';
import { AgentMonitor } from './pages/AgentMonitor';
import { Glossary } from './pages/Glossary';
import { WorkspaceSettings } from './pages/WorkspaceSettings';
import { Settings } from './pages/Settings';
import { NotFound } from './pages/NotFound';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { token, isLoading } = useAuthStore();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center text-xs text-typography-muted">
        Loading QueryMind AI...
      </div>
    );
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  const { fetchUser } = useAuthStore();

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  return (
    <BrowserRouter>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />

        {/* Protected Application Routes */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="assistant" element={<Assistant />} />
          <Route path="workspace" element={<SQLWorkspace />} />
          <Route path="connections" element={<Connections />} />
          <Route path="schema" element={<SchemaExplorer />} />
          <Route path="er-diagram" element={<ERDiagramPage />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="reports" element={<Reports />} />
          <Route path="reports/:reportId" element={<ReportDetail />} />
          <Route path="history" element={<QueryHistory />} />
          <Route path="saved-queries" element={<SavedQueries />} />
          <Route path="agents" element={<AgentMonitor />} />
          <Route path="glossary" element={<Glossary />} />
          <Route path="workspace-settings" element={<WorkspaceSettings />} />
          <Route path="settings" element={<Settings />} />
        </Route>

        {/* 404 Route */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
};

