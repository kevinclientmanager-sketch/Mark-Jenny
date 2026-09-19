import { api } from './client';

export interface QuickAction {
  id: string;
  label: string;
  desc: string;
  icon: string;
  category: string;
  route?: string | null;
  needs_file: boolean;
}

export const quickActionsApi = {
  list: async (): Promise<QuickAction[]> => api.get<QuickAction[]>('/quick-actions'),
  get: async (id: string): Promise<QuickAction> => api.get<QuickAction>(`/quick-actions/${id}`),
  execute: async (id: string, data: { prompt: string; project_id?: number; file_ids?: number[]; connectors?: number[] }): Promise<{message:string; task_id?: number; route?: string; action_id: string; status?: string; title?: string}> => {
    return api.post(`/quick-actions/${id}/execute`, data);
  },
};
