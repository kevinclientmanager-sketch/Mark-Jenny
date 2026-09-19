import { api } from './client';

export interface ExecutionRequest { language: string; code: string; timeout?: number; project_id?: number; }
export interface ExecutionResult { success: boolean; language: string; stdout?: string; stderr?: string; returncode?: number; duration?: number; sandbox?: string; files?: any[]; error?: string; timeout?: boolean; }

export const executionApi = {
  capabilities: async (): Promise<any> => api.get('/execution/capabilities'),
  languages: async (): Promise<any> => api.get('/execution/languages'),
  run: async (data: ExecutionRequest): Promise<ExecutionResult> => api.post<ExecutionResult>('/execution/run', data),
  runPython: async (code:string, timeout?:number): Promise<ExecutionResult> => api.post<ExecutionResult>('/execution/python', { language:'python', code, timeout }),
  runJS: async (code:string, timeout?:number): Promise<ExecutionResult> => api.post<ExecutionResult>('/execution/javascript', { language:'javascript', code, timeout }),
  runPS: async (code:string, timeout?:number): Promise<ExecutionResult> => api.post<ExecutionResult>('/execution/powershell', { language:'powershell', code, timeout }),
};
