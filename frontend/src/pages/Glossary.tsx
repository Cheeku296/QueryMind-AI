import React, { useEffect, useState } from 'react';
import {
  BookOpen,
  Plus,
  Trash2,
  Edit2,
  Table as TableIcon,
  Search,
  Sparkles,
} from 'lucide-react';
import { apiRequest } from '../api/client';
import { useConnectionStore } from '../store/useConnectionStore';

export const Glossary: React.FC = () => {
  const { activeConnectionId } = useConnectionStore();
  const [terms, setTerms] = useState<any[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  // Form state
  const [term, setTerm] = useState('');
  const [definition, setDefinition] = useState('');
  const [tablesStr, setTablesStr] = useState('');
  const [colsStr, setColsStr] = useState('');
  const [exampleSql, setExampleSql] = useState('');

  const loadTerms = async () => {
    try {
      const data = await apiRequest('/glossary');
      setTerms(data || []);
    } catch {}
  };

  useEffect(() => {
    loadTerms();
  }, []);

  const handleOpenCreate = () => {
    setEditingId(null);
    setTerm('');
    setDefinition('');
    setTablesStr('orders, order_items');
    setColsStr('total_amount, status');
    setExampleSql("SELECT SUM(total_amount) FROM orders WHERE status = 'completed';");
    setShowModal(true);
  };

  const handleOpenEdit = (t: any) => {
    setEditingId(t.id);
    setTerm(t.term);
    setDefinition(t.definition);
    setTablesStr(t.associated_tables?.join(', ') || '');
    setColsStr(t.associated_columns?.join(', ') || '');
    setExampleSql(t.example_sql || '');
    setShowModal(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      term: term.trim(),
      definition: definition.trim(),
      associated_tables: tablesStr.split(',').map(s => s.trim()).filter(Boolean),
      associated_columns: colsStr.split(',').map(s => s.trim()).filter(Boolean),
      example_sql: exampleSql.trim() || undefined,
      connection_id: activeConnectionId || undefined,
    };

    try {
      if (editingId) {
        await apiRequest(`/glossary/${editingId}`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        });
      } else {
        await apiRequest('/glossary', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
      }
      setShowModal(false);
      loadTerms();
    } catch (e: any) {
      alert(`Failed to save glossary term: ${e.message}`);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this business glossary definition?')) return;
    try {
      await apiRequest(`/glossary/${id}`, { method: 'DELETE' });
      setTerms(prev => prev.filter(t => t.id !== id));
    } catch {}
  };

  const filtered = terms.filter(
    t =>
      t.term.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.definition.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-accent-primary" />
            Business Glossary
          </h1>
          <p className="text-xs text-typography-secondary mt-0.5">
            Define corporate metrics, domain jargon, and calculations indexed into Qdrant for accurate AI SQL generation.
          </p>
        </div>

        <button
          onClick={handleOpenCreate}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-accent-primary hover:bg-accent-hover text-white text-xs font-semibold shadow-md shadow-accent-primary/20 transition-all"
        >
          <Plus className="w-4 h-4" />
          <span>Add Definition</span>
        </button>
      </div>

      {/* Search Input */}
      <div className="relative max-w-md">
        <Search className="w-3.5 h-3.5 text-typography-muted absolute left-3 top-3 pointer-events-none" />
        <input
          type="text"
          placeholder="Filter glossary terms..."
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          className="w-full bg-background-card border border-border rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-typography-muted focus:outline-none focus:border-accent-primary"
        />
      </div>

      {/* Terms Grid */}
      {filtered.length === 0 ? (
        <div className="p-12 text-center text-xs text-typography-muted rounded-2xl bg-background-card border border-border">
          No glossary definitions found. Add terms like "Revenue", "Active Customer", or "Churn Rate".
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filtered.map(item => (
            <div
              key={item.id}
              className="p-5 rounded-2xl bg-background-card border border-border flex flex-col justify-between space-y-4 hover:border-accent-primary/40 transition-all group"
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <h3 className="text-sm font-bold text-white tracking-tight">{item.term}</h3>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => handleOpenEdit(item)}
                      className="p-1 text-typography-muted hover:text-white"
                      title="Edit term"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => handleDelete(item.id)}
                      className="p-1 text-typography-muted hover:text-status-error"
                      title="Delete term"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                <p className="text-xs text-typography-secondary leading-relaxed">{item.definition}</p>

                {item.associated_tables?.length > 0 && (
                  <div className="mt-3 flex items-center gap-1.5 flex-wrap">
                    {item.associated_tables.map((t: string) => (
                      <span
                        key={t}
                        className="text-[10px] px-2 py-0.5 rounded bg-background-elevated text-typography-muted border border-border font-mono flex items-center gap-1"
                      >
                        <TableIcon className="w-2.5 h-2.5" /> {t}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {item.example_sql && (
                <div className="pt-3 border-t border-border">
                  <span className="text-[10px] uppercase font-mono text-typography-muted block mb-1">
                    Example SQL Rule
                  </span>
                  <pre className="p-2.5 rounded-lg bg-[#0F1117] border border-border text-[10px] font-mono text-[#E2E8F0] overflow-x-auto">
                    <code>{item.example_sql}</code>
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Add / Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg bg-background-card border border-border rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-accent-primary" />
                {editingId ? 'Edit Glossary Term' : 'Add Business Definition'}
              </h2>
              <button onClick={() => setShowModal(false)} className="text-typography-muted text-sm">
                ✕
              </button>
            </div>

            <form onSubmit={handleSave} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-typography-secondary font-medium mb-1">Business Term</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Net Revenue"
                  value={term}
                  onChange={e => setTerm(e.target.value)}
                  className="w-full bg-background-elevated border border-border rounded-lg px-3 py-2 text-white focus:outline-none focus:border-accent-primary"
                />
              </div>

              <div>
                <label className="block text-typography-secondary font-medium mb-1">Exact Definition / Calculation Rule</label>
                <textarea
                  rows={3}
                  required
                  placeholder="e.g. Total order item subtotal excluding cancelled or refunded orders."
                  value={definition}
                  onChange={e => setDefinition(e.target.value)}
                  className="w-full bg-background-elevated border border-border rounded-lg p-3 text-white focus:outline-none focus:border-accent-primary"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-typography-secondary font-medium mb-1">Associated Tables (comma-separated)</label>
                  <input
                    type="text"
                    placeholder="orders, payments"
                    value={tablesStr}
                    onChange={e => setTablesStr(e.target.value)}
                    className="w-full bg-background-elevated border border-border rounded-lg px-3 py-2 text-white focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-typography-secondary font-medium mb-1">Associated Columns</label>
                  <input
                    type="text"
                    placeholder="total_amount, status"
                    value={colsStr}
                    onChange={e => setColsStr(e.target.value)}
                    className="w-full bg-background-elevated border border-border rounded-lg px-3 py-2 text-white focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-typography-secondary font-medium mb-1">Example SQL Implementation (Optional)</label>
                <textarea
                  rows={2}
                  placeholder="SELECT SUM(total_amount) FROM orders WHERE status = 'completed';"
                  value={exampleSql}
                  onChange={e => setExampleSql(e.target.value)}
                  className="w-full font-mono text-[11px] bg-background-elevated border border-border rounded-lg p-3 text-white focus:outline-none focus:border-accent-primary"
                />
              </div>

              <div className="pt-3 border-t border-border flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-3 py-2 rounded-lg text-typography-secondary hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-accent-primary hover:bg-accent-hover text-white font-semibold shadow-md shadow-accent-primary/20"
                >
                  Save & Index in Qdrant
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
