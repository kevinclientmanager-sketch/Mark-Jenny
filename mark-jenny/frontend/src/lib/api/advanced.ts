import { api } from './client';
export const advancedApi = {
  selfCheck: async (taskId: number): Promise<any> => api.post(`/advanced/self-check/${taskId}`, {}),
  saveCheckpoint: async (taskId: number, step: number, state: any): Promise<any> => api.post(`/advanced/checkpoint/${taskId}`, { step, state }),
  listCheckpoints: async (taskId: number): Promise<any> => api.get(`/advanced/checkpoint/${taskId}`),
  restoreCheckpoint: async (taskId: number, idx: number): Promise<any> => api.post(`/advanced/checkpoint/${taskId}/restore/${idx}`, {}),
  recover: async (taskId: number, error: string, attempt?: number): Promise<any> => api.post(`/advanced/recover/${taskId}?error=${encodeURIComponent(error)}&attempt=${attempt||0}`, {}),
  delegate: async (taskId: number, subtasks: any[]): Promise<any> => api.post(`/advanced/delegate/${taskId}`, subtasks),
  verify: async (taskId: number, results: any[]): Promise<any> => api.post(`/advanced/verify/${taskId}`, results),
  createMemory: async (data: { type: string; content: string; project_id?: number; task_id?: number }): Promise<any> => api.post('/advanced/memory', data),
  getFailures: async (): Promise<any> => api.get('/advanced/memory/failures'),
  listAgents: async (): Promise<any> => api.get('/advanced/agents/specialized'),
};
