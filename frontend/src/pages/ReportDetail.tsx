import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  FileText,
  ArrowLeft,
  Download,
  Clock,
  Terminal,
  Database,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
} from 'lucide-react';
import { apiRequest } from '../api/client';

export const ReportDetail: React.FC = () => {
  const { reportId } = useParams<{ reportId: string }>();
  const [report, setReport] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [copiedSql, setCopiedSql] = useState(false);

  useEffect(() => {
    if (!reportId) return;
    apiRequest(`/reports/${reportId}`)
      .then(res => setReport(res))
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, [reportId]);

  const copySql = () => {
    if (!report?.report_content?.sql_query) return;
    navigator.clipboard.writeText(report.report_content.sql_query);
    setCopiedSql(true);
    setTimeout(() => setCopiedSql(false), 2000);
  };

  const handleDownload = async (format: 'json' | 'csv') => {
    if (!reportId) return;
    try {
      const res = await apiRequest(`/reports/${reportId}/download?format=${format}`);
      const blob = new Blob([typeof res === 'string' ? res : JSON.stringify(res, null, 2)], {
        type: format === 'csv' ? 'text/csv' : 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${report.title.toLowerCase().replace(/\s+/g, '_')}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {}
  };

  if (isLoading) {
    return (
      <div className="h-64 flex items-center justify-center text-xs text-typography-muted">
        Loading analytical report...
      </div>
    );
  }

  if (!report) {
    return (
      <div className="p-8 text-center text-xs text-status-error">
        Report not found. <Link to="/reports" className="text-accent-primary underline ml-1">Return to reports</Link>
      </div>
    );
  }

  const content = report.report_content || {};

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-12">
      {/* Top Bar Navigation & Actions */}
      <div className="flex items-center justify-between">
        <Link
          to="/reports"
          className="inline-flex items-center gap-1.5 text-xs text-typography-secondary hover:text-white transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to All Reports</span>
        </Link>

        <div className="flex items-center gap-2">
          <button
            onClick={() => handleDownload('csv')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-background-elevated hover:bg-background-card border border-border text-xs text-typography-primary transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download CSV</span>
          </button>
          <button
            onClick={() => handleDownload('json')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-background-elevated hover:bg-background-card border border-border text-xs text-typography-primary transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download JSON</span>
          </button>
        </div>
      </div>

      {/* Main Report Document Card */}
      <div className="p-8 rounded-2xl bg-background-card border border-border space-y-8 shadow-2xl">
        {/* Document Header */}
        <div className="border-b border-border pb-6 space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono uppercase px-2.5 py-0.5 rounded bg-accent-primary/10 border border-accent-primary/20 text-accent-primary">
              {report.report_type}
            </span>
            <span className="text-xs text-typography-muted font-mono">
              Generated {new Date(report.created_at).toLocaleString()}
            </span>
          </div>

          <h1 className="text-2xl font-bold text-white tracking-tight">{report.title}</h1>
          <p className="text-xs text-typography-secondary flex items-center gap-2">
            <Database className="w-3.5 h-3.5 text-accent-primary" />
            <span>Database Source: {content.database_source || 'PostgreSQL'}</span>
          </p>
        </div>

        {/* 1. Executive Summary */}
        <div className="space-y-2">
          <h2 className="text-xs font-bold uppercase tracking-wider text-accent-primary flex items-center gap-2">
            1. Executive Summary
          </h2>
          <div className="p-4 rounded-xl bg-background-elevated/70 border border-border text-xs text-typography-primary leading-relaxed whitespace-pre-wrap">
            {content.executive_summary}
          </div>
        </div>

        {/* 2. Key Metrics */}
        {content.key_metrics && (
          <div className="space-y-3">
            <h2 className="text-xs font-bold uppercase tracking-wider text-accent-primary">
              2. Key Metrics
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {Object.entries(content.key_metrics).map(([key, val]: [string, any]) => (
                <div key={key} className="p-4 rounded-xl bg-background-elevated border border-border">
                  <span className="text-[11px] text-typography-secondary uppercase font-medium">
                    {key.replace(/_/g, ' ')}
                  </span>
                  <div className="text-xl font-bold text-white mt-1 font-mono">
                    {String(val)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 3. Findings & Takeaways */}
        {content.findings && content.findings.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-xs font-bold uppercase tracking-wider text-accent-primary">
              3. Core Findings
            </h2>
            <ul className="space-y-2 text-xs text-typography-primary">
              {content.findings.map((f: string, i: number) => (
                <li key={i} className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-status-success shrink-0 mt-0.5" />
                  <span>{f}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 4. Executed SQL Query */}
        {content.sql_query && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-bold uppercase tracking-wider text-accent-primary flex items-center gap-2">
                <Terminal className="w-3.5 h-3.5" /> 4. Executed SQL Statement
              </h2>
              <button
                onClick={copySql}
                className="flex items-center gap-1 text-[11px] text-typography-secondary hover:text-white"
              >
                {copiedSql ? <Check className="w-3 h-3 text-status-success" /> : <Copy className="w-3 h-3" />}
                <span>{copiedSql ? 'Copied' : 'Copy SQL'}</span>
              </button>
            </div>
            <pre className="p-4 rounded-xl bg-[#0F1117] border border-border text-[11px] font-mono text-[#E2E8F0] overflow-x-auto">
              <code>{content.sql_query}</code>
            </pre>
          </div>
        )}

        {/* 5. Data Sample */}
        {content.sample_rows && content.columns && (
          <div className="space-y-3">
            <h2 className="text-xs font-bold uppercase tracking-wider text-accent-primary">
              5. Data Sample (First {content.sample_rows.length} rows)
            </h2>
            <div className="overflow-x-auto rounded-xl border border-border">
              <table className="w-full text-left text-xs">
                <thead className="bg-background-elevated text-typography-muted border-b border-border">
                  <tr>
                    {content.columns.map((c: string) => (
                      <th key={c} className="py-2 px-3 font-medium whitespace-nowrap">
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/30 text-typography-primary">
                  {content.sample_rows.map((row: any[], rIdx: number) => (
                    <tr key={rIdx} className="hover:bg-background-elevated/40">
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

        {/* 6. Limitations */}
        {content.limitations && (
          <div className="p-4 rounded-xl bg-background-elevated/40 border border-border text-[11px] text-typography-muted space-y-1">
            <span className="font-semibold text-typography-secondary block">Scope & Limitations:</span>
            {content.limitations.map((lim: string, idx: number) => (
              <p key={idx}>• {lim}</p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

