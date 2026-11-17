import { create } from 'zustand';
import { User, Workspace } from '../types';
import { apiRequest } from '../api/client';

interface AuthState {
  user: User | null;
  token: string | null;
  workspaces: Workspace[];
  activeWorkspaceId: string | null;
  isLoading: boolean;
  login: (data: any) => void;
  logout: () => void;
  setActiveWorkspace: (id: string) => void;
  fetchUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: JSON.parse(localStorage.getItem('querymind_user') || 'null'),
  token: localStorage.getItem('querymind_token'),
  workspaces: [],
  activeWorkspaceId: localStorage.getItem('querymind_workspace_id'),
  isLoading: true,

  login: (data: any) => {
    localStorage.setItem('querymind_token', data.access_token);
    localStorage.setItem('querymind_user', JSON.stringify(data.user));
    if (data.user.workspace_id) {
      localStorage.setItem('querymind_workspace_id', data.user.workspace_id);
    }
    set({
      token: data.access_token,
      user: data.user,
      activeWorkspaceId: data.user.workspace_id || null,
      isLoading: false,
    });
    get().fetchUser();
  },

  logout: () => {
    localStorage.removeItem('querymind_token');
    localStorage.removeItem('querymind_user');
    localStorage.removeItem('querymind_workspace_id');
    set({
      user: null,
      token: null,
      workspaces: [],
      activeWorkspaceId: null,
      isLoading: false,
    });
    window.location.href = '/login';
  },

  setActiveWorkspace: (id: string) => {
    localStorage.setItem('querymind_workspace_id', id);
    set({ activeWorkspaceId: id });
  },

  fetchUser: async () => {
    try {
      const data = await apiRequest<any>('/auth/me');
      const wsList = data.workspaces || [];
      const currentWsId = get().activeWorkspaceId;
      const validWsId = wsList.some((w: any) => w.id === currentWsId)
        ? currentWsId
        : (wsList[0]?.id || null);

      if (validWsId) {
        localStorage.setItem('querymind_workspace_id', validWsId);
      }

      set({
        user: {
          id: data.id,
          name: data.name,
          email: data.email,
          status: data.status,
          created_at: data.created_at,
          workspace_id: validWsId,
        },
        workspaces: wsList,
        activeWorkspaceId: validWsId,
        isLoading: false,
      });
    } catch {
      set({ isLoading: false });
    }
  },
}));
