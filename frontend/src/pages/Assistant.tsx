import React, { useEffect, useState, useRef } from 'react';
import {
  Bot,
  Send,
  Sparkles,
  Plus,
  Trash2,
  Copy,
  Check,
  Play,
  Bookmark,
  ChevronDown,
  ChevronUp,
  Download,
  Terminal,
  Activity,
  Layers,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { apiRequest } from '../api/client';
import { useConnectionStore } from '../store/useConnectionStore';
import { ChartRenderer } from '../components/chat/ChartRenderer';
import { Link } from 'react-router-dom';

const SAMPLE_QUESTIONS = [
  'How many employees are in each department?',
  'Which five products generated the highest revenue?',
  'Show monthly revenue for the previous six months.',
  'Which customers have not placed an order?',
  'What is the average order value?',
];

export const Assistant: React.FC = () => {
  const { activeConnectionId, connections } = useConnectionStore();
  const [conversations, setConversations] = useState<any[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [inputQuestion, setInputQuestion] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [copiedSql, setCopiedSql] = useState<string | null>(null);
  const [expandedEvents, setExpandedEvents] = useState<Record<string, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load conversations
  const loadConversations = async () => {
    try {
      const data = await apiRequest('/chat');
      setConversations(data || []);
      if (data && data.length > 0 && !activeConvId) {
        setActiveConvId(data[0].id);
        loadMessages(data[0].id);
      }
    } catch {}
  };

  const loadMessages = async (convId: string) => {
    try {
      const data = await apiRequest(`/chat/${convId}`);
      setMessages(data.messages || []);
    } catch {}
  };

  useEffect(() => {
    loadConversations();
  }, [activeConnectionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSubmitting]);

  const handleSelectConv = (id: string) => {
    setActiveConvId(id);
    loadMessages(id);
  };

  const handleNewConversation = () => {
    setActiveConvId(null);
    setMessages([]);
  };

  const handleDeleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await apiRequest(`/chat/${id}`, { method: 'DELETE' });
      setConversations(prev => prev.filter(c => c.id !== id));
      if (activeConvId === id) {
        handleNewConversation();
      }
    } catch {}
  };

  const handleSendMessage = async (customQ?: string) => {
    const q = (customQ || inputQuestion).trim();
    if (!q || !activeConnectionId || isSubmitting) return;

    setInputQuestion('');
    setIsSubmitting(true);

    // Optimistic user message
    const tempUserMsg = {
      id: `temp_${Date.now()}`,
      role: 'user',
      content: q,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, tempUserMsg]);

    try {
      const res = await apiRequest('/chat', {
        method: 'POST',
        body: JSON.stringify({
          connection_id: activeConnectionId,
          conversation_id: activeConvId,
          question: q,
        }),
      });

      if (!activeConvId && res.conversation_id) {
        setActiveConvId(res.conversation_id);
        loadConversations();
      }

      setMessages(prev => [...prev, res.message]);
    } catch (e: any) {
      setMessages(prev => [
        ...prev,
        {
          id: `err_${Date.now()}`,
          role: 'assistant',
          content: `Error: ${e.message}`,
          execution_status: 'failed',
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsSubmitting(false);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSql(id);
    setTimeout(() => setCopiedSql(null), 2000);
  };

  const exportTableCSV = (cols: string[], rows: any[][], title: string) => {
    const lines = [cols.map(c => `"${c}"`).join(',')];
    rows.forEach(r => {
      lines.push(r.map(val => (val !== null ? `"${val}"` : '""')).join(','));
    });
    const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title.toLowerCase().replace(/\s+/g, '_')}_results.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const activeConn = connections.find(c => c.id === activeConnectionId);

  return (
    <div className="flex h-[calc(100vh-6.5rem)] gap-4 overflow-hidden">
      {/* Conversation History Sidebar */}
      <div className="w-64 bg-background-card border border-border rounded-2xl flex flex-col overflow-hidden shrink-0">
        <div className="p-3 border-b border-border">
          <button
            onClick={handleNewConversation}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-accent-primary hover:bg-accent-hover text-white text-xs font-semibold shadow-sm transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>New Conversation</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {conversations.length === 0 ? (
            <div className="p-4 text-center text-xs text-typography-muted">No conversations yet.</div>
          ) : (
            conversations.map(c => (
              <div
                key={c.id}
                onClick={() => handleSelectConv(c.id)}
                className={`flex items-center justify-between px-3 py-2.5 rounded-lg text-xs cursor-pointer transition-colors group ${
                  activeConvId === c.id
                    ? 'bg-background-elevated text-accent-primary font-medium border border-border'
                    : 'text-typography-secondary hover:bg-background-elevated/50 hover:text-typography-primary'
                }`}
              >
                <span className="truncate pr-2">{c.title || 'Untitled Conversation'}</span>
                <button
                  onClick={e => handleDeleteConversation(c.id, e)}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-status-error transition-opacity"
                  title="Delete conversation"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main Chat Interface */}
      <div className="flex-1 bg-background-card border border-border rounded-2xl flex flex-col overflow-hidden shadow-2xl">
        {/* Chat Header */}
        <div className="h-14 px-5 border-b border-border bg-background-elevated/40 backdrop-blur flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-accent-primary/20 text-accent-primary flex items-center justify-center">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-xs font-bold text-white">AI SQL Copilot</h2>
              <span className="text-[10px] text-typography-secondary font-mono">
                {activeConn ? `Connected to: ${activeConn.name}` : 'No active database'}
              </span>
            </div>
          </div>
          <span className="text-[10px] px-2 py-0.5 rounded bg-accent-primary/10 border border-accent-primary/20 text-accent-primary font-mono">
            LangGraph Multi-Agent
          </span>
        </div>

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto my-auto py-12">
              <div className="w-12 h-12 rounded-2xl bg-accent-primary/10 text-accent-primary flex items-center justify-center mb-3">
                <Sparkles className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-white">Ask Anything About Your Database</h3>
              <p className="text-xs text-typography-secondary mt-1">
                Type your question in natural language. QueryMind AI retrieves relevant schemas via RAG,
                generates dialect-specific SQL with Google Gemini, executes safely, and visualizes results.
              </p>

              {/* Sample Questions */}
              <div className="mt-6 w-full space-y-2 text-left">
                <span className="text-[11px] font-semibold text-typography-muted uppercase tracking-wider block mb-1">
                  Suggested Questions:
                </span>
                {SAMPLE_QUESTIONS.map((sq, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(sq)}
                    className="w-full text-left p-2.5 rounded-lg bg-background-elevated hover:bg-background-elevated/80 border border-border text-xs text-typography-primary transition-all flex items-center justify-between group"
                  >
                    <span>{sq}</span>
                    <Sparkles className="w-3.5 h-3.5 text-accent-primary opacity-0 group-hover:opacity-100 transition-opacity" />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m, index) => (
              <div
                key={m.id || index}
                className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {m.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-lg bg-accent-primary/20 text-accent-primary flex items-center justify-center shrink-0 mt-1">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div className={`max-w-3xl space-y-3 ${m.role === 'user' ? 'w-auto' : 'w-full'}`}>
                  {/* Message Bubble */}
                  <div
                    className={`p-4 rounded-2xl text-xs leading-relaxed ${
                      m.role === 'user'
                        ? 'bg-accent-primary text-white rounded-tr-none'
                        : 'bg-background-elevated border border-border text-typography-primary rounded-tl-none shadow-lg'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{m.content}</p>
                  </div>

                  {/* Assistant Extra Assets (SQL, Results, Charts, Events) */}
                  {m.role === 'assistant' && (
                    <>
                      {/* Generated SQL Card */}
                      {m.generated_sql && (
                        <div className="rounded-xl bg-[#0F1117] border border-border overflow-hidden">
                          <div className="px-3 py-2 bg-background-secondary border-b border-border flex items-center justify-between text-[11px]">
                            <span className="font-mono text-accent-primary font-semibold flex items-center gap-1.5">
                              <Terminal className="w-3.5 h-3.5" /> Generated PostgreSQL
                            </span>
                            <div className="flex items-center gap-1.5">
                              <button
                                onClick={() => copyToClipboard(m.generated_sql, m.id)}
                                className="flex items-center gap-1 px-2 py-1 rounded hover:bg-background-elevated text-typography-secondary hover:text-white transition-colors"
                              >
                                {copiedSql === m.id ? (
                                  <>
                                    <Check className="w-3 h-3 text-status-success" />
                                    <span>Copied</span>
                                  </>
                                ) : (
                                  <>
                                    <Copy className="w-3 h-3" />
                                    <span>Copy SQL</span>
                                  </>
                                )}
                              </button>
                              <Link
                                to="/workspace"
                                state={{ initialSql: m.generated_sql }}
                                className="flex items-center gap-1 px-2 py-1 rounded hover:bg-background-elevated text-accent-primary transition-colors"
                              >
                                <Play className="w-3 h-3" />
                                <span>Run in Studio</span>
                              </Link>
                            </div>
                          </div>
                          <pre className="p-3 text-[11px] font-mono text-[#E2E8F0] overflow-x-auto selection:bg-accent-primary/40">
                            <code>{m.generated_sql}</code>
                          </pre>
                        </div>
                      )}

                      {/* Execution Results Table */}
                      {m.execution_result && m.execution_result.rows && m.execution_result.rows.length > 0 && (
                        <div className="rounded-xl bg-background-elevated border border-border overflow-hidden">
                          <div className="px-3 py-2 bg-background-card border-b border-border flex items-center justify-between text-[11px]">
                            <span className="font-medium text-white flex items-center gap-1.5">
                              <CheckCircle2 className="w-3.5 h-3.5 text-status-success" />
                              Results ({m.execution_result.row_count} rows in {m.execution_result.execution_time_ms} ms)
                            </span>
                            <button
                              onClick={() => exportTableCSV(m.execution_result.columns, m.execution_result.rows, 'query')}
                              className="flex items-center gap-1 px-2 py-1 rounded hover:bg-background-elevated text-typography-secondary hover:text-white transition-colors"
                            >
                              <Download className="w-3 h-3" />
                              <span>Export CSV</span>
                            </button>
                          </div>
                          <div className="max-h-56 overflow-auto">
                            <table className="w-full text-left text-[11px]">
                              <thead className="bg-background-secondary/80 text-typography-muted border-b border-border sticky top-0">
                                <tr>
                                  {m.execution_result.columns.map((c: string) => (
                                    <th key={c} className="py-1.5 px-3 font-semibold whitespace-nowrap">
                                      {c}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-border/30">
                                {m.execution_result.rows.slice(0, 15).map((row: any[], rIdx: number) => (
                                  <tr key={rIdx} className="hover:bg-background-card/50">
                                    {row.map((val: any, cIdx: number) => (
                                      <td key={cIdx} className="py-1.5 px-3 font-mono whitespace-nowrap">
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

                      {/* Recharts Visualization */}
                      {m.chart && m.chart.data && m.chart.data.length > 0 && (
                        <ChartRenderer chartSpec={m.chart} />
                      )}

                      {/* LangGraph Node Events Summary Accordion */}
                      {m.node_events && m.node_events.length > 0 && (
                        <div className="rounded-xl border border-border/70 bg-background-card/40 overflow-hidden">
                          <button
                            onClick={() =>
                              setExpandedEvents(prev => ({
                                ...prev,
                                [m.id]: !prev[m.id],
                              }))
                            }
                            className="w-full px-3 py-2 flex items-center justify-between text-[11px] text-typography-secondary hover:text-typography-primary font-mono transition-colors"
                          >
                            <span className="flex items-center gap-1.5">
                              <Activity className="w-3.5 h-3.5 text-accent-primary" />
                              Multi-Agent Execution Timeline ({m.node_events.length} events)
                            </span>
                            {expandedEvents[m.id] ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                          </button>
                          {expandedEvents[m.id] && (
                            <div className="p-3 border-t border-border/50 divide-y divide-border/20 text-[10px] font-mono space-y-1.5 bg-background-elevated/40">
                              {m.node_events.map((ev: any, idx: number) => (
                                <div key={idx} className="pt-1.5 flex items-start justify-between">
                                  <div>
                                    <span className="font-bold text-accent-primary uppercase mr-2">{ev.node}</span>
                                    <span className="text-typography-primary">{ev.output || ev.message}</span>
                                  </div>
                                  {ev.duration_ms !== undefined && (
                                    <span className="text-typography-muted shrink-0 ml-3">{ev.duration_ms} ms</span>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))
          )}

          {isSubmitting && (
            <div className="flex gap-3 items-start">
              <div className="w-8 h-8 rounded-lg bg-accent-primary/20 text-accent-primary flex items-center justify-center shrink-0 animate-pulse">
                <Bot className="w-4 h-4" />
              </div>
              <div className="p-3.5 rounded-2xl bg-background-elevated border border-border text-xs text-typography-secondary flex items-center gap-2.5">
                <div className="w-2 h-2 rounded-full bg-accent-primary animate-ping" />
                <span>LangGraph multi-agent pipeline executing (retrieval, SQL generation, validation)...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-border bg-background-secondary">
          <form
            onSubmit={e => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={inputQuestion}
              onChange={e => setInputQuestion(e.target.value)}
              placeholder="Ask a question about your database in natural language (e.g. 'Show total revenue for each month')..."
              disabled={isSubmitting || !activeConnectionId}
              className="flex-1 bg-background-elevated border border-border rounded-xl px-4 py-2.5 text-xs text-white placeholder-typography-muted focus:outline-none focus:border-accent-primary transition-colors disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isSubmitting || !inputQuestion.trim() || !activeConnectionId}
              className="px-4 py-2.5 rounded-xl bg-accent-primary hover:bg-accent-hover disabled:opacity-40 text-white text-xs font-semibold flex items-center gap-1.5 transition-all shadow-md shadow-accent-primary/20"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Send</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
