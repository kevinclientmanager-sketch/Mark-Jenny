import { api } from "./client";

export interface BuildSession {
  session_id?: string;
  id?: string;
  status?: string;
  phase?: string;
  user_request?: string;
  progress?: number;
  error?: string | null;
  [key: string]: unknown;
}

export const selfBuildApi = {
  start: (user_request: string) => api.post<{ session_id: string; message: string }>("/self-build/start", { user_request }),
  sessions: () => api.get<{ sessions: BuildSession[]; stats: Record<string, unknown> }>("/self-build/sessions"),
  session: (id: string) => api.get<BuildSession>(`/self-build/${id}`),
  logs: (id: string) => api.get<{ logs: Array<{ timestamp?: string; level?: string; message?: string; [key: string]: unknown }> }>(`/self-build/${id}/logs`),
  files: (id: string) => api.get<{ files: Array<{ path?: string; name?: string; size?: number; [key: string]: unknown }> }>(`/self-build/${id}/files`),
  integrate: (id: string) => api.post<Record<string, unknown>>(`/self-build/${id}/integrate`, {}),
  rollback: (id: string) => api.post<Record<string, unknown>>(`/self-build/${id}/rollback`, {}),
};

export const buildTargets = [
  { id: "web", label: "Web application", detail: "Next.js/PWA source, preview, production deployment" },
  { id: "android", label: "Android app", detail: "Package-ready Expo/React Native or Capacitor workspace" },
  { id: "windows", label: "Windows app", detail: "Package-ready Electron or Tauri desktop workspace" },
] as const;
