import { create } from 'zustand';
import { DatabaseConnection } from '../types';
import { apiRequest } from '../api/client';

interface ConnectionState {
  connections: DatabaseConnection[];
  activeConnectionId: string | null;
  isLoading: boolean;
  error: string | null;
  fetchConnections: () => Promise<void>;
  setActiveConnection: (id: string) => void;
}

export const useConnectionStore = create<ConnectionState>((set, get) => ({
  connections: [],
  activeConnectionId: localStorage.getItem('querymind_active_connection'),
  isLoading: false,
  error: null,

  fetchConnections: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await apiRequest<DatabaseConnection[]>('/connections');
      const list = data || [];
      const currentActive = get().activeConnectionId;
      const validActive = list.some(c => c.id === currentActive)
        ? currentActive
        : (list[0]?.id || null);

      if (validActive) {
        localStorage.setItem('querymind_active_connection', validActive);
      } else {
        localStorage.removeItem('querymind_active_connection');
      }

      set({
        connections: list,
        activeConnectionId: validActive,
        isLoading: false,
      });
    } catch (e: any) {
      set({ error: e.message, isLoading: false });
    }
  },

  setActiveConnection: (id: string) => {
    localStorage.setItem('querymind_active_connection', id);
    set({ activeConnectionId: id });
  },
}));

