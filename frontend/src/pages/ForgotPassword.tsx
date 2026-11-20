import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Database, Mail, ArrowRight, ArrowLeft, CheckCircle2 } from 'lucide-react';
import { apiRequest } from '../api/client';

export const ForgotPassword: React.FC = () => {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [resetToken, setResetToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const res = await apiRequest('/auth/forgot-password', {
        method: 'POST',
        body: JSON.stringify({ email: email.trim() }),
      });
      setSent(true);
      if (res.reset_token) {
        setResetToken(res.reset_token);
      }
    } catch {}
    setIsLoading(false);
  };

  return (
    <div className="min-h-screen bg-background flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center space-y-2">
        <div className="inline-flex w-12 h-12 rounded-2xl bg-gradient-to-br from-accent-primary to-accent-secondary items-center justify-center shadow-lg shadow-accent-primary/25 mb-2">
          <Database className="w-6 h-6 text-white" />
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-white">Reset Password</h2>
        <p className="text-xs text-typography-secondary">
          Enter your registered email address to receive reset instructions.
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-background-card py-8 px-6 shadow-2xl border border-border rounded-2xl sm:px-10 space-y-6">
          {sent ? (
            <div className="space-y-4 text-center">
              <div className="w-12 h-12 rounded-full bg-status-success/10 text-status-success flex items-center justify-center mx-auto">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-bold text-white">Password Reset Instructions Dispatched</h3>
              <p className="text-xs text-typography-secondary">
                If an account with {email} exists, reset token instructions have been generated.
              </p>
              {resetToken && (
                <div className="p-3 bg-background-elevated rounded-xl border border-border text-[11px] font-mono text-left break-all text-typography-primary">
                  <span className="text-typography-muted text-[10px] block mb-1">Generated Dev Token:</span>
                  {resetToken}
                </div>
              )}
              <Link
                to="/login"
                className="inline-flex items-center gap-2 text-xs font-semibold text-accent-primary hover:underline mt-2"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Return to Sign In
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block font-medium text-typography-secondary mb-1">Email Address</label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-typography-muted absolute left-3 top-2.5 pointer-events-none" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    placeholder="name@company.com"
                    className="w-full bg-background-elevated border border-border rounded-xl pl-9 pr-3 py-2.5 text-white placeholder-typography-muted focus:outline-none focus:border-accent-primary"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full mt-2 py-2.5 px-4 rounded-xl bg-accent-primary hover:bg-accent-hover text-white text-xs font-semibold shadow-md shadow-accent-primary/20 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
              >
                <span>{isLoading ? 'Sending...' : 'Send Reset Link'}</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <div className="pt-2 text-center">
                <Link
                  to="/login"
                  className="inline-flex items-center gap-1.5 text-xs text-typography-secondary hover:text-white"
                >
                  <ArrowLeft className="w-3 h-3" /> Back to Sign In
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

