import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Bot,
  Terminal,
  Database,
  Layers,
  Network,
  BarChart3,
  FileText,
  History,
  Bookmark,
  Cpu,
  BookOpen,
  Settings,
  LogOut,
  ChevronDown,
  Building,
} from 'lucide-react';
import { useAuthStore } from '../../store/useAuthStore';

const navigationItems = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'AI SQL Assistant', path: '/assistant', icon: Bot },
  { name: 'SQL Workspace', path: '/workspace', icon: Terminal },
  { name: 'Database Connections', path: '/connections', icon: Database },
  { name: 'Schema Explorer', path: '/schema', icon: Layers },
  { name: 'ER Diagram', path: '/er-diagram', icon: Network },
  { name: 'Analytics', path: '/analytics', icon: BarChart3 },
  { name: 'Reports', path: '/reports', icon: FileText },
  { name: 'Query History', path: '/history', icon: History },
  { name: 'Saved Queries', path: '/saved-queries', icon: Bookmark },
  { name: 'Agent Monitor', path: '/agents', icon: Cpu },
  { name: 'Business Glossary', path: '/glossary', icon: BookOpen },
  { name: 'Settings', path: '/settings', icon: Settings },
];

export const Sidebar: React.FC = () => {
  const { user, workspaces, activeWorkspaceId, setActiveWorkspace, logout } = useAuthStore();
  const currentWs = workspaces.find(w => w.id === activeWorkspaceId);

  return (
    <aside className="w-64 bg-background-secondary border-r border-border flex flex-col h-screen fixed left-0 top-0 z-30 select-none">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-5 border-b border-border bg-background-card/40 backdrop-blur">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-accent-primary to-accent-secondary flex items-center justify-center shadow-lg shadow-accent-primary/20">
            <Database className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="font-bold text-base tracking-tight text-white flex items-center gap-1.5">
              QueryMind <span className="text-xs px-1.5 py-0.5 rounded bg-accent-primary/20 text-accent-primary font-mono font-medium">AI</span>
            </div>
            <div className="text-[10px] text-typography-secondary font-medium tracking-wide">
              DB Intelligence & SQL Copilot
            </div>
          </div>
        </div>
      </div>

      {/* Navigation List */}
      <div className="flex-1 overflow-y-auto py-3 px-3 space-y-1">
        <div className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-typography-muted">
          Platform
        </div>
        {navigationItems.map(item => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-accent-primary text-white shadow-sm shadow-accent-primary/30 font-semibold'
                    : 'text-typography-secondary hover:text-typography-primary hover:bg-background-elevated'
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span className="truncate">{item.name}</span>
            </NavLink>
          );
        })}
      </div>

      {/* Footer / Workspace & User */}
      <div className="p-3 border-t border-border bg-background-card/20 space-y-2">
        {/* Workspace selector */}
        {workspaces.length > 0 && (
          <div className="relative">
            <select
              value={activeWorkspaceId || ''}
              onChange={e => setActiveWorkspace(e.target.value)}
              className="w-full bg-background-elevated text-typography-primary text-xs rounded-lg px-2.5 py-1.5 border border-border appearance-none cursor-pointer pr-7 focus:outline-none focus:border-accent-primary"
            >
              {workspaces.map(w => (
                <option key={w.id} value={w.id} className="bg-background-card">
                  {w.name} ({w.role})
                </option>
              ))}
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-typography-secondary absolute right-2.5 top-2.5 pointer-events-none" />
          </div>
        )}

        {/* User Card */}
        <div className="flex items-center justify-between p-2 rounded-lg bg-background-elevated/50 border border-border/50">
          <div className="flex items-center gap-2 overflow-hidden">
            <div className="w-7 h-7 rounded-full bg-accent-secondary/30 text-accent-secondary flex items-center justify-center font-bold text-xs shrink-0">
              {user?.name?.[0]?.toUpperCase() || 'U'}
            </div>
            <div className="truncate text-left">
              <div className="text-xs font-medium text-typography-primary truncate">{user?.name || 'User'}</div>
              <div className="text-[10px] text-typography-secondary truncate">{user?.email || ''}</div>
            </div>
          </div>
          <button
            onClick={logout}
            title="Log Out"
            className="p-1.5 rounded hover:bg-background-card text-typography-muted hover:text-status-error transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </aside>
  );
};
