import { api } from './client';

export const computerApi = {
  info: async (): Promise<any> => api.get('/computer/info'),
  listFiles: async (path?: string): Promise<any> => api.get(`/computer/files?path=${encodeURIComponent(path||".")}`),
  readFile: async (path: string): Promise<any> => api.get(`/computer/files/read?path=${encodeURIComponent(path)}`),
  writeFile: async (path:string, content:string): Promise<any> => api.post('/computer/files/write', { path, content, require_confirm:false }),
  listProcesses: async (limit?:number): Promise<any> => api.get(`/computer/processes?limit=${limit||50}`),
  killProcess: async (pid:number): Promise<any> => api.post(`/computer/processes/${pid}/kill?confirm=true`, {}),
  clipboardRead: async (): Promise<any> => api.get('/computer/clipboard'),
  clipboardWrite: async (text:string): Promise<any> => api.post('/computer/clipboard', { text }),
  listWindows: async (): Promise<any> => api.get('/computer/windows'),
  permissions: async (): Promise<any> => api.get('/computer/permissions'),
};
