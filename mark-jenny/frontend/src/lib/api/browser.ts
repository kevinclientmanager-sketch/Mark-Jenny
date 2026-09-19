import { api } from './client';

export interface BrowserCapability {
  capability: { status: string; detail: string };
  playwright_installed: boolean;
  setup: string;
  persistent_login: string;
  sessions_active: number;
}

export const browserApi = {
  capability: async (): Promise<BrowserCapability> => api.get<BrowserCapability>('/browser/capability'),
  createSession: async (persistent=false): Promise<{session_id:string; persistent:boolean}> => api.post('/browser/sessions', { persistent }),
  listSessions: async (): Promise<any[]> => api.get('/browser/sessions'),
  closeSession: async (id:string): Promise<any> => api.delete(`/browser/sessions/${id}`),
  navigate: async (data:{url:string; session_id?:string; persistent?:boolean}): Promise<any> => api.post('/browser/navigate', data),
  search: async (data:{query:string; engine?:string; session_id?:string}): Promise<any> => api.post('/browser/search', data),
  click: async (data:{selector:string; session_id:string}): Promise<any> => api.post('/browser/click', data),
  type: async (data:{selector:string; text:string; session_id:string}): Promise<any> => api.post('/browser/type', data),
  scroll: async (session_id:string, y?:number): Promise<any> => api.post(`/browser/scroll?session_id=${session_id}&y=${y||500}`, {}),
  read: async (session_id:string): Promise<any> => api.post(`/browser/read?session_id=${session_id}`, {}),
  extract: async (data:{selector:string; attribute?:string; session_id:string}): Promise<any> => api.post('/browser/extract', data),
};
