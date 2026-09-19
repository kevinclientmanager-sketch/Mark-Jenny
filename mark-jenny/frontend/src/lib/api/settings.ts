import { api } from './client';
export const settingsApi = {
  get: async (category?: string): Promise<any> => api.get(`/settings${category?`?category=${category}`:""}`),
  update: async (category: string, data: any): Promise<any> => api.patch('/settings', { category, data }),
  clearCache: async (): Promise<any> => api.post('/settings/clear-cache', {}),
  dataControls: async (): Promise<any> => api.get('/settings/data-controls/overview'),
  cloudBrowserGet: async (): Promise<any> => api.get('/settings/cloud-browser'),
  cloudBrowserUpdate: async (data:any): Promise<any> => api.patch('/settings/cloud-browser', data),
  mailGet: async (): Promise<any> => api.get('/settings/mail'),
  mailUpdate: async (data:any): Promise<any> => api.patch('/settings/mail', data),
  mailInbox: async (): Promise<any> => api.get('/settings/mail/inbox'),
  mailExecute: async (id:number): Promise<any> => api.post(`/settings/mail/inbox/${id}/execute`, {}),
};
export const adminApi = {
  listUsers: async (params?:any): Promise<any> => {
    const sp=new URLSearchParams(); if(params) Object.entries(params).forEach(([k,v])=>{ if(v!==undefined) sp.set(k,String(v)); });
    return api.get(`/admin/users?${sp.toString()}`);
  },
  getUser: async (id:number): Promise<any> => api.get(`/admin/users/${id}`),
  setRole: async (id:number, role:string): Promise<any> => api.patch(`/admin/users/${id}/role`, { role }),
  blacklist: async (id:number): Promise<any> => api.post(`/admin/users/${id}/blacklist`, {}),
  getBlacklist: async (): Promise<any> => api.get('/admin/blacklist'),
  getFlags: async (): Promise<any> => api.get('/admin/feature-flags'),
  setFlag: async (flag:string, enabled:boolean): Promise<any> => api.patch('/admin/feature-flags', { flag, enabled }),
  getAudit: async (): Promise<any> => api.get('/admin/audit-logs'),
  getSystem: async (): Promise<any> => api.get('/admin/system/config'),
  getAccess: async (): Promise<any> => api.get('/admin/access-control'),
};
