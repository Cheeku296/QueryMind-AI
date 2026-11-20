import React, { useState } from 'react';
import {
  Database,
  Plus,
  RefreshCw,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Clock,
  Layers,
  Key,
} from 'lucide-react';
import { useConnectionStore } from '../store/useConnectionStore';
import { apiRequest } from '../api/client';

export const Connections: React.FC = () => {
  const { connections, activeConnectionId, setActiveConnection, fetchConnections } = useConnectionStore();
  const [showAddModal, setShowAddModal] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    name: 'Production PostgreSQL',
    database_type: 'postgresql',
    host: 'localhost',
    port: 5432,
    database_name: 'querymind_demo',
    username: 'postgres',
    password: 'postgrespassword',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);

  const handleTestParams = async () => {
    setIsSubmitting(true);
    setTestResult(null);
    try {
      const res = await apiRequest('/connections/test', {
        method: 'POST',
        body: JSON.stringify(formData),
      });
      setTestResult({ success: true, message: res.message });
    } catch (e: any) {
      setTestResult({ success: false, message: e.message });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateConnection = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await apiRequest('/connections', {
        method: 'POST',
        body: JSON.stringify(formData),
      });
      setShowAddModal(false);
      fetchConnections();
      setActionMessage('Connection created and schema indexed in Qdrant successfully.');
      setTimeout(() => setActionMessage(null), 3500);
    } catch (e: any) {
      setTestResult({ success: false, message: e.message });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSyncSchema = async (id: string) => {
    setSyncingId(id);
    try {
      const res = await apiRequest(`/connections/${id}/sync`, { method: 'POST' });
      setActionMessage(res.message);
      setTimeout(() => setActionMessage(null), 3500);
    } catch (e: any) {
      setActionMessage(`Sync failed: ${e.message}`);
    } finally {
      setSyncingId(null);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to remove this connection and its vector index?')) return;
    try {
      await apiRequest(`/connections/${id}`, { method: 'DELETE' });
      fetchConnections();
    } catch {}
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Database className="w-5 h-5 text-accent-primary" />
            Database Connections
          </h1>
          <p className="text-xs text-typography-secondary mt-0.5">
            Manage credentials, test live connectivity, and synchronize schemas with Qdrant vector retrieval.
          </p>
        </div>

        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-accent-primary hover:bg-accent-hover text-white text-xs font-semibold shadow-md shadow-accent-primary/20 transition-all"
        >
          <Plus className="w-4 h-4" />
          <span>Add Connection</span>
        </button>
      </div>

      {actionMessage && (
        <div className="p-3.5 rounded-xl bg-accent-primary/10 border border-accent-primary/30 text-xs text-accent-primary flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* Connections List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {connections.map(conn => (
          <div
            key={conn.id}
            className={`p-5 rounded-2xl bg-background-card border transition-all flex flex-col justify-between ${
              activeConnectionId === conn.id ? 'border-accent-primary shadow-lg shadow-accent-primary/10' : 'border-border'
            }`}
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-background-elevated text-typography-secondary border border-border">
                  {conn.database_type}
                </span>
                <span
                  className={`inline-flex items-center gap-1.5 text-xs font-semibold ${
                    conn.status === 'connected' ? 'text-status-success' : 'text-status-error'
                  }`}
                >
                  <span
                    className={`w-2 h-2 rounded-full ${
                      conn.status === 'connected' ? 'bg-status-success' : 'bg-status-error'
                    }`}
                  />
                  {conn.status}
                </span>
              </div>

              <h3 className="text-base font-bold text-white tracking-tight">{conn.name}</h3>
              <div className="mt-2 text-xs font-mono text-typography-secondary space-y-1">
                <div>
                  <span className="text-typography-muted">Database:</span> {conn.database_name}
                </div>
                <div>
                  <span className="text-typography-muted">Endpoint:</span> {conn.host}:{conn.port}
                </div>
                <div>
                  <span className="text-typography-muted">User:</span> {conn.username}
                </div>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-border flex items-center justify-between">
              <button
                onClick={() => setActiveConnection(conn.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  activeConnectionId === conn.id
                    ? 'bg-accent-primary/20 text-accent-primary border border-accent-primary/30'
                    : 'bg-background-elevated hover:bg-background-secondary text-typography-primary border border-border'
                }`}
              >
                {activeConnectionId === conn.id ? 'Active Connection' : 'Set as Active'}
              </button>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleSyncSchema(conn.id)}
                  disabled={syncingId === conn.id}
                  title="Force re-sync schema & index into Qdrant"
                  className="p-1.5 rounded-lg bg-background-elevated hover:bg-background-card border border-border text-typography-secondary hover:text-white"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${syncingId === conn.id ? 'animate-spin text-accent-primary' : ''}`} />
                </button>
                <button
                  onClick={() => handleDelete(conn.id)}
                  title="Delete connection"
                  className="p-1.5 rounded-lg bg-background-elevated hover:bg-background-card border border-border text-typography-muted hover:text-status-error"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Add Connection Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg bg-background-card border border-border rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Database className="w-5 h-5 text-accent-primary" />
                Connect New Database
              </h2>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-typography-muted hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateConnection} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-typography-secondary font-medium mb-1">Connection Name</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={e => setFormData({ ...formData, name: e.target.value })}
                  className="w-full bg-background-elevated border border-border rounded-lg px-3 py-2 text-white focus:outline-none focus:border-accent-primary"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-typography-secondary font-medium mb-1">Database Type</label>
                  <select
                    value={formData.database_type}
                    onChange={e => {
                      const newType = e.target.value;
                      setFormData({
                        ...formData,
                        database_type: newType,
                        port: newType === 'mysql' ? (formData.port === 5432 ? 3306 : formData.port) : (formData.port === 3306 ? 5432 : formData.port)
                      });
                    }}
                    className="w-full bg-background-elevated border border-border rounded-lg px-3 py-2 text-white focus:outline-none"
                  >
                    <option value="postgresql">PostgreSQL</option>
                    <option value="mysql">MySQL</option>
                  </select>
                </div>
                <div>
                  <label className="block text-typography-secondary font-medium mb-1">Database Name</label>
                  <input
                    type="text"
                    required
                    value={formData.database_name}
                    onChange={e => setFormData({ ...formData, database_name: e.target.value })}
                    className="w-full bg-background-elevated border border-border rounded-lg px-3 py-2 text-white focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className="block text-typography-secondary font-medium mb-1">Host</label>
                  <input
                    type="text"
                    required
                    value={formData.host}
                    onChange={e => setFormData({ ...formData, host: e.target.value })}
                    className="w-full bg-background-elevated border border-border rounded-lg px-3 py-2 text-white focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-typography-secondary font-medium mb-1">Port</label>
                  <input
                    type="number"
                    required
                    value={formData.port}
                    onChange={e => setFormData({ ...formData, port: parseInt(e.target.value) || 5432 })}
                    className="w-full bg-background-elevated border border-border rounded-lg px-3 py-2 text-white focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-typography-secondary font-medium mb-1">Username</label>
                  <input
                    type="text"
                    required
                    value={formData.username}
                    onChange={e => setFormData({ ...formData, username: e.target.value })}
                    className="w-full bg-background-elevated border border-border rounded-lg px-3 py-2 text-white focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-typography-secondary font-medium mb-1">Password</label>
                  <input
                    type="password"
                    required
                    value={formData.password}
                    onChange={e => setFormData({ ...formData, password: e.target.value })}
                    className="w-full bg-background-elevated border border-border rounded-lg px-3 py-2 text-white focus:outline-none"
                  />
                </div>
              </div>

              {testResult && (
                <div
                  className={`p-3 rounded-lg border text-xs flex items-center gap-2 ${
                    testResult.success
                      ? 'bg-status-success/10 border-status-success/30 text-status-success'
                      : 'bg-status-error/10 border-status-error/30 text-status-error'
                  }`}
                >
                  {testResult.success ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
                  <span>{testResult.message}</span>
                </div>
              )}

              <div className="pt-3 border-t border-border flex items-center justify-between">
                <button
                  type="button"
                  onClick={handleTestParams}
                  disabled={isSubmitting}
                  className="px-3 py-2 rounded-lg bg-background-elevated hover:bg-background-secondary border border-border text-typography-primary font-medium"
                >
                  Test Connection
                </button>

                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setShowAddModal(false)}
                    className="px-3 py-2 rounded-lg bg-transparent text-typography-secondary hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="px-4 py-2 rounded-lg bg-accent-primary hover:bg-accent-hover text-white font-semibold shadow-md shadow-accent-primary/20"
                  >
                    Save & Index Schema
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

