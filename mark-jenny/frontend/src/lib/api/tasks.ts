import { api } from './client';

export type TaskStatus = 'PENDING' | 'PLANNING' | 'RUNNING' | 'WAITING_APPROVAL' | 'PAUSED' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
export type TaskPriority = 'LOW' | 'NORMAL' | 'HIGH' | 'CRITICAL';

export interface Subtask {
  id: number;
  task_id: number;
  title: string;
  description: string | null;
  status: TaskStatus;
  order: number;
  assigned_agent: string | null;
  required_skills: string[] | null;
  required_tools: string[] | null;
  result: Record<string, unknown> | null;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface TaskRun {
  id: number;
  task_id: number;
  run_number: number;
  status: TaskStatus;
  plan: Record<string, unknown> | null;
  steps_completed: number;
  tool_calls: Record<string, unknown>[] | null;
  model_usage: Record<string, unknown> | null;
  files_created: Record<string, unknown>[] | null;
  errors: Record<string, unknown>[] | null;
  started_at: string;
  completed_at: string | null;
  duration_seconds: number | null;
}

export interface Task {
  id: number;
  title: string;
  description: string | null;
  original_request: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  autonomy_level: number;
  owner_id: number;
  project_id: number | null;
  project_name: string | null;
  parent_task_id: number | null;
  plan: Record<string, unknown> | null;
  current_step: number;
  total_steps: number;
  model_used: string | null;
  agent_type: string | null;
  result: Record<string, unknown> | null;
  error: string | null;
  subtasks: Subtask[];
  runs: TaskRun[];
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface TaskListResponse {
  tasks: Task[];
  total: number;
  page: number;
  page_size: number;
}

export interface CreateTaskData {
  title: string;
  description?: string;
  original_request?: string;
  project_id?: number;
  priority?: TaskPriority;
  autonomy_level?: number;
}

export interface UpdateTaskData {
  title?: string;
  description?: string;
  priority?: TaskPriority;
  autonomy_level?: number;
  status?: TaskStatus;
}

export interface ExecuteTaskData {
  prompt: string;
  project_id?: number;
  agent_type?: string;
  model_preference?: string;
  autonomy_level?: number;
  skip_confirmations?: boolean;
}

export const tasksApi = {
  list: async (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    status?: TaskStatus;
    priority?: TaskPriority;
    project_id?: number;
    sort_by?: string;
    sort_order?: string;
  }): Promise<TaskListResponse> => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value));
        }
      });
    }
    return api.get<TaskListResponse>(`/tasks?${searchParams.toString()}`);
  },

  get: async (id: number): Promise<Task> => {
    return api.get<Task>(`/tasks/${id}`);
  },

  create: async (data: CreateTaskData): Promise<Task> => {
    return api.post<Task>('/tasks', data);
  },

  update: async (id: number, data: UpdateTaskData): Promise<Task> => {
    return api.patch<Task>(`/tasks/${id}`, data);
  },

  delete: async (id: number): Promise<{ message: string }> => {
    return api.delete<{ message: string }>(`/tasks/${id}`);
  },

  execute: async (id: number, data: ExecuteTaskData): Promise<{ message: string; task_id: number }> => {
    return api.post<{ message: string; task_id: number }>(`/tasks/${id}/execute`, data);
  },

  pause: async (id: number): Promise<{ message: string }> => {
    return api.post<{ message: string }>(`/tasks/${id}/pause`, {});
  },

  resume: async (id: number): Promise<{ message: string }> => {
    return api.post<{ message: string }>(`/tasks/${id}/resume`, {});
  },

  cancel: async (id: number): Promise<{ message: string }> => {
    return api.post<{ message: string }>(`/tasks/${id}/cancel`, {});
  },

  retry: async (id: number): Promise<{ message: string }> => {
    return api.post<{ message: string }>(`/tasks/${id}/retry`, {});
  },

  listRuns: async (taskId: number): Promise<TaskRun[]> => {
    return api.get<TaskRun[]>(`/tasks/${taskId}/runs`);
  },

  getRun: async (taskId: number, runId: number): Promise<TaskRun> => {
    return api.get<TaskRun>(`/tasks/${taskId}/runs/${runId}`);
  },
};