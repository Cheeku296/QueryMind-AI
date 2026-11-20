import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Database,
  Bot,
  Terminal,
  Layers,
  FileText,
  Activity,
  CheckCircle2,
  Clock,
  Sparkles,
  ArrowRight,
  TrendingUp,
} from 'lucide-react';
import { apiRequest } from '../api/client';
import { useConnectionStore } from '../store/useConnectionStore';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';

export const Dashboard: React.FC = () => {
  const { connections } = useConnectionStore();
  const [overview, setOverview] = useState<any>(null);
  const [trends, setTrends] = useState<any[]>([]);
  const [recentQueries, setRecentQueries] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiRequest('/analytics/overview?days=30').catch(() => null),
      apiRequest('/analytics/query-trends?days=7').catch(() => ({ trends: [] })),
      apiRequest('/queries/history?limit=5').catch(() => ({ items: [] })),
    ]).then(([ov, tr, qh]) => {
      if (ov) setOverview(ov);
      if (tr && tr.trends) setTrends(tr.trends);
      if (qh && qh.items) setRecentQueries(qh.items);
      setIsLoading(false);
    });
  }, []);

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-background-card via-background-elevated to-background-card border border-border relative overflow-hidden">
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-accent-primary/10 border border-accent-primary/20 text-accent-primary text-xs font-semibold mb-3">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Google Gemini-Powered Database Intelligence</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Your Data. Your Questions. Intelligent Answers.
          </h1>
          <p className="text-sm text-typography-secondary mt-1.5 leading-relaxed">
            Connect your relational databases, discover schemas automatically, generate precision SQL with Google Gemini,
            and extract visual business intelligence in real time.
          </p>
          <div className="mt-4 flex items-center gap-3">
            <Link
              to="/assistant"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent-primary hover:bg-accent-hover text-white text-xs font-semibold shadow-md shadow-accent-primary/20 transition-all"
            >
              <Bot className="w-4 h-4" />
              <span>Ask AI Copilot</span>
            </Link>
            <Link
              to="/workspace"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-background-elevated hover:bg-background-secondary border border-border text-typography-primary text-xs font-semibold transition-all"
            >
              <Terminal className="w-4 h-4 text-accent-secondary" />
              <span>Open SQL Studio</span>
            </Link>
          </div>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Connected DBs */}
        <div className="p-5 rounded-xl bg-background-card border border-border flex items-center justify-between">
          <div>
            <span className="text-xs text-typography-secondary font-medium">Connected Databases</span>
            <div className="text-2xl font-bold text-white mt-1">
              {overview ? overview.connected_databases : connections.length}
            </div>
            <span className="text-[11px] text-status-success mt-1 inline-flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> Live & Introspected
            </span>
          </div>
          <div className="w-11 h-11 rounded-xl bg-accent-primary/10 text-accent-primary flex items-center justify-center">
            <Database className="w-5 h-5" />
          </div>
        </div>

        {/* Discovered Tables */}
        <div className="p-5 rounded-xl bg-background-card border border-border flex items-center justify-between">
          <div>
            <span className="text-xs text-typography-secondary font-medium">Discovered Tables</span>
            <div className="text-2xl font-bold text-white mt-1">
              {overview ? overview.available_tables : 0}
            </div>
            <span className="text-[11px] text-typography-secondary mt-1">Indexed in Qdrant Vector RAG</span>
          </div>
          <div className="w-11 h-11 rounded-xl bg-accent-secondary/10 text-accent-secondary flex items-center justify-center">
            <Layers className="w-5 h-5" />
          </div>
        </div>

        {/* Total Queries */}
        <div className="p-5 rounded-xl bg-background-card border border-border flex items-center justify-between">
          <div>
            <span className="text-xs text-typography-secondary font-medium">Queries Executed</span>
            <div className="text-2xl font-bold text-white mt-1">
              {overview ? overview.total_queries : 0}
            </div>
            <span className="text-[11px] text-status-success mt-1">
              {overview ? `${overview.success_rate}% Success Rate` : '100%'}
            </span>
          </div>
          <div className="w-11 h-11 rounded-xl bg-status-success/10 text-status-success flex items-center justify-center">
            <Activity className="w-5 h-5" />
          </div>
        </div>

        {/* Avg Latency */}
        <div className="p-5 rounded-xl bg-background-card border border-border flex items-center justify-between">
          <div>
            <span className="text-xs text-typography-secondary font-medium">Avg Execution Time</span>
            <div className="text-2xl font-bold text-white mt-1">
              {overview ? `${overview.average_query_duration_ms} ms` : '0 ms'}
            </div>
            <span className="text-[11px] text-typography-secondary mt-1">Safe read-only execution</span>
          </div>
          <div className="w-11 h-11 rounded-xl bg-status-warning/10 text-status-warning flex items-center justify-center">
            <Clock className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Charts & Quick Navigation Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Query Execution Trends */}
        <div className="lg:col-span-2 p-5 rounded-2xl bg-background-card border border-border space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-accent-primary" />
                Query Execution Volume & Trends
              </h3>
              <p className="text-xs text-typography-secondary mt-0.5">7-day execution trends</p>
            </div>
            <span className="text-xs px-2.5 py-1 rounded-md bg-background-elevated text-typography-secondary font-mono border border-border">
              Last 7 Days
            </span>
          </div>

          <div className="h-60 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trends.length > 0 ? trends : [{ date: 'Today', queries: overview?.total_queries || 1 }]}>
                <defs>
                  <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.6}/>
                    <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#293041" opacity={0.6} />
                <XAxis dataKey="date" stroke="#94A3B8" fontSize={11} tickLine={false} />
                <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#171B26', borderColor: '#293041', borderRadius: '8px', color: '#F8FAFC' }}
                />
                <Area type="monotone" dataKey="queries" stroke="#8B5CF6" strokeWidth={2.5} fill="url(#chartGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right Col: Quick Actions */}
        <div className="p-5 rounded-2xl bg-background-card border border-border flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-semibold text-white mb-3">Quick Navigation</h3>
            <div className="space-y-2.5">
              <Link
                to="/schema"
                className="flex items-center justify-between p-3 rounded-xl bg-background-elevated/70 hover:bg-background-elevated border border-border transition-colors group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-accent-primary/10 text-accent-primary flex items-center justify-center">
                    <Layers className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-white">Schema Explorer</div>
                    <div className="text-[10px] text-typography-secondary">Browse tables and preview data</div>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-typography-muted group-hover:text-accent-primary transition-colors" />
              </Link>

              <Link
                to="/er-diagram"
                className="flex items-center justify-between p-3 rounded-xl bg-background-elevated/70 hover:bg-background-elevated border border-border transition-colors group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-accent-secondary/10 text-accent-secondary flex items-center justify-center">
                    <Activity className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-white">ER Diagram</div>
                    <div className="text-[10px] text-typography-secondary">Visual relationship graph</div>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-typography-muted group-hover:text-accent-secondary transition-colors" />
              </Link>

              <Link
                to="/reports"
                className="flex items-center justify-between p-3 rounded-xl bg-background-elevated/70 hover:bg-background-elevated border border-border transition-colors group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-status-success/10 text-status-success flex items-center justify-center">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-white">Analytical Reports</div>
                    <div className="text-[10px] text-typography-secondary">Generate summaries & exports</div>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-typography-muted group-hover:text-status-success transition-colors" />
              </Link>

              <Link
                to="/connections"
                className="flex items-center justify-between p-3 rounded-xl bg-background-elevated/70 hover:bg-background-elevated border border-border transition-colors group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-status-warning/10 text-status-warning flex items-center justify-center">
                    <Database className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-white">Database Connections</div>
                    <div className="text-[10px] text-typography-secondary">Manage credentials & sync</div>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-typography-muted group-hover:text-status-warning transition-colors" />
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Query Activity Table */}
      <div className="p-5 rounded-2xl bg-background-card border border-border space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Clock className="w-4 h-4 text-accent-primary" />
            Recent Query Executions
          </h3>
          <Link to="/history" className="text-xs text-accent-primary hover:underline font-medium">
            View All History →
          </Link>
        </div>

        {recentQueries.length === 0 ? (
          <div className="p-8 text-center text-xs text-typography-muted">
            No queries executed yet. Ask a question in the AI SQL Assistant or run queries in SQL Workspace!
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-background-elevated/60 text-typography-muted border-b border-border">
                <tr>
                  <th className="py-2.5 px-3 font-medium">Status</th>
                  <th className="py-2.5 px-3 font-medium">Executed SQL</th>
                  <th className="py-2.5 px-3 font-medium">Database</th>
                  <th className="py-2.5 px-3 font-medium">Duration</th>
                  <th className="py-2.5 px-3 font-medium">Rows</th>
                  <th className="py-2.5 px-3 font-medium">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40 text-typography-primary">
                {recentQueries.map((q: any) => (
                  <tr key={q.id} className="hover:bg-background-elevated/40 transition-colors">
                    <td className="py-2.5 px-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium ${
                          q.status === 'success'
                            ? 'bg-status-success/10 text-status-success'
                            : 'bg-status-error/10 text-status-error'
                        }`}
                      >
                        {q.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] truncate max-w-md">
                      {q.executed_sql}
                    </td>
                    <td className="py-2.5 px-3 text-typography-secondary">{q.connection_name || 'PostgreSQL'}</td>
                    <td className="py-2.5 px-3 font-mono text-typography-secondary">{q.execution_time_ms} ms</td>
                    <td className="py-2.5 px-3 font-mono text-typography-secondary">{q.row_count}</td>
                    <td className="py-2.5 px-3 text-typography-muted">
                      {new Date(q.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

