import React, { useEffect, useState } from 'react';
import {
  Cpu,
  Activity,
  CheckCircle2,
  AlertCircle,
  Clock,
  RefreshCw,
  Terminal,
  Layers,
  Sparkles,
  Search,
} from 'lucide-react';
import { apiRequest } from '../api/client';

export const AgentMonitor: React.FC = () => {
  const [runs, setRuns] = useState<any[]>([]);
  const [selectedRun, setSelectedRun] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadRuns = async () => {
    setIsLoading(true);
    try {
      const data = await apiRequest('/agents/runs');
      setRuns(data || []);
      if (data && data.length > 0 && !selectedRun) {
        setSelectedRun(data[0]);
      }
    } catch {}
    setIsLoading(false);
  };

  useEffect(() => {
    loadRuns();
  }, []);

  return (
    <div className="flex h-[calc(100vh-6.5rem)] gap-5 overflow-hidden">
      {/* Runs List Sidebar */}
      <div className="w-80 bg-background-card border border-border rounded-2xl flex flex-col overflow-hidden shrink-0">
        <div className="p-4 border-b border-border flex items-center justify-between">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Cpu className="w-4 h-4 text-accent-primary" />
            Agent Runs ({runs.length})
          </h2>
          <button
            onClick={loadRuns}
            disabled={isLoading}
            className="p-1.5 rounded-lg hover:bg-background-elevated text-typography-secondary hover:text-white"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-accent-primary' : ''}`} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {runs.length === 0 ? (
            <div className="p-6 text-center text-xs text-typography-muted">
              No LangGraph agent executions recorded yet.
            </div>
          ) : (
            runs.map(r => (
              <div
                key={r.id}
                onClick={() => setSelectedRun(r)}
                className={`p-3 rounded-xl cursor-pointer transition-colors border ${
                  selectedRun?.id === r.id
                    ? 'bg-background-elevated border-accent-primary text-white shadow-sm'
                    : 'bg-transparent border-transparent text-typography-secondary hover:bg-background-elevated/40'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono text-[11px] font-semibold text-white truncate max-w-[150px]">
                    {r.run_id}
                  </span>
                  <span
                    className={`text-[10px] px-1.5 py-0.2 rounded font-medium ${
                      r.status === 'completed'
                        ? 'bg-status-success/10 text-status-success'
                        : r.status === 'failed'
                        ? 'bg-status-error/10 text-status-error'
                        : 'bg-accent-primary/10 text-accent-primary animate-pulse'
                    }`}
                  >
                    {r.status}
                  </span>
                </div>
                <p className="text-[11px] text-typography-secondary truncate mt-0.5">
                  {r.metadata?.question || 'Natural language query execution'}
                </p>
                <div className="mt-1 text-[10px] text-typography-muted flex items-center justify-between">
                  <span>Node: {r.current_node}</span>
                  <span>{new Date(r.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Selected Run Inspection Panel */}
      <div className="flex-1 bg-background-card border border-border rounded-2xl flex flex-col overflow-hidden shadow-2xl p-6 overflow-y-auto space-y-6">
        {!selectedRun ? (
          <div className="h-full flex items-center justify-center text-xs text-typography-muted">
            Select a run to inspect its multi-agent workflow timeline.
          </div>
        ) : (
          <>
            {/* Run Header */}
            <div className="border-b border-border pb-4 flex items-center justify-between">
              <div>
                <span className="text-[10px] font-mono uppercase text-accent-primary font-semibold">
                  Graph Execution ID
                </span>
                <h2 className="text-lg font-bold text-white font-mono mt-0.5">{selectedRun.run_id}</h2>
                <span className="text-xs text-typography-secondary">
                  Started: {new Date(selectedRun.started_at).toLocaleString()}
                </span>
              </div>
              <span
                className={`px-3 py-1 rounded-full text-xs font-semibold uppercase font-mono ${
                  selectedRun.status === 'completed'
                    ? 'bg-status-success/15 text-status-success border border-status-success/30'
                    : 'bg-status-error/15 text-status-error border border-status-error/30'
                }`}
              >
                {selectedRun.status}
              </span>
            </div>

            {/* User Prompt / Context */}
            {selectedRun.metadata?.question && (
              <div className="p-4 rounded-xl bg-background-elevated border border-border space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-typography-muted">
                  Input User Prompt
                </span>
                <p className="text-xs text-white font-medium">{selectedRun.metadata.question}</p>
              </div>
            )}

            {/* Generated SQL if present */}
            {selectedRun.metadata?.sql && (
              <div className="space-y-1.5">
                <span className="text-[10px] font-bold uppercase tracking-wider text-typography-muted">
                  Executed SQL Output
                </span>
                <pre className="p-3 rounded-xl bg-[#0F1117] border border-border text-[11px] font-mono text-[#E2E8F0] overflow-x-auto">
                  <code>{selectedRun.metadata.sql}</code>
                </pre>
              </div>
            )}

            {/* Architecture Node Workflow Pipeline Diagram */}
            <div className="space-y-3">
              <span className="text-xs font-bold uppercase tracking-wider text-accent-primary">
                Multi-Agent Pipeline Graph
              </span>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="p-3 rounded-xl bg-background-elevated border border-border space-y-1">
                  <div className="text-[10px] uppercase font-mono text-typography-muted">Node 1</div>
                  <div className="text-xs font-bold text-white flex items-center gap-1.5">
                    <Activity className="w-3.5 h-3.5 text-accent-primary" />
                    Supervisor Agent
                  </div>
                  <p className="text-[11px] text-typography-secondary">Intent classification & router</p>
                </div>

                <div className="p-3 rounded-xl bg-background-elevated border border-border space-y-1">
                  <div className="text-[10px] uppercase font-mono text-typography-muted">Node 2</div>
                  <div className="text-xs font-bold text-white flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-accent-secondary" />
                    Schema Retrieval (RAG)
                  </div>
                  <p className="text-[11px] text-typography-secondary">Qdrant vector search & context builder</p>
                </div>

                <div className="p-3 rounded-xl bg-background-elevated border border-border space-y-1">
                  <div className="text-[10px] uppercase font-mono text-typography-muted">Node 3</div>
                  <div className="text-xs font-bold text-white flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-accent-primary" />
                    SQL Generation Agent
                  </div>
                  <p className="text-[11px] text-typography-secondary">Google Gemini PostgreSQL generation</p>
                </div>

                <div className="p-3 rounded-xl bg-background-elevated border border-border space-y-1">
                  <div className="text-[10px] uppercase font-mono text-typography-muted">Node 4</div>
                  <div className="text-xs font-bold text-white flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-status-success" />
                    SQL Validation Agent
                  </div>
                  <p className="text-[11px] text-typography-secondary">SQLGlot deterministic security & rules</p>
                </div>

                <div className="p-3 rounded-xl bg-background-elevated border border-border space-y-1">
                  <div className="text-[10px] uppercase font-mono text-typography-muted">Node 5</div>
                  <div className="text-xs font-bold text-white flex items-center gap-1.5">
                    <Terminal className="w-3.5 h-3.5 text-status-warning" />
                    SQL Execution Agent
                  </div>
                  <p className="text-[11px] text-typography-secondary">Read-only transaction & 15s timeout</p>
                </div>

                <div className="p-3 rounded-xl bg-background-elevated border border-border space-y-1">
                  <div className="text-[10px] uppercase font-mono text-typography-muted">Node 6</div>
                  <div className="text-xs font-bold text-white flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5 text-status-info" />
                    Result & Visualization
                  </div>
                  <p className="text-[11px] text-typography-secondary">Gemini synthesis & Recharts spec</p>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
