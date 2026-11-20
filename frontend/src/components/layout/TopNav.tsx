import React, { useEffect, useState } from 'react';
import { Database, Plus, Sparkles, Activity, CheckCircle2, AlertCircle } from 'lucide-react';
import { useConnectionStore } from '../../store/useConnectionStore';
import { apiRequest } from '../../api/client';
import { Link } from 'react-router-dom';

export const TopNav: React.FC = () => {
  const { connections, activeConnectionId, setActiveConnection, fetchConnections } = useConnectionStore();
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    fetchConnections();
    apiRequest('/health')
      .then(res => setHealth(res))
      .catch(() => {});
  }, [fetchConnections]);

  const activeConn = connections.find(c => c.id === activeConnectionId);
  const geminiConfigured = health?.services?.llm_provider?.is_configured;
  const geminiModel = health?.services?.llm_provider?.model || 'gemini-2.5-flash';

  return (
    <header className="h-16 bg-background-secondary/90 backdrop-blur border-b border-border fixed top-0 right-0 left-64 z-20 px-6 flex items-center justify-between">
      {/* Left: Active Database selector */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-background-elevated border border-border">
          <Database className="w-4 h-4 text-accent-primary" />
          <span className="text-xs text-typography-secondary font-medium">Active Database:</span>
          {connections.length > 0 ? (
            <select
              value={activeConnectionId || ''}
              onChange={e => setActiveConnection(e.target.value)}
              className="bg-transparent text-xs text-typography-primary font-semibold focus:outline-none cursor-pointer"
            >
              {connections.map(c => (
                <option key={c.id} value={c.id} className="bg-background-card">
                  {c.name} ({c.database_name})
                </option>
              ))}
            </select>
          ) : (
            <span className="text-xs text-typography-muted italic">No databases connected</span>
          )}
          {activeConn && (
            <span
              className={`w-2 h-2 rounded-full ${
                activeConn.status === 'connected' ? 'bg-status-success animate-pulse' : 'bg-status-error'
              }`}
              title={`Status: ${activeConn.status}`}
            />
          )}
        </div>

        <Link
          to="/connections"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-background-elevated hover:bg-background-card border border-border text-xs text-typography-primary font-medium transition-colors"
        >
          <Plus className="w-3.5 h-3.5 text-accent-primary" />
          <span>Connect DB</span>
        </Link>
      </div>

      {/* Right: AI & System Health Badges */}
      <div className="flex items-center gap-3">
        {/* Gemini Provider Badge */}
        <Link
          to="/settings"
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${
            geminiConfigured
              ? 'bg-accent-primary/10 border-accent-primary/30 text-accent-primary hover:bg-accent-primary/20'
              : 'bg-status-warning/10 border-status-warning/30 text-status-warning hover:bg-status-warning/20'
          }`}
          title={geminiConfigured ? `Google Gemini (${geminiModel}) active` : 'Configure GEMINI_API_KEY'}
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Google Gemini</span>
          <span className="text-[10px] px-1.5 py-0.2 rounded bg-background/50 font-mono">
            {geminiConfigured ? 'Ready' : 'Setup Key'}
          </span>
        </Link>

        {/* System Health */}
        <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-background-elevated border border-border text-xs text-typography-secondary">
          <Activity className="w-3.5 h-3.5 text-status-success" />
          <span className="font-mono text-[11px]">System Online</span>
        </div>
      </div>
    </header>
  );
};

