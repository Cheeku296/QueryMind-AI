import React, { useEffect, useState } from 'react';
import {
  Building,
  Users,
  Shield,
  Plus,
  Trash2,
  CheckCircle2,
} from 'lucide-react';
import { apiRequest } from '../api/client';
import { useAuthStore } from '../store/useAuthStore';

export const WorkspaceSettings: React.FC = () => {
  const { activeWorkspaceId } = useAuthStore();
  const [workspace, setWorkspace] = useState<any>(null);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('EDITOR');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const loadWorkspace = async () => {
    if (!activeWorkspaceId) return;
    try {
      const data = await apiRequest(`/workspaces/${activeWorkspaceId}`);
      setWorkspace(data);
    } catch {}
  };

  useEffect(() => {
    loadWorkspace();
  }, [activeWorkspaceId]);

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail.trim() || isSubmitting) return;
    setIsSubmitting(true);
    try {
      const res = await apiRequest(`/workspaces/${activeWorkspaceId}/members`, {
        method: 'POST',
        body: JSON.stringify({ email: inviteEmail.trim(), role: inviteRole }),
      });
      setMsg(res.message);
      setInviteEmail('');
      loadWorkspace();
      setTimeout(() => setMsg(null), 3000);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Building className="w-5 h-5 text-accent-primary" />
          Workspace Management & RBAC
        </h1>
        <p className="text-xs text-typography-secondary mt-0.5">
          Manage workspace members, team roles (ADMIN, EDITOR, VIEWER), and permissions.
        </p>
      </div>

      {msg && (
        <div className="p-3.5 rounded-xl bg-status-success/10 border border-status-success/30 text-xs text-status-success flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{msg}</span>
        </div>
      )}

      {/* Workspace Details Card */}
      <div className="p-6 rounded-2xl bg-background-card border border-border space-y-3 shadow-xl">
        <h2 className="text-sm font-bold text-white">Workspace Overview</h2>
        <div className="grid grid-cols-2 gap-4 text-xs font-mono">
          <div className="p-3.5 rounded-xl bg-background-elevated border border-border">
            <span className="text-typography-muted text-[11px] block mb-1">Workspace Name</span>
            <span className="font-semibold text-white">{workspace?.name || 'Default Workspace'}</span>
          </div>
          <div className="p-3.5 rounded-xl bg-background-elevated border border-border">
            <span className="text-typography-muted text-[11px] block mb-1">Your Role</span>
            <span className="font-bold text-accent-primary">{workspace?.current_user_role || 'ADMIN'}</span>
          </div>
        </div>
      </div>

      {/* Add Member Form */}
      <div className="p-6 rounded-2xl bg-background-card border border-border space-y-4 shadow-xl">
        <h2 className="text-sm font-bold text-white flex items-center gap-2">
          <Plus className="w-4 h-4 text-accent-primary" />
          Add Team Member
        </h2>

        <form onSubmit={handleAddMember} className="flex gap-3 text-xs">
          <input
            type="email"
            required
            placeholder="colleague@company.com"
            value={inviteEmail}
            onChange={e => setInviteEmail(e.target.value)}
            className="flex-1 bg-background-elevated border border-border rounded-xl px-4 py-2 text-white placeholder-typography-muted focus:outline-none focus:border-accent-primary"
          />

          <select
            value={inviteRole}
            onChange={e => setInviteRole(e.target.value)}
            className="bg-background-elevated border border-border rounded-xl px-3 py-2 text-white focus:outline-none"
          >
            <option value="EDITOR">EDITOR (Queries & Reports)</option>
            <option value="VIEWER">VIEWER (Read-Only)</option>
            <option value="ADMIN">ADMIN (Full Control)</option>
          </select>

          <button
            type="submit"
            disabled={isSubmitting}
            className="px-4 py-2 rounded-xl bg-accent-primary hover:bg-accent-hover text-white font-semibold transition-all shadow-md shadow-accent-primary/20 disabled:opacity-50"
          >
            {isSubmitting ? 'Adding...' : 'Add Member'}
          </button>
        </form>
      </div>

      {/* Members List */}
      <div className="p-6 rounded-2xl bg-background-card border border-border space-y-4 shadow-xl">
        <h2 className="text-sm font-bold text-white flex items-center gap-2">
          <Users className="w-4 h-4 text-accent-secondary" />
          Workspace Members ({workspace?.members?.length || 0})
        </h2>

        <div className="divide-y divide-border/30 text-xs">
          {workspace?.members?.map((m: any) => (
            <div key={m.id} className="py-3 flex items-center justify-between">
              <div>
                <div className="font-semibold text-white">{m.name}</div>
                <div className="text-[11px] text-typography-secondary">{m.email}</div>
              </div>

              <span
                className={`text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full border ${
                  m.role === 'ADMIN'
                    ? 'bg-accent-primary/10 text-accent-primary border-accent-primary/30'
                    : m.role === 'EDITOR'
                    ? 'bg-accent-secondary/10 text-accent-secondary border-accent-secondary/30'
                    : 'bg-background-elevated text-typography-muted border-border'
                }`}
              >
                {m.role}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
