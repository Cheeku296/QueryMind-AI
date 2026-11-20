import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Bookmark,
  Plus,
  Play,
  Trash2,
  Tag,
  Copy,
  Check,
  Search,
} from 'lucide-react';
import { apiRequest } from '../api/client';

export const SavedQueries: React.FC = () => {
  const [queries, setQueries] = useState<any[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const loadQueries = async () => {
    try {
      const data = await apiRequest('/saved-queries');
      setQueries(data || []);
    } catch {}
  };

  useEffect(() => {
    loadQueries();
  }, []);

  const copySql = (sql: string, id: string) => {
    navigator.clipboard.writeText(sql);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this saved query?')) return;
    try {
      await apiRequest(`/saved-queries/${id}`, { method: 'DELETE' });
      setQueries(prev => prev.filter(q => q.id !== id));
    } catch {}
  };

  const filteredQueries = queries.filter(q =>
    q.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    q.sql.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Bookmark className="w-5 h-5 text-accent-primary" />
            Saved Queries Library
          </h1>
          <p className="text-xs text-typography-secondary mt-0.5">
            Curated and approved SQL queries reusable across your workspace team.
          </p>
        </div>

        <Link
          to="/workspace"
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-accent-primary hover:bg-accent-hover text-white text-xs font-semibold shadow-md shadow-accent-primary/20 transition-all"
        >
          <Plus className="w-4 h-4" />
          <span>New Query</span>
        </Link>
      </div>

      {/* Search Input */}
      <div className="relative max-w-md">
        <Search className="w-3.5 h-3.5 text-typography-muted absolute left-3 top-3 pointer-events-none" />
        <input
          type="text"
          placeholder="Filter saved queries..."
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          className="w-full bg-background-card border border-border rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-typography-muted focus:outline-none focus:border-accent-primary"
        />
      </div>

      {/* Saved Queries Grid */}
      {filteredQueries.length === 0 ? (
        <div className="p-12 text-center text-xs text-typography-muted rounded-2xl bg-background-card border border-border">
          No saved queries found. Save queries from the SQL Workspace or AI Assistant!
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {filteredQueries.map(q => (
            <div
              key={q.id}
              className="p-5 rounded-2xl bg-background-card border border-border hover:border-accent-primary/40 transition-all flex flex-col justify-between space-y-3 group"
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <h3 className="text-sm font-bold text-white group-hover:text-accent-primary transition-colors">
                    {q.title}
                  </h3>
                  <button
                    onClick={() => handleDelete(q.id)}
                    className="p-1 text-typography-muted hover:text-status-error opacity-0 group-hover:opacity-100 transition-opacity"
                    title="Delete query"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                {q.description && (
                  <p className="text-xs text-typography-secondary mb-2">{q.description}</p>
                )}

                {/* SQL Code Block */}
                <pre className="p-3 rounded-xl bg-[#0F1117] border border-border text-[11px] font-mono text-[#E2E8F0] overflow-x-auto max-h-32">
                  <code>{q.sql}</code>
                </pre>
              </div>

              <div className="pt-3 border-t border-border flex items-center justify-between">
                <div className="flex items-center gap-1.5 flex-wrap">
                  {q.tags?.map((t: string) => (
                    <span
                      key={t}
                      className="text-[10px] px-2 py-0.5 rounded-full bg-background-elevated text-typography-secondary border border-border flex items-center gap-1"
                    >
                      <Tag className="w-2.5 h-2.5" />
                      {t}
                    </span>
                  ))}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => copySql(q.sql, q.id)}
                    className="p-1.5 rounded-lg bg-background-elevated hover:bg-background-card border border-border text-typography-secondary hover:text-white"
                    title="Copy SQL"
                  >
                    {copiedId === q.id ? <Check className="w-3.5 h-3.5 text-status-success" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                  <Link
                    to="/workspace"
                    state={{ initialSql: q.sql }}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-accent-primary/10 hover:bg-accent-primary/20 text-accent-primary text-xs font-semibold border border-accent-primary/30 transition-colors"
                  >
                    <Play className="w-3 h-3" />
                    <span>Run Query</span>
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

