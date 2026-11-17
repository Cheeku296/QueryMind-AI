import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Database, Lock, Mail, ArrowRight, AlertCircle, Sparkles } from 'lucide-react';
import { apiRequest } from '../api/client';
import { useAuthStore } from '../store/useAuthStore';

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const [email, setEmail] = useState('admin@querymind.ai');
  const [password, setPassword] = useState('Password123!');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiRequest('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email: email.trim(), password }),
      });
      login(data);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Login failed. Please verify credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center space-y-2">
        <div className="inline-flex w-12 h-12 rounded-2xl bg-gradient-to-br from-accent-primary to-accent-secondary items-center justify-center shadow-lg shadow-accent-primary/25 mb-2">
          <Database className="w-6 h-6 text-white" />
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-white">
          Sign In to QueryMind AI
        </h2>
        <p className="text-xs text-typography-secondary">
          Your Data. Your Questions. Intelligent Answers.
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-background-card py-8 px-6 shadow-2xl border border-border rounded-2xl sm:px-10 space-y-6">
          {error && (
            <div className="p-3.5 rounded-xl bg-status-error/10 border border-status-error/30 text-xs text-status-error flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

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

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block font-medium text-typography-secondary">Password</label>
                <Link to="/forgot-password" className="text-accent-primary hover:underline text-[11px]">
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <Lock className="w-4 h-4 text-typography-muted absolute left-3 top-2.5 pointer-events-none" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-background-elevated border border-border rounded-xl pl-9 pr-3 py-2.5 text-white placeholder-typography-muted focus:outline-none focus:border-accent-primary"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-2 py-2.5 px-4 rounded-xl bg-accent-primary hover:bg-accent-hover text-white text-xs font-semibold shadow-md shadow-accent-primary/20 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
            >
              <span>{isLoading ? 'Signing In...' : 'Sign In'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          <div className="pt-4 border-t border-border text-center text-xs text-typography-secondary">
            Don't have an account yet?{' '}
            <Link to="/register" className="text-accent-primary hover:underline font-semibold ml-1">
              Create an account
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
