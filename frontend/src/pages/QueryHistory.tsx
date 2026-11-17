import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  History,
  Search,
  CheckCircle2,
  AlertCircle,
  Play,
  Copy,
  Check,
  Bookmark,
  Clock,
  Filter,
} from 'lucide-react';
import { apiRequest } from '../api/client';

export const QueryHistory: React.FC = () => {
  const [history, setHistory] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const loadHistory = async () => {
    setIsLoading(true);
    try {
      let endpoint = `/queries/history?limit=100`;
      if (searchTerm.trim()) endpoint += `&search=${encodeURIComponent(searchTerm.trim())}`;
      if (statusFilter) endpoint += `&status=${statusFilter}`;
      const data = await apiRequest(endpoint);
      setHistory(data.items || []);
      setTotal(data.total || 0);
    } catch {}
    setIsLoading(false);
  };

  useEffect(() => {
    loadHistory();
  }, [statusFilter]);

  const copySql = (sql: string, id: string) => {
    navigator.clipboard.writeText(sql);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <History className="w-5 h-5 text-accent-primary" />
            Query Execution History
          </h1>
          <p className="text-xs text-typography-secondary mt-0.5">
            Audit log of all queries executed through the AI Assistant or SQL Studio.
          </p>
        </div>

        <span className="text-xs font-mono px-3 py-1.5 rounded-lg bg-background-elevated border border-border text-typography-secondary">
          {total} Total Queries Logged
        </span>
      </div>

      {/* Filters Bar */}
      <div className="flex items-center gap-3">
        <div className="flex-1 relative">
          <Search className="w-3.5 h-3.5 text-typography-muted absolute left-3 top-3 pointer-events-none" />
          <input
            type="text"
            placeholder="Search queries or questions..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && loadHistory()}
            className="w-full bg-background-card border border-border rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-typography-muted focus:outline-none focus:border-accent-primary"
          />
        </div>

        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="bg-background-card border border-border rounded-xl px-3 py-2 text-xs text-typography-primary focus:outline-none"
          >
            <option value="">All Statuses</option>
            <option value="success">Successful</option>
            <option value="failed">Failed</option>
          </select>

          <button
            onClick={loadHistory}
            className="px-4 py-2 rounded-xl bg-background-elevated hover:bg-background-card border border-border text-xs text-typography-primary font-medium"
          >
            Apply
          </button>
        </div>
      </div>

      {/* History Table Card */}
      <div className="rounded-2xl bg-background-card border border-border overflow-hidden shadow-xl">
        {isLoading ? (
          <div className="p-12 text-center text-xs text-typography-muted">Loading query logs...</div>
        ) : history.length === 0 ? (
          <div className="p-12 text-center text-xs text-typography-muted">No query execution history found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-background-elevated text-typography-muted border-b border-border">
                <tr>
                  <th className="py-3 px-4 font-semibold">Status</th>
                  <th className="py-3 px-4 font-semibold">Natural Question / Prompt</th>
                  <th className="py-3 px-4 font-semibold">Executed SQL</th>
                  <th className="py-3 px-4 font-semibold">Database</th>
                  <th className="py-3 px-4 font-semibold">Duration</th>
                  <th className="py-3 px-4 font-semibold">Rows</th>
                  <th className="py-3 px-4 font-semibold">Timestamp</th>
                  <th className="py-3 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/30 text-typography-primary">
                {history.map(item => (
                  <tr key={item.id} className="hover:bg-background-elevated/40 transition-colors">
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium ${
                          item.status === 'success'
                            ? 'bg-status-success/10 text-status-success'
                            : 'bg-status-error/10 text-status-error'
                        }`}
                      >
                        {item.status === 'success' ? (
                          <CheckCircle2 className="w-3 h-3" />
                        ) : (
                          <AlertCircle className="w-3 h-3" />
                        )}
                        {item.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-white font-medium max-w-xs truncate">
                      {item.original_question || '-'}
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px] max-w-sm truncate text-typography-secondary">
                      {item.executed_sql}
                    </td>
                    <td className="py-3 px-4 text-typography-secondary">{item.connection_name}</td>
                    <td className="py-3 px-4 font-mono text-typography-secondary">{item.execution_time_ms} ms</td>
                    <td className="py-3 px-4 font-mono text-typography-secondary">{item.row_count}</td>
                    <td className="py-3 px-4 text-typography-muted text-[11px] whitespace-nowrap">
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => copySql(item.executed_sql, item.id)}
                          title="Copy SQL"
                          className="p-1.5 rounded hover:bg-background-elevated text-typography-secondary hover:text-white"
                        >
                          {copiedId === item.id ? <Check className="w-3.5 h-3.5 text-status-success" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                        <Link
                          to="/workspace"
                          state={{ initialSql: item.executed_sql }}
                          title="Open in SQL Studio"
                          className="p-1.5 rounded hover:bg-background-elevated text-accent-primary"
                        >
                          <Play className="w-3.5 h-3.5" />
                        </Link>
                      </div>
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
