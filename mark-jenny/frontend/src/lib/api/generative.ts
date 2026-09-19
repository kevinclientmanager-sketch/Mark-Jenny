import { api } from './client';

export interface GenerateResult {
  task_id: number;
  type: string;
  files: { id: number; name: string; path: string; size: number }[];
  message: string;
  preview_url?: string | null;
}

export const generativeApi = {
  types: async (): Promise<{id:string; label:string; desc:string; icon:string}[]> => api.get('/generate/types'),
  website: async (data:{prompt:string; project_id?:number}): Promise<GenerateResult> => api.post('/generate/website', data),
  app: async (data:{prompt:string; project_id?:number}): Promise<GenerateResult> => api.post('/generate/app', data),
  slides: async (data:{prompt:string; project_id?:number}): Promise<GenerateResult> => api.post('/generate/slides', data),
  image: async (data:{prompt:string; project_id?:number}): Promise<GenerateResult> => api.post('/generate/image', data),
  imageEdit: async (data:{prompt:string; project_id?:number}): Promise<GenerateResult> => api.post('/generate/image-edit', data),
  research: async (data:{prompt:string; project_id?:number}): Promise<GenerateResult> => api.post('/generate/research', data),
  spreadsheet: async (data:{prompt:string; project_id?:number}): Promise<GenerateResult> => api.post('/generate/spreadsheet', data),
  video: async (data:{prompt:string; project_id?:number}): Promise<GenerateResult> => api.post('/generate/video', data),
  audio: async (data:{prompt:string; project_id?:number}): Promise<GenerateResult> => api.post('/generate/audio', data),
  document: async (data:{prompt:string; project_id?:number}): Promise<GenerateResult> => api.post('/generate/document', data),
  code: async (data:{prompt:string; project_id?:number}): Promise<GenerateResult> => api.post('/generate/code', data),
  generate: async (type:string, data:{prompt:string; project_id?:number}): Promise<GenerateResult> => api.post(`/generate/${type}`, data),
};
