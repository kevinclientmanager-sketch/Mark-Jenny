import { api } from './client';

export interface Knowledge {
  id: number;
  name: string;
  use_when: string | null;
  content: string;
  enabled: boolean;
  project_id: number | null;
  project_name: string | null;
  owner_id: number | null;
  source: string | null;
  confidence: number | null;
  importance: number | null;
  tags: string[] | null;
  created_at: string;
  updated_at: string | null;
}

export interface KnowledgeListResponse {
  knowledge: Knowledge[];
  total: number;
  page: number;
  page_size: number;
}

export const knowledgeApi = {
  list: async (params?: { page?: number; page_size?: number; search?: string; project_id?: number; enabled?: boolean; sort_by?: string; sort_order?: string }): Promise<KnowledgeListResponse> => {
    const sp = new URLSearchParams();
    if (params) Object.entries(params).forEach(([k,v])=>{ if(v!==undefined && v!==null) sp.set(k, String(v)); });
    return api.get<KnowledgeListResponse>(`/knowledge?${sp.toString()}`);
  },
  create: async (data: { name: string; use_when?: string; content: string; enabled?: boolean; project_id?: number; source?: string; confidence?: number; importance?: number; tags?: string[] }): Promise<Knowledge> => api.post<Knowledge>('/knowledge', data),
  update: async (id: number, data: Partial<{ name: string; use_when: string; content: string; enabled: boolean; project_id: number | null; source: string; confidence: number; importance: number; tags: string[] }>): Promise<Knowledge> => api.patch<Knowledge>(`/knowledge/${id}`, data),
  delete: async (id: number): Promise<{message:string}> => api.delete<{message:string}>(`/knowledge/${id}`),
  toggle: async (id: number): Promise<Knowledge> => api.post<Knowledge>(`/knowledge/${id}/toggle`, {}),
};
