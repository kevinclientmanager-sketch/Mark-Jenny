import { api, ApiError } from './client';

export interface Project {
  id: number;
  name: string;
  description: string | null;
  icon: string | null;
  avatar_url: string | null;
  instructions: string | null;
  status: string;
  owner_id: number;
  task_count: number;
  file_count: number;
  skill_count: number;
  last_modified: string | null;
  running_status: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface ProjectListResponse {
  projects: Project[];
  total: number;
  page: number;
  page_size: number;
}

export interface CreateProjectData {
  name: string;
  description?: string;
  icon?: string;
  instructions?: string;
}

export interface UpdateProjectData {
  name?: string;
  description?: string;
  icon?: string;
  instructions?: string;
  status?: string;
}

export interface ProjectSkill {
  id: number;
  name: string;
  display_name: string | null;
  description: string | null;
  version: string;
  source: string;
  status: string;
  enabled: boolean;
  config: Record<string, unknown> | null;
  last_updated: string | null;
}

export const projectsApi = {
  list: async (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    status?: string;
    sort_by?: string;
    sort_order?: string;
  }): Promise<ProjectListResponse> => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value));
        }
      });
    }
    return api.get<ProjectListResponse>(`/projects?${searchParams.toString()}`);
  },

  get: async (id: number): Promise<Project> => {
    return api.get<Project>(`/projects/${id}`);
  },

  create: async (data: CreateProjectData): Promise<Project> => {
    return api.post<Project>('/projects', data);
  },

  update: async (id: number, data: UpdateProjectData): Promise<Project> => {
    return api.patch<Project>(`/projects/${id}`, data);
  },

  delete: async (id: number): Promise<{ message: string }> => {
    return api.delete<{ message: string }>(`/projects/${id}`);
  },

  duplicate: async (id: number): Promise<Project> => {
    return api.post<Project>(`/projects/${id}/duplicate`, {});
  },

  listSkills: async (projectId: number): Promise<ProjectSkill[]> => {
    return api.get<ProjectSkill[]>(`/projects/${projectId}/skills`);
  },

  addSkill: async (projectId: number, skillId: number, enabled = true, config?: Record<string, unknown>): Promise<{ message: string }> => {
    return api.post<{ message: string }>(`/projects/${projectId}/skills`, { skill_id: skillId, enabled, config });
  },

  updateSkill: async (projectId: number, skillId: number, enabled: boolean, config?: Record<string, unknown>): Promise<{ message: string }> => {
    return api.patch<{ message: string }>(`/projects/${projectId}/skills/${skillId}`, { enabled, config });
  },

  removeSkill: async (projectId: number, skillId: number): Promise<{ message: string }> => {
    return api.delete<{ message: string }>(`/projects/${projectId}/skills/${skillId}`);
  },
};