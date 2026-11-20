import React, { useEffect, useState } from 'react';
import {
  Layers,
  Search,
  Key,
  Database,
  Table as TableIcon,
  RefreshCw,
  Eye,
  Info,
} from 'lucide-react';
import { useConnectionStore } from '../store/useConnectionStore';
import { apiRequest } from '../api/client';

export const SchemaExplorer: React.FC = () => {
  const { activeConnectionId, connections } = useConnectionStore();
  const [tables, setTables] = useState<any[]>([]);
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [tableDetails, setTableDetails] = useState<any>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);

  const loadTables = async () => {
    if (!activeConnectionId) return;
    setIsLoading(true);
    try {
      const data = await apiRequest(`/connections/${activeConnectionId}/schema/tables`);
      setTables(data || []);
      if (data && data.length > 0 && !selectedTable) {
        handleSelectTable(data[0].name);
      }
    } catch {}
    setIsLoading(false);
  };

  const handleSelectTable = async (tableName: string) => {
    setSelectedTable(tableName);
    setPreviewLoading(true);
    try {
      const details = await apiRequest(
        `/connections/${activeConnectionId}/schema/tables/${tableName}?preview=true&preview_limit=10`
      );
      setTableDetails(details);
    } catch {}
    setPreviewLoading(false);
  };

  useEffect(() => {
    loadTables();
  }, [activeConnectionId]);

  const filteredTables = tables.filter(t =>
    t.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const activeConn = connections.find(c => c.id === activeConnectionId);

  return (
    <div className="flex h-[calc(100vh-6.5rem)] gap-5 overflow-hidden">
      {/* Tables Sidebar */}
      <div className="w-80 bg-background-card border border-border rounded-2xl flex flex-col overflow-hidden shrink-0">
        <div className="p-4 border-b border-border space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-accent-primary" />
              Tables ({tables.length})
            </h2>
            <button
              onClick={loadTables}
              disabled={isLoading}
              title="Refresh tables"
              className="p-1.5 rounded-lg hover:bg-background-elevated text-typography-secondary hover:text-white"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-accent-primary' : ''}`} />
            </button>
          </div>

          <div className="relative">
            <Search className="w-3.5 h-3.5 text-typography-muted absolute left-3 top-2.5 pointer-events-none" />
            <input
              type="text"
              placeholder="Filter tables..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="w-full bg-background-elevated border border-border rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-typography-muted focus:outline-none focus:border-accent-primary"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {filteredTables.length === 0 ? (
            <div className="p-6 text-center text-xs text-typography-muted">
              {tables.length === 0 ? 'No tables found in connection.' : 'No matching tables.'}
            </div>
          ) : (
            filteredTables.map(t => (
              <div
                key={t.name}
                onClick={() => handleSelectTable(t.name)}
                className={`p-3 rounded-xl cursor-pointer transition-colors border ${
                  selectedTable === t.name
                    ? 'bg-background-elevated border-accent-primary text-white shadow-sm'
                    : 'bg-transparent border-transparent text-typography-secondary hover:bg-background-elevated/40 hover:text-typography-primary'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <TableIcon className="w-3.5 h-3.5 text-accent-secondary shrink-0" />
                    <span className="font-semibold text-xs truncate">{t.name}</span>
                  </div>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-background/50 text-typography-muted">
                    {t.row_count} rows
                  </span>
                </div>
                {t.description && (
                  <p className="text-[10px] text-typography-muted truncate mt-0.5">{t.description}</p>
                )}
                <div className="mt-1 text-[10px] text-typography-muted flex gap-2">
                  <span>{t.columns_count} columns</span>
                  {t.primary_key?.length > 0 && <span>• PK: {t.primary_key.join(', ')}</span>}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Table Details & Controlled Preview Panel */}
      <div className="flex-1 bg-background-card border border-border rounded-2xl flex flex-col overflow-hidden shadow-2xl">
        {!selectedTable || !tableDetails ? (
          <div className="h-full flex flex-col items-center justify-center p-6 text-center text-typography-muted">
            <Layers className="w-12 h-12 mb-3 opacity-30 text-accent-primary" />
            <h3 className="text-sm font-semibold text-typography-primary">Select a Table to Inspect</h3>
            <p className="text-xs text-typography-secondary mt-1">
              View schema attributes, column types, primary/foreign keys, and data preview.
            </p>
          </div>
        ) : (
          <div className="h-full flex flex-col overflow-y-auto">
            {/* Table Header Details */}
            <div className="p-6 border-b border-border bg-background-elevated/30">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-accent-primary/10 text-accent-primary flex items-center justify-center">
                    <TableIcon className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-white tracking-tight">{tableDetails.name}</h2>
                    <span className="text-xs text-typography-secondary">
                      Schema: <code className="text-accent-secondary">public</code> • Estimated Rows: {tableDetails.row_count}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs px-2.5 py-1 rounded-lg bg-background-elevated border border-border text-typography-secondary font-mono">
                    {tableDetails.columns?.length || 0} Columns
                  </span>
                </div>
              </div>

              {tableDetails.description && (
                <div className="mt-3 p-3 rounded-lg bg-background-elevated/60 border border-border text-xs text-typography-primary flex items-center gap-2">
                  <Info className="w-4 h-4 text-accent-primary shrink-0" />
                  <span>{tableDetails.description}</span>
                </div>
              )}
            </div>

            {/* Columns Schema Section */}
            <div className="p-6 space-y-4">
              <h3 className="text-xs font-bold text-typography-muted uppercase tracking-wider">
                Columns & Constraints
              </h3>

              <div className="overflow-x-auto rounded-xl border border-border">
                <table className="w-full text-left text-xs">
                  <thead className="bg-background-elevated text-typography-muted border-b border-border">
                    <tr>
                      <th className="py-2.5 px-3 font-medium">Column Name</th>
                      <th className="py-2.5 px-3 font-medium">Data Type</th>
                      <th className="py-2.5 px-3 font-medium">Key / Constraint</th>
                      <th className="py-2.5 px-3 font-medium">Nullable</th>
                      <th className="py-2.5 px-3 font-medium">Description</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/30 text-typography-primary">
                    {tableDetails.columns?.map((col: any) => {
                      const isPk = tableDetails.primary_key?.includes(col.name);
                      const fk = tableDetails.foreign_keys?.find((f: any) => f.column === col.name);
                      return (
                        <tr key={col.name} className="hover:bg-background-elevated/40">
                          <td className="py-2.5 px-3 font-mono font-semibold text-white">
                            {col.name}
                          </td>
                          <td className="py-2.5 px-3 font-mono text-accent-secondary">
                            {col.data_type}
                          </td>
                          <td className="py-2.5 px-3">
                            {isPk ? (
                              <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-status-warning/10 text-status-warning border border-status-warning/20">
                                <Key className="w-3 h-3" /> PK
                              </span>
                            ) : fk ? (
                              <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded bg-accent-primary/10 text-accent-primary border border-accent-primary/20">
                                FK → {fk.target_table}.{fk.target_column}
                              </span>
                            ) : (
                              <span className="text-typography-muted text-[10px]">-</span>
                            )}
                          </td>
                          <td className="py-2.5 px-3 text-typography-secondary">
                            {col.is_nullable ? 'YES' : 'NO'}
                          </td>
                          <td className="py-2.5 px-3 text-typography-muted">
                            {col.description || '-'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Live Data Preview Section */}
            {tableDetails.preview && tableDetails.preview.rows && (
              <div className="p-6 pt-0 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold text-typography-muted uppercase tracking-wider flex items-center gap-1.5">
                    <Eye className="w-3.5 h-3.5 text-accent-primary" />
                    Data Sample Preview (First {tableDetails.preview.rows.length} rows)
                  </h3>
                  <span className="text-[10px] text-typography-muted">Controlled row limit</span>
                </div>

                <div className="overflow-x-auto rounded-xl border border-border">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-background-elevated text-typography-muted border-b border-border">
                      <tr>
                        {tableDetails.preview.columns?.map((c: string) => (
                          <th key={c} className="py-2 px-3 font-medium whitespace-nowrap">
                            {c}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/30 text-typography-primary">
                      {tableDetails.preview.rows.map((row: any[], idx: number) => (
                        <tr key={idx} className="hover:bg-background-elevated/40">
                          {row.map((val: any, cIdx: number) => (
                            <td key={cIdx} className="py-2 px-3 font-mono text-[11px] whitespace-nowrap">
                              {val !== null ? String(val) : <span className="text-typography-muted italic">null</span>}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

