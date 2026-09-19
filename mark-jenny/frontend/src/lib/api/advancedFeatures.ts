import { api } from './client';
export const advancedFeaturesApi = {
  saveBlueprint: async (taskId:number): Promise<any> => api.post(`/advanced/blueprints/${taskId}`, {}),
  listBlueprints: async (projectId?:number): Promise<any> => api.get(`/advanced/blueprints${projectId?`?project_id=${projectId}`:""}`),
  heal: async (taskId:number, error:string): Promise<any> => api.post(`/advanced/heal/${taskId}`, { error }),
  simulate: async (prompt:string, project_id?:number): Promise<any> => api.post('/advanced/simulate', { prompt, project_id }),
  dryRun: async (prompt:string, project_id?:number): Promise<any> => api.post('/advanced/dry-run', { prompt, project_id }),
  listPendingApprovals: async (): Promise<any> => api.get('/advanced/approvals/pending'),
  approve: async (id:number, reason?:string): Promise<any> => api.post(`/advanced/approvals/${id}/approve`, { reason }),
  reject: async (id:number, reason?:string): Promise<any> => api.post(`/advanced/approvals/${id}/reject`, { reason }),
  timeline: async (taskId:number): Promise<any> => api.get(`/advanced/timeline/${taskId}`),
  createSnapshot: async (projectId:number, name:string): Promise<any> => api.post(`/advanced/snapshots/${projectId}`, { name }),
  listSnapshots: async (projectId:number): Promise<any> => api.get(`/advanced/snapshots/${projectId}`),
  restoreSnapshot: async (projectId:number, snapshotId:string): Promise<any> => api.post(`/advanced/snapshots/${projectId}/restore/${snapshotId}`, {}),
  diffSnapshots: async (projectId:number, id1:string, id2:string): Promise<any> => api.get(`/advanced/snapshots/${projectId}/diff?id1=${id1}&id2=${id2}`),
  validateDependency: async (skill:any, available:string[]): Promise<any> => api.post('/advanced/skill-dependency/validate', { skill, available_skills: available }),
  knowledgeGraph: async (projectId?:number): Promise<any> => api.get(`/advanced/knowledge-graph${projectId?`?project_id=${projectId}`:""}`),
  rateLimit: async (): Promise<any> => api.get('/advanced/security/rate-limit'),
};
