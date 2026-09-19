import { api } from './client';

export type SkillSource = 'OFFICIAL' | 'UPLOADED' | 'GITHUB' | 'CREATED_BY_MARK';
export type SkillStatus = 'INSTALLED' | 'ENABLED' | 'DISABLED' | 'ERROR' | 'UPDATING' | 'NOT_INSTALLED';

export interface Skill {
  id: number;
  name: string;
  display_name: string | null;
  description: string | null;
  version: string;
  source: SkillSource;
  source_url: string | null;
  status: string;
  manifest: Record<string, any> | null;
  instructions: string | null;
  tools: string[] | null;
  permissions: string[] | null;
  config_schema: Record<string, any> | null;
  default_config: Record<string, any> | null;
  dependencies: string[] | null;
  owner_id: number | null;
  created_at: string;
  updated_at: string | null;
  installed_at: string | null;
}

export interface SkillListResponse {
  skills: Skill[];
  total: number;
  page: number;
  page_size: number;
}

export const skillsApi = {
  list: async (params?: { page?: number; page_size?: number; search?: string; source?: SkillSource; status?: string }): Promise<SkillListResponse> => {
    const sp = new URLSearchParams();
    if (params) Object.entries(params).forEach(([k,v])=>{ if(v!==undefined && v!==null) sp.set(k, String(v)); });
    return api.get<SkillListResponse>(`/skills?${sp.toString()}`);
  },
  official: async (): Promise<Skill[]> => api.get<Skill[]>('/skills/official'),
  installOfficial: async (name: string): Promise<Skill> => api.post<Skill>(`/skills/official/${name}/install`, {}),
  upload: async (file: File): Promise<Skill> => {
    const fd = new FormData(); fd.append('file', file);
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/skills/upload`, { method:'POST', headers:{ Authorization:`Bearer ${localStorage.getItem('access_token')}`}, body: fd, credentials:'include' });
    if(!res.ok) throw new Error((await res.json()).detail || 'Upload failed');
    return res.json();
  },
  importGithub: async (url: string): Promise<Skill> => api.post<Skill>('/skills/github', { url }),
  build: async (prompt: string, project_id?: number): Promise<Skill> => api.post<Skill>('/skills/build', { prompt, project_id }),
  validate: async (pkg: any): Promise<{valid:boolean; errors:string[]}> => api.post('/skills/validate', { package: pkg }),
  get: async (id: number): Promise<Skill> => api.get<Skill>(`/skills/${id}`),
  enable: async (id: number): Promise<Skill> => api.post<Skill>(`/skills/${id}/enable`, {}),
  disable: async (id: number): Promise<Skill> => api.post<Skill>(`/skills/${id}/disable`, {}),
  configure: async (id: number, config: any): Promise<Skill> => api.post<Skill>(`/skills/${id}/configure`, config),
  updateVersion: async (id: number, data: any): Promise<Skill> => api.post<Skill>(`/skills/${id}/update`, data),
  rollback: async (id: number): Promise<Skill> => api.post<Skill>(`/skills/${id}/rollback`, {}),
  remove: async (id: number): Promise<{message:string}> => api.delete(`/skills/${id}`),
  versions: async (id: number): Promise<any[]> => api.get(`/skills/${id}/versions`),

  // Self-Builder: Discover & Auto-Install
  discover: async (params: { query?: string; url?: string; auto_install?: boolean }): Promise<{
    skills: Array<{name:string; display_name:string; description:string; source_repo:string; source_url:string; tools:string[]; category:string; origin:string}>;
    repos: Array<{full_name:string; description:string; stars:number; url:string}>;
    installed: number;
    message: string;
  }> => api.post('/skills/discover', params),
  autoInstall: async (skills: string[]): Promise<{installed: number; message: string}> => api.post('/skills/auto-install', { skills }),
  fillGaps: async (): Promise<{filled: number; gaps: string[]; message: string}> => api.post('/skills/fill-gaps', {}),
  importLocal: async (directory: string, limit?: number): Promise<{imported: number; errors: string[]; message: string}> => api.post('/skills/import-local', { directory, limit: limit || 50 }),
};
