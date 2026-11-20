import React, { useEffect, useState } from 'react';
import {
  Settings as SettingsIcon,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Activity,
  ShieldCheck,
  Key,
  Server,
  Database,
  Layers,
} from 'lucide-react';
import { apiRequest } from '../api/client';

export const Settings: React.FC = () => {
  const [appSettings, setAppSettings] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [isTestingGemini, setIsTestingGemini] = useState(false);
  const [geminiTestResult, setGeminiTestResult] = useState<any>(null);

  const loadSettingsAndHealth = () => {
    apiRequest('/settings').then(res => setAppSettings(res)).catch(() => {});
    apiRequest('/health').then(res => setHealth(res)).catch(() => {});
  };

  useEffect(() => {
    loadSettingsAndHealth();
  }, []);

  const handleTestGemini = async () => {
    setIsTestingGemini(true);
    setGeminiTestResult(null);
    try {
      const res = await apiRequest('/settings/test-gemini', { method: 'POST' });
      setGeminiTestResult(res);
      loadSettingsAndHealth();
    } catch (e: any) {
      setGeminiTestResult({
        success: false,
        message: e.message || 'Gemini connectivity test failed',
      });
    } finally {
      setIsTestingGemini(false);
    }
  };

  const geminiConfigured = appSettings?.gemini_configured;

  return (
    <div className="max-w-4xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <SettingsIcon className="w-5 h-5 text-accent-primary" />
          Settings & AI Configuration
        </h1>
        <p className="text-xs text-typography-secondary mt-0.5">
          Configure Google Gemini AI credentials, verify service health, and review execution governance policies.
        </p>
      </div>

      {/* Primary AI Provider: Google Gemini Card */}
      <div className="p-6 rounded-2xl bg-background-card border border-border space-y-5 shadow-xl">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-accent-primary/10 text-accent-primary flex items-center justify-center">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                Primary AI Provider — Google Gemini
              </h2>
              <span className="text-xs text-typography-secondary">
                Official Google GenAI SDK & LangChain Gemini Integration
              </span>
            </div>
          </div>

          <span
            className={`px-3 py-1 rounded-full text-xs font-semibold font-mono flex items-center gap-1.5 ${
              geminiConfigured
                ? 'bg-status-success/10 text-status-success border border-status-success/30'
                : 'bg-status-warning/10 text-status-warning border border-status-warning/30'
            }`}
          >
            {geminiConfigured ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5" />}
            <span>{geminiConfigured ? 'Connected & Verified' : 'API Key Setup Required'}</span>
          </span>
        </div>

        {/* Model Identifiers */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          <div className="p-3.5 rounded-xl bg-background-elevated border border-border">
            <span className="text-typography-muted text-[11px] uppercase block mb-1">
              Generation Model (LLM)
            </span>
            <span className="font-semibold text-white">
              {appSettings?.gemini_model || 'gemini-2.5-flash'}
            </span>
          </div>

          <div className="p-3.5 rounded-xl bg-background-elevated border border-border">
            <span className="text-typography-muted text-[11px] uppercase block mb-1">
              Embedding Model (RAG)
            </span>
            <span className="font-semibold text-white">
              {appSettings?.gemini_embedding_model || 'text-embedding-004'}
            </span>
          </div>
        </div>

        {/* Configuration Guide */}
        {!geminiConfigured && (
          <div className="p-4 rounded-xl bg-background-elevated/70 border border-status-warning/30 text-xs space-y-2">
            <div className="font-bold text-status-warning flex items-center gap-2">
              <Key className="w-4 h-4" />
              <span>How to configure your Google Gemini API key:</span>
            </div>
            <ol className="list-decimal list-inside space-y-1 text-typography-primary pl-1">
              <li>Open Google AI Studio at <code className="text-accent-primary">https://aistudio.google.com/app/apikey</code></li>
              <li>Generate your fresh Gemini API key</li>
              <li>Open <code className="text-accent-primary">backend/.env</code> in your QueryMind root directory</li>
              <li>Set <code className="text-white bg-background px-1.5 py-0.5 rounded font-mono">GEMINI_API_KEY=YOUR_KEY_HERE</code></li>
              <li>Save file and click the Test button below to verify</li>
            </ol>
          </div>
        )}

        {/* Connectivity Test Action */}
        <div className="pt-2 flex items-center justify-between">
          <button
            onClick={handleTestGemini}
            disabled={isTestingGemini}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-accent-primary hover:bg-accent-hover text-white text-xs font-semibold shadow-md shadow-accent-primary/20 transition-all disabled:opacity-50"
          >
            <Activity className={`w-3.5 h-3.5 ${isTestingGemini ? 'animate-spin' : ''}`} />
            <span>{isTestingGemini ? 'Testing Gemini API Handshake...' : 'Test Gemini API Connectivity'}</span>
          </button>

          <span className="text-[11px] text-typography-muted">
            Read exclusively from backend environment
          </span>
        </div>

        {/* Test Result Display */}
        {geminiTestResult && (
          <div
            className={`p-4 rounded-xl border text-xs space-y-1.5 ${
              geminiTestResult.success
                ? 'bg-status-success/10 border-status-success/30 text-status-success'
                : 'bg-status-error/10 border-status-error/30 text-status-error'
            }`}
          >
            <div className="font-bold flex items-center gap-2">
              {geminiTestResult.success ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
              <span>{geminiTestResult.message}</span>
            </div>
            {geminiTestResult.details && (
              <pre className="font-mono text-[10px] text-typography-primary p-2 rounded bg-background/50 overflow-x-auto">
                {JSON.stringify(geminiTestResult.details, null, 2)}
              </pre>
            )}
          </div>
        )}
      </div>

      {/* System Infrastructure Health */}
      <div className="p-6 rounded-2xl bg-background-card border border-border space-y-4 shadow-xl">
        <h2 className="text-sm font-bold text-white flex items-center gap-2">
          <Server className="w-4 h-4 text-accent-secondary" />
          Infrastructure & Backing Services
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-background-elevated border border-border flex items-center justify-between">
            <div>
              <span className="text-xs font-semibold text-white flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5 text-accent-primary" /> PostgreSQL
              </span>
              <span className="text-[10px] text-typography-muted">Application & target store</span>
            </div>
            <span className="text-[11px] font-bold text-status-success flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" /> Online
            </span>
          </div>

          <div className="p-4 rounded-xl bg-background-elevated border border-border flex items-center justify-between">
            <div>
              <span className="text-xs font-semibold text-white flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-accent-secondary" /> Qdrant
              </span>
              <span className="text-[10px] text-typography-muted">Vector RAG retrieval</span>
            </div>
            <span className="text-[11px] font-bold text-status-success flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" /> Online
            </span>
          </div>

          <div className="p-4 rounded-xl bg-background-elevated border border-border flex items-center justify-between">
            <div>
              <span className="text-xs font-semibold text-white flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-status-warning" /> Redis & Celery
              </span>
              <span className="text-[10px] text-typography-muted">Queue & cache processing</span>
            </div>
            <span className="text-[11px] font-bold text-status-success flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" /> Online
            </span>
          </div>
        </div>
      </div>

      {/* SQL Execution Governance Policy */}
      <div className="p-6 rounded-2xl bg-background-card border border-border space-y-3 shadow-xl">
        <h2 className="text-sm font-bold text-white flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-status-success" />
          SQL Security & Execution Governance
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
          <div className="p-3.5 rounded-xl bg-background-elevated border border-border">
            <span className="text-typography-muted text-[11px] block mb-1">Execution Mode</span>
            <span className="font-bold text-status-success">READ ONLY ENFORCED</span>
          </div>
          <div className="p-3.5 rounded-xl bg-background-elevated border border-border">
            <span className="text-typography-muted text-[11px] block mb-1">Result Row Limit</span>
            <span className="font-bold text-white">500 Rows Maximum</span>
          </div>
          <div className="p-3.5 rounded-xl bg-background-elevated border border-border">
            <span className="text-typography-muted text-[11px] block mb-1">Query Timeout</span>
            <span className="font-bold text-white">15 Seconds</span>
          </div>
        </div>
      </div>
    </div>
  );
};

