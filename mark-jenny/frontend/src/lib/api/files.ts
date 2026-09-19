import { api } from './client';

export type FileType = 'IMAGE' | 'DOCUMENT' | 'VIDEO' | 'AUDIO' | 'SPREADSHEET' | 'CODE' | 'ARCHIVE' | 'WEBSITE' | 'OTHER';

export interface File {
  id: number;
  name: string;
  original_name: string;
  path: string;
  storage_key: string | null;
  mime_type: string | null;
  file_type: FileType;
  size: number;
  hash: string | null;
  owner_id: number;
  project_id: number | null;
  task_id: number | null;
  folder_id: number | null;
  is_public: boolean;
  file_metadata: string | null;
  created_at: string;
  updated_at: string | null;
  deleted_at: string | null;
}

export interface FileListResponse {
  files: File[];
  total: number;
  page: number;
  page_size: number;
}

export interface Folder {
  id: number;
  name: string;
  path: string | null;
  parent_id: number | null;
  project_id: number | null;
  owner_id: number;
  children: Folder[];
  file_count: number;
  created_at: string;
  updated_at: string | null;
}

export interface CreateFolderData {
  name: string;
  parent_id?: number;
  project_id?: number;
}

export interface UpdateFolderData {
  name?: string;
  parent_id?: number;
}

export const filesApi = {
  listFiles: async (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    file_type?: FileType;
    project_id?: number;
    task_id?: number;
    folder_id?: number;
    sort_by?: string;
    sort_order?: string;
  }): Promise<FileListResponse> => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value));
        }
      });
    }
    return api.get<FileListResponse>(`/files?${searchParams.toString()}`);
  },

  getFile: async (id: number): Promise<File> => {
    return api.get<File>(`/files/${id}`);
  },

  updateFile: async (id: number, data: {
    name?: string;
    folder_id?: number;
    project_id?: number;
    is_public?: boolean;
  }): Promise<File> => {
    return api.patch<File>(`/files/${id}`, data);
  },

  deleteFile: async (id: number): Promise<{ message: string }> => {
    return api.delete<{ message: string }>(`/files/${id}`);
  },

  restoreFile: async (id: number): Promise<{ message: string }> => {
    return api.post<{ message: string }>(`/files/${id}/restore`, {});
  },

  downloadFile: async (id: number): Promise<Blob> => {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/files/${id}/download`, {
      credentials: 'include',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
      },
    });
    if (!response.ok) throw new Error('Download failed');
    return response.blob();
  },

  uploadFile: async (file: globalThis.File, options?: {
    project_id?: number;
    task_id?: number;
    folder_id?: number;
  }): Promise<File> => {
    const formData = new FormData();
    formData.append('file', file);
    if (options?.project_id) formData.append('project_id', String(options.project_id));
    if (options?.task_id) formData.append('task_id', String(options.task_id));
    if (options?.folder_id) formData.append('folder_id', String(options.folder_id));

    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/files/upload`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Upload failed');
    }

    return response.json();
  },

  listFolders: async (params?: {
    project_id?: number;
    parent_id?: number;
  }): Promise<Folder[]> => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value));
        }
      });
    }
    return api.get<Folder[]>(`/files/folders?${searchParams.toString()}`);
  },

  createFolder: async (data: CreateFolderData): Promise<Folder> => {
    return api.post<Folder>('/files/folders', data);
  },

  updateFolder: async (id: number, data: UpdateFolderData): Promise<Folder> => {
    return api.patch<Folder>(`/files/folders/${id}`, data);
  },

  deleteFolder: async (id: number): Promise<{ message: string }> => {
    return api.delete<{ message: string }>(`/files/folders/${id}`);
  },

  getCategories: async (): Promise<{ value: string; label: string }[]> => {
    return api.get<{ value: string; label: string }[]>('/files/types/categories');
  },
};