import React, { useEffect, useState } from 'react';
import {
  BarChart3,
  Activity,
  CheckCircle2,
  Clock,
  TrendingUp,
  Cpu,
  Database,
  Calendar,
} from 'lucide-react';
import { apiRequest } from '../api/client';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';

export const Analytics: React.FC = () => {
  const [days, setDays] = useState(30);
  const [overview, setOverview] = useState<any>(null);
  const [trends, setTrends] = useState<any[]>([]);
  const [dbUsage, setDbUsage] = useState<any[]>([]);
  const [agentPerf, setAgentPerf] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    Promise.all([
      apiRequest(`/analytics/overview?days=${days}`).catch(() => null),
      apiRequest(`/analytics/query-trends?days=${days}`).catch(() => ({ trends: [] })),
      apiRequest('/analytics/database-usage').catch(() => []),
      apiRequest('/analytics/agent-performance').catch(() => null),
    ]).then(([ov, tr, du, ap]) => {
      if (ov) setOverview(ov);
      if (tr && tr.trends) setTrends(tr.trends);
      if (du) setDbUsage(du);
      if (ap) setAgentPerf(ap);
      setIsLoading(false);
    });
  }, [days]);

  return (
    <div className="space-y-6">
      {/* Header and Filter */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-accent-primary" />
            Analytics & Usage Intelligence
          </h1>
          <p className="text-xs text-typography-secondary mt-0.5">
            Query performance metrics, database utilization, and multi-agent workflow statistics.
          </p>
        </div>

        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-background-elevated border border-border">
          {[7, 30, 90].map(d => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                days === d
                  ? 'bg-accent-primary text-white font-semibold'
                  : 'text-typography-secondary hover:text-white'
              }`}
            >
              Last {d} Days
            </button>
          ))}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl bg-background-card border border-border">
          <span className="text-xs text-typography-secondary font-medium">Total Query Executions</span>
          <div className="text-2xl font-bold text-white mt-1">
            {overview ? overview.total_queries : 0}
          </div>
          <span className="text-[11px] text-status-success mt-1 inline-flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" />
            {overview ? `${overview.successful_queries} successful` : '0'}
          </span>
        </div>

        <div className="p-5 rounded-xl bg-background-card border border-border">
          <span className="text-xs text-typography-secondary font-medium">Query Success Rate</span>
          <div className="text-2xl font-bold text-white mt-1">
            {overview ? `${overview.success_rate}%` : '100%'}
          </div>
          <span className="text-[11px] text-typography-secondary mt-1">
            {overview?.failed_queries || 0} failed / corrected
          </span>
        </div>

        <div className="p-5 rounded-xl bg-background-card border border-border">
          <span className="text-xs text-typography-secondary font-medium">Average Query Duration</span>
          <div className="text-2xl font-bold text-white mt-1">
            {overview ? `${overview.average_query_duration_ms} ms` : '0 ms'}
          </div>
          <span className="text-[11px] text-status-success mt-1">Target &lt; 200ms</span>
        </div>

        <div className="p-5 rounded-xl bg-background-card border border-border">
          <span className="text-xs text-typography-secondary font-medium">Agent Workflow Success</span>
          <div className="text-2xl font-bold text-white mt-1">
            {agentPerf ? `${agentPerf.workflow_success_rate}%` : '100%'}
          </div>
          <span className="text-[11px] text-typography-secondary mt-1">
            {agentPerf ? `${agentPerf.total_agent_runs} LangGraph runs` : '0 runs'}
          </span>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Trend Area Chart */}
        <div className="p-5 rounded-2xl bg-background-card border border-border space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-accent-primary" />
              Daily Query Execution Volume
            </h3>
          </div>
          <div className="h-64 pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trends.length > 0 ? trends : [{ date: 'Today', queries: overview?.total_queries || 1 }]}>
                <defs>
                  <linearGradient id="anGrad" x1="0" y1="0" x2="0" y2="1">
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
                <Area type="monotone" dataKey="queries" stroke="#8B5CF6" strokeWidth={2.5} fill="url(#anGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Database Usage Distribution */}
        <div className="p-5 rounded-2xl bg-background-card border border-border space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Database className="w-4 h-4 text-accent-secondary" />
              Database Utilization Breakdown
            </h3>
          </div>
          <div className="h-64 pt-2">
            {dbUsage.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-typography-muted">
                No database query records found.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={dbUsage}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#293041" opacity={0.6} />
                  <XAxis dataKey="database" stroke="#94A3B8" fontSize={11} tickLine={false} />
                  <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#171B26', borderColor: '#293041', borderRadius: '8px', color: '#F8FAFC' }}
                  />
                  <Bar dataKey="query_count" fill="#6366F1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
