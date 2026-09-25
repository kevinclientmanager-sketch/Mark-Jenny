import { api } from './client';

export interface WorkTask {
  id: string;
  type: string;
  description: string;
  status: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  requires_approval: boolean;
  result?: Record<string, unknown>;
}

export interface WorkPattern {
  id: string;
  type: string;
  trigger: string;
  action: string;
  frequency: number;
  confidence: number;
  last_seen: string;
}

export interface WorkRecord {
  id: string;
  task_type: string;
  description: string;
  outcome: string;
  timestamp: string;
  duration: number;
}

export interface Prediction {
  need: string;
  confidence: number;
  suggestion: string;
  pattern_id?: string;
}

export const workAgentApi = {
  getTasks: () =>
    api.get<{ status: string; pending: WorkTask[]; active: WorkTask[]; completed: WorkTask[] }>('/work-agent/tasks'),

  createTask: (taskType: string, description: string, params?: Record<string, unknown>, requiresApproval?: boolean) =>
    api.post<{ status: string; task: WorkTask }>('/work-agent/tasks', {
      task_type: taskType,
      description,
      params: params || {},
      requires_approval: requiresApproval !== false,
    }),

  approveTask: (taskId: string) =>
    api.post<{ status: string }>(`/work-agent/tasks/${taskId}/approve`, {}),

  completeTask: (taskId: string, result?: Record<string, unknown>) =>
    api.post<{ status: string }>(`/work-agent/tasks/${taskId}/complete`, result || {}),

  failTask: (taskId: string, error?: string) =>
    api.post<{ status: string }>(`/work-agent/tasks/${taskId}/fail`, { error: error || 'Unknown error' }),

  fileAction: (action: string, params?: Record<string, unknown>) =>
    api.post<{ status: string; result: unknown }>('/work-agent/files', { action, params: params || {} }),

  draftEmail: (to: string, subject: string, context: string, tone?: string) =>
    api.post<{ status: string; result: unknown }>('/work-agent/email/draft', { to, subject, context, tone: tone || 'professional' }),

  readEmail: () =>
    api.get<{ status: string; result: unknown }>('/work-agent/email/read'),

  getPatterns: () =>
    api.get<{ status: string; patterns: WorkPattern[] }>('/work-agent/patterns'),

  learnPattern: (trigger: string, action: string) =>
    api.post<{ status: string }>(`/work-agent/patterns/learn?trigger=${encodeURIComponent(trigger)}&action=${encodeURIComponent(action)}`, {}),

  predict: () =>
    api.get<{ status: string; predictions: Prediction[] }>('/work-agent/predict'),

  getRecords: (limit?: number) =>
    api.get<{ status: string; records: WorkRecord[] }>(`/work-agent/records${limit ? `?limit=${limit}` : ''}`),

  getStats: () =>
    api.get<{ status: string; stats: Record<string, number> }>('/work-agent/stats'),
};
