import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText,
  Plus,
  Trash2,
  Download,
  Clock,
  Sparkles,
  ArrowRight,
  Database,
} from 'lucide-react';
import { apiRequest } from '../api/client';
import { useConnectionStore } from '../store/useConnectionStore';

export const Reports: React.FC = () => {
  const { activeConnectionId, connections } = useConnectionStore();
  const [reports, setReports] = useState<any[]>([]);
  const [showGenerateModal, setShowGenerateModal] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  // Form state
  const [reportTitle, setReportTitle] = useState('Monthly E-Commerce Revenue & Orders Analysis');
  const [reportType, setReportType] = useState('analytical');
  const [customSql, setCustomSql] = useState(
    'SELECT DATE_TRUNC(\'month\', order_date)::date as month, count(id) as total_orders, sum(total_amount) as revenue\nFROM orders\nWHERE status = \'completed\'\nGROUP BY month\nORDER BY month DESC\nLIMIT 12;'
  );

  const loadReports = async () => {
    try {
      const data = await apiRequest('/reports');
      setReports(data || []);
    } catch {}
  };

  useEffect(() => {
    loadReports();
  }, []);

  const handleGenerateReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeConnectionId || isGenerating) return;
    setIsGenerating(true);
    try {
      await apiRequest('/reports/generate', {
        method: 'POST',
        body: JSON.stringify({
          connection_id: activeConnectionId,
          title: reportTitle.trim(),
          report_type: reportType,
          sql_query: customSql.trim(),
        }),
      });
      setShowGenerateModal(false);
      loadReports();
    } catch (e: any) {
      alert(`Report generation failed: ${e.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this report?')) return;
    try {
      await apiRequest(`/reports/${id}`, { method: 'DELETE' });
      setReports(prev => prev.filter(r => r.id !== id));
    } catch {}
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <FileText className="w-5 h-5 text-accent-primary" />
            Analytical Reports
          </h1>
          <p className="text-xs text-typography-secondary mt-0.5">
            AI-synthesized business reports with executive summaries, metrics, and data exports.
          </p>
        </div>

        <button
          onClick={() => setShowGenerateModal(true)}
          disabled={!activeConnectionId}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-accent-primary hover:bg-accent-hover disabled:opacity-50 text-white text-xs font-semibold shadow-md shadow-accent-primary/20 transition-all"
        >
          <Sparkles className="w-4 h-4" />
          <span>Generate Report</span>
        </button>
      </div>

      {/* Reports Grid */}
      {reports.length === 0 ? (
        <div className="p-12 rounded-2xl bg-background-card border border-border text-center max-w-lg mx-auto">
          <FileText className="w-12 h-12 text-typography-muted mx-auto mb-3 opacity-40" />
          <h3 className="text-base font-bold text-white">No Reports Generated Yet</h3>
          <p className="text-xs text-typography-secondary mt-1 max-w-sm mx-auto">
            Generate your first business intelligence report using actual query results and Google Gemini synthesis.
          </p>
          <button
            onClick={() => setShowGenerateModal(true)}
            className="mt-4 px-4 py-2 rounded-xl bg-accent-primary hover:bg-accent-hover text-white text-xs font-semibold"
          >
            Create New Report
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {reports.map(r => (
            <Link
              key={r.id}
              to={`/reports/${r.id}`}
              className="p-5 rounded-2xl bg-background-card border border-border hover:border-accent-primary/50 transition-all group flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-background-elevated text-typography-secondary border border-border">
                    {r.report_type}
                  </span>
                  <button
                    onClick={e => handleDelete(r.id, e)}
                    className="p-1 text-typography-muted hover:text-status-error opacity-0 group-hover:opacity-100 transition-opacity"
                    title="Delete Report"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                <h3 className="text-sm font-bold text-white group-hover:text-accent-primary transition-colors line-clamp-2">
                  {r.title}
                </h3>

                <p className="text-xs text-typography-secondary mt-2 line-clamp-3 leading-relaxed">
                  {r.report_content?.executive_summary || 'Executive analytical summary.'}
                </p>
              </div>

              <div className="mt-5 pt-3 border-t border-border flex items-center justify-between text-[11px] text-typography-muted">
                <span>{new Date(r.created_at).toLocaleDateString()}</span>
                <span className="flex items-center gap-1 text-accent-primary font-medium group-hover:translate-x-0.5 transition-transform">
                  View Report <ArrowRight className="w-3 h-3" />
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Generate Report Modal */}
      {showGenerateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg bg-background-card border border-border rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-accent-primary" />
                Generate Analytical Report
              </h2>
              <button onClick={() => setShowGenerateModal(false)} className="text-typography-muted text-sm">
                ✕
              </button>
            </div>

            <form onSubmit={handleGenerateReport} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-typography-secondary font-medium mb-1">Report Title</label>
                <input
                  type="text"
                  required
                  value={reportTitle}
                  onChange={e => setReportTitle(e.target.value)}
                  className="w-full bg-background-elevated border border-border rounded-lg px-3 py-2 text-white focus:outline-none focus:border-accent-primary"
                />
              </div>

              <div>
                <label className="block text-typography-secondary font-medium mb-1">Report Type</label>
                <select
                  value={reportType}
                  onChange={e => setReportType(e.target.value)}
                  className="w-full bg-background-elevated border border-border rounded-lg px-3 py-2 text-white focus:outline-none"
                >
                  <option value="analytical">Executive Analytical Report</option>
                  <option value="summary">Data Summary</option>
                  <option value="trend">Trend & Forecasting Analysis</option>
                  <option value="comparative">Comparative Assessment</option>
                </select>
              </div>

              <div>
                <label className="block text-typography-secondary font-medium mb-1">Source SQL Query</label>
                <textarea
                  rows={4}
                  required
                  value={customSql}
                  onChange={e => setCustomSql(e.target.value)}
                  className="w-full font-mono text-[11px] bg-background-elevated border border-border rounded-lg p-3 text-white focus:outline-none focus:border-accent-primary"
                />
              </div>

              <div className="pt-3 border-t border-border flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowGenerateModal(false)}
                  className="px-3 py-2 rounded-lg text-typography-secondary hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isGenerating}
                  className="px-4 py-2 rounded-lg bg-accent-primary hover:bg-accent-hover text-white font-semibold flex items-center gap-1.5 shadow-md shadow-accent-primary/20"
                >
                  <Sparkles className={`w-3.5 h-3.5 ${isGenerating ? 'animate-spin' : ''}`} />
                  <span>{isGenerating ? 'Generating with Gemini...' : 'Generate Report'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

