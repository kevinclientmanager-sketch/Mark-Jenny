import { api } from './client';

export type MemoryType = 'WORKING' | 'SHORT_TERM' | 'EPISODIC' | 'SEMANTIC' | 'PROCEDURAL' | 'PROJECT' | 'USER_PREFERENCE' | 'TASK' | 'FAILURE';

export interface Memory {
  id: number;
  type: MemoryType;
  content: string;
  source: string | null;
  confidence: number | null;
  importance: number | null;
  enabled: boolean;
  owner_id: number;
  project_id: number | null;
  project_name: string | null;
  task_id: number | null;
  memory_metadata: Record<string, any> | null;
  created_at: string;
  updated_at: string | null;
}

export interface MemoryListResponse {
  memories: Memory[];
  total: number;
  page: number;
  page_size: number;
}

export const memoryApi = {
  list: async (params?: { page?: number; page_size?: number; search?: string; type?: MemoryType; project_id?: number; task_id?: number; enabled?: boolean; sort_by?: string; sort_order?: string }): Promise<MemoryListResponse> => {
    const sp = new URLSearchParams();
    if (params) Object.entries(params).forEach(([k,v])=>{ if(v!==undefined && v!==null) sp.set(k, String(v)); });
    return api.get<MemoryListResponse>(`/memories?${sp.toString()}`);
  },
  create: async (data: { type: MemoryType; content: string; source?: string; confidence?: number; importance?: number; enabled?: boolean; project_id?: number; task_id?: number; memory_metadata?: Record<string,any> }): Promise<Memory> => api.post<Memory>('/memories', data),
  update: async (id: number, data: Partial<{ type: MemoryType; content: string; source: string; confidence: number; importance: number; enabled: boolean; project_id: number | null; task_id: number | null; memory_metadata: Record<string,any> }>): Promise<Memory> => api.patch<Memory>(`/memories/${id}`, data),
  delete: async (id: number): Promise<{message:string}> => api.delete<{message:string}>(`/memories/${id}`),
  toggle: async (id: number): Promise<Memory> => api.post<Memory>(`/memories/${id}/toggle`, {}),
  types: async (): Promise<{value:string; label:string}[]> => api.get<{value:string; label:string}[]>('/memories/types/list'),
};
