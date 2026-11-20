import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import {
  Play,
  Sparkles,
  AlignLeft,
  Bookmark,
  Clock,
  CheckCircle2,
  AlertCircle,
  Download,
  Copy,
  Check,
  Table as TableIcon,
  HelpCircle,
} from 'lucide-react';
import { apiRequest } from '../api/client';
import { useConnectionStore } from '../store/useConnectionStore';

export const SQLWorkspace: React.FC = () => {
  const location = useLocation();
  const { activeConnectionId, connections } = useConnectionStore();
  const [sql, setSql] = useState<string>(
    location.state?.initialSql ||
      'SELECT d.name AS department, COUNT(e.id) AS employees, ROUND(AVG(e.salary), 2) AS avg_salary\nFROM departments d\nLEFT JOIN employees e ON d.id = e.department_id\nGROUP BY d.name\nORDER BY employees DESC\nLIMIT 10;'
  );
  const [isRunning, setIsRunning] = useState(false);
  const [activeTab, setActiveTab] = useState<'results' | 'explanation'>('results');
  const [executionResult, setExecutionResult] = useState<any>(null);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [saveTitle, setSaveTitle] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    if (location.state?.initialSql) {
      setSql(location.state.initialSql);
    }
  }, [location.state]);

  const handleRunQuery = async () => {
    if (!sql.trim() || !activeConnectionId || isRunning) return;
    setIsRunning(true);
    setExecutionResult(null);
    try {
      const res = await apiRequest('/sql/execute', {
        method: 'POST',
        body: JSON.stringify({
          connection_id: activeConnectionId,
          sql: sql.trim(),
        }),
      });
      setExecutionResult(res);
      setActiveTab('results');
    } catch (e: any) {
      setExecutionResult({
        success: false,
        error: e.message || 'Execution error',
      });
    } finally {
      setIsRunning(false);
    }
  };

  const handleExplainQuery = async () => {
    if (!sql.trim() || !activeConnectionId) return;
    try {
      const res = await apiRequest('/sql/explain', {
        method: 'POST',
        body: JSON.stringify({
          connection_id: activeConnectionId,
          sql: sql.trim(),
        }),
      });
      setExplanation(res.explanation);
      setActiveTab('explanation');
    } catch (e: any) {
      setExplanation(`Explanation error: ${e.message}`);
    }
  };

  const handleFormatSQL = async () => {
    if (!sql.trim()) return;
    try {
      const res = await apiRequest('/sql/format', {
        method: 'POST',
        body: JSON.stringify({ sql: sql.trim(), dialect: 'postgres' }),
      });
      if (res.formatted_sql) {
        setSql(res.formatted_sql);
      }
    } catch {}
  };

  const handleSaveQuery = async () => {
    const title = saveTitle.trim() || `Query - ${new Date().toLocaleDateString()}`;
    setIsSaving(true);
    try {
      await apiRequest('/saved-queries', {
        method: 'POST',
        body: JSON.stringify({
          title,
          sql: sql.trim(),
          tags: ['workspace'],
        }),
      });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch {}
    setIsSaving(false);
  };

  const exportCSV = () => {
    if (!executionResult || !executionResult.columns) return;
    const lines = [executionResult.columns.map((c: string) => `"${c}"`).join(',')];
    executionResult.rows.forEach((r: any[]) => {
      lines.push(r.map(val => (val !== null ? `"${val}"` : '""')).join(','));
    });
    const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `query_result_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const activeConn = connections.find(c => c.id === activeConnectionId);

  return (
    <div className="flex flex-col h-[calc(100vh-6.5rem)] space-y-4">
      {/* Editor & Actions Toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            onClick={handleRunQuery}
            disabled={isRunning || !activeConnectionId}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-accent-primary hover:bg-accent-hover disabled:opacity-40 text-white text-xs font-semibold shadow-md shadow-accent-primary/20 transition-all"
          >
            <Play className={`w-3.5 h-3.5 fill-current ${isRunning ? 'animate-spin' : ''}`} />
            <span>{isRunning ? 'Executing...' : 'Run Query'}</span>
          </button>

          <button
            onClick={handleExplainQuery}
            disabled={!activeConnectionId || !sql.trim()}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-background-elevated hover:bg-background-card border border-border text-xs text-typography-primary font-medium transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5 text-accent-primary" />
            <span>Explain Query</span>
          </button>

          <button
            onClick={handleFormatSQL}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-background-elevated hover:bg-background-card border border-border text-xs text-typography-primary font-medium transition-colors"
          >
            <AlignLeft className="w-3.5 h-3.5" />
            <span>Format</span>
          </button>
        </div>

        {/* Save & Copy */}
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Save as..."
            value={saveTitle}
            onChange={e => setSaveTitle(e.target.value)}
            className="w-40 px-3 py-1.5 rounded-lg bg-background-elevated border border-border text-xs text-typography-primary placeholder-typography-muted focus:outline-none"
          />
          <button
            onClick={handleSaveQuery}
            disabled={isSaving}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-background-elevated hover:bg-background-card border border-border text-xs text-typography-primary font-medium transition-colors"
          >
            {saveSuccess ? (
              <Check className="w-3.5 h-3.5 text-status-success" />
            ) : (
              <Bookmark className="w-3.5 h-3.5 text-accent-secondary" />
            )}
            <span>{saveSuccess ? 'Saved!' : 'Save'}</span>
          </button>
        </div>
      </div>

      {/* Monaco Editor Container */}
      <div className="h-64 rounded-2xl border border-border bg-[#1E1E1E] overflow-hidden shadow-xl">
        <Editor
          height="100%"
          defaultLanguage="sql"
          theme="vs-dark"
          value={sql}
          onChange={val => setSql(val || '')}
          options={{
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            automaticLayout: true,
            padding: { top: 12, bottom: 12 },
          }}
        />
      </div>

      {/* Tabs & Results Panel */}
      <div className="flex-1 rounded-2xl border border-border bg-background-card flex flex-col overflow-hidden shadow-xl">
        {/* Tabs Bar */}
        <div className="h-12 px-4 border-b border-border bg-background-secondary flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setActiveTab('results')}
              className={`flex items-center gap-1.5 text-xs font-semibold py-2 px-3 border-b-2 transition-colors ${
                activeTab === 'results'
                  ? 'border-accent-primary text-accent-primary'
                  : 'border-transparent text-typography-secondary hover:text-typography-primary'
              }`}
            >
              <TableIcon className="w-3.5 h-3.5" />
              <span>Query Results</span>
              {executionResult?.row_count !== undefined && (
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-background-elevated font-mono text-typography-primary">
                  {executionResult.row_count}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('explanation')}
              className={`flex items-center gap-1.5 text-xs font-semibold py-2 px-3 border-b-2 transition-colors ${
                activeTab === 'explanation'
                  ? 'border-accent-primary text-accent-primary'
                  : 'border-transparent text-typography-secondary hover:text-typography-primary'
              }`}
            >
              <HelpCircle className="w-3.5 h-3.5" />
              <span>AI Explanation</span>
            </button>
          </div>

          {/* Result Metadata / Action */}
          <div className="flex items-center gap-3">
            {executionResult && (
              <div className="flex items-center gap-2 text-xs font-mono text-typography-secondary">
                <Clock className="w-3.5 h-3.5" />
                <span>{executionResult.execution_time_ms} ms</span>
              </div>
            )}
            {executionResult?.rows && executionResult.rows.length > 0 && (
              <button
                onClick={exportCSV}
                className="flex items-center gap-1 px-2.5 py-1 rounded bg-background-elevated hover:bg-background-card border border-border text-xs text-typography-primary"
              >
                <Download className="w-3 h-3" />
                <span>Export CSV</span>
              </button>
            )}
          </div>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-auto p-4">
          {activeTab === 'results' ? (
            !executionResult ? (
              <div className="h-full flex flex-col items-center justify-center text-center text-typography-muted text-xs">
                Click <span className="font-semibold text-accent-primary mx-1">Run Query</span> to execute against the active database.
              </div>
            ) : !executionResult.success ? (
              <div className="p-4 rounded-xl bg-status-error/10 border border-status-error/30 text-xs text-status-error space-y-1">
                <div className="font-semibold flex items-center gap-1.5">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>Execution Error:</span>
                </div>
                <pre className="font-mono text-[11px] whitespace-pre-wrap">{executionResult.error}</pre>
              </div>
            ) : executionResult.rows.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-typography-muted">
                Query executed successfully. 0 rows returned.
              </div>
            ) : (
              <table className="w-full text-left text-xs">
                <thead className="bg-background-elevated text-typography-muted border-b border-border sticky top-0">
                  <tr>
                    {executionResult.columns.map((c: string) => (
                      <th key={c} className="py-2 px-3 font-semibold whitespace-nowrap">
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/30 text-typography-primary">
                  {executionResult.rows.map((row: any[], rIdx: number) => (
                    <tr key={rIdx} className="hover:bg-background-elevated/40 transition-colors">
                      {row.map((val: any, cIdx: number) => (
                        <td key={cIdx} className="py-2 px-3 font-mono text-[11px] whitespace-nowrap">
                          {val !== null ? String(val) : <span className="text-typography-muted italic">null</span>}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            )
          ) : (
            <div className="p-4 text-xs leading-relaxed text-typography-primary whitespace-pre-wrap">
              {explanation || 'Click "Explain Query" to receive an in-depth breakdown of this SQL statement from Gemini.'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

