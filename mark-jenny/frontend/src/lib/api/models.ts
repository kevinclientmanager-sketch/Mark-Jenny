import { api } from './client';

export type ModelProvider = 'OPENAI' | 'ANTHROPIC' | 'GOOGLE' | 'OLLAMA' | 'AZURE' | 'CUSTOM';
export type ModelCapability = 'CHAT' | 'REASONING' | 'CODING' | 'VISION' | 'IMAGE_GENERATION' | 'AUDIO' | 'VIDEO' | 'EMBEDDINGS';

export interface AIModel {
  id: number;
  name: string;
  display_name: string | null;
  provider: ModelProvider;
  model_id: string;
  capabilities: string[] | null;
  context_window: number | null;
  max_output_tokens: number | null;
  cost_per_1k_input: number | null;
  cost_per_1k_output: number | null;
  is_local: boolean;
  is_active: boolean;
  config: Record<string, any> | null;
  created_at: string;
}

export interface ProviderConfig {
  id: number;
  provider: string;
  base_url: string | null;
  has_key: boolean;
  is_default: boolean;
  created_at: string;
}

export interface ProviderCatalogEntry {
  provider: string;
  label: string;
  free_tier: boolean;
  api_base: string | null;
  signup_url: string;
  note: string;
  discovery: boolean;
}

export interface Agent {
  id: number;
  name: string;
  type: string;
  description: string | null;
  system_prompt: string | null;
  model_id: number | null;
  model_name: string | null;
  available_tools: string[] | null;
  available_skills: string[] | null;
  config: Record<string, any> | null;
  is_active: boolean;
  created_at: string;
}

export const modelsApi = {
  listModels: async (params?: { provider?: string; is_local?: boolean; capability?: string }): Promise<AIModel[]> => {
    const sp = new URLSearchParams();
    if (params) Object.entries(params).forEach(([k,v])=>{ if(v!==undefined && v!==null) sp.set(k, String(v)); });
    return api.get<AIModel[]>(`/ai/models?${sp.toString()}`);
  },
  createModel: async (data: any): Promise<AIModel> => api.post<AIModel>('/ai/models', data),
  getModel: async (id:number): Promise<AIModel> => api.get<AIModel>(`/ai/models/${id}`),
  updateModel: async (id:number, data:any): Promise<AIModel> => api.patch<AIModel>(`/ai/models/${id}`, data),
  deleteModel: async (id:number): Promise<any> => api.delete(`/ai/models/${id}`),
  listProviders: async (): Promise<ProviderConfig[]> => api.get<ProviderConfig[]>('/ai/providers'),
  providerCatalog: async (): Promise<{ providers: ProviderCatalogEntry[]; note: string }> => api.get('/ai/providers/catalog'),
  refreshModels: async (provider?: string): Promise<{ report: any; total_models: number }> =>
    api.get(`/ai/models/refresh${provider ? `?provider=${provider}` : ''}`),
  upsertProvider: async (data: { provider: ModelProvider; api_key?: string; base_url?: string; config?: any; is_default?: boolean }): Promise<ProviderConfig> => api.post<ProviderConfig>('/ai/providers', data),
  testProvider: async (data: { provider: ModelProvider; api_key?: string; base_url?: string; model?: string }): Promise<{ ok: boolean; provider: string; model?: string; status_code?: number; detail: string }> => api.post('/ai/providers/test', data),
  selectModel: async (provider: ModelProvider, model: string): Promise<ProviderConfig> => api.post<ProviderConfig>('/ai/providers', { provider, config: { model }, is_default: true }),
  deleteProvider: async (provider: string): Promise<any> => api.delete(`/ai/providers/${provider}`),
  listAgents: async (): Promise<Agent[]> => api.get<Agent[]>('/ai/agents'),
  createAgent: async (data:any): Promise<Agent> => api.post<Agent>('/ai/agents', data),
  route: async (data: { task_type: string; prompt?: string; prefer_local?: boolean; prefer_cheap?: boolean; require_capabilities?: string[] }): Promise<any> => api.post('/ai/route', data),
  plan: async (data: { user_request: string; project_id?: number; task_type?: string }): Promise<any> => api.post('/ai/plan', data),
  capabilities: async (): Promise<any> => api.get('/ai/capabilities/list'),
};
