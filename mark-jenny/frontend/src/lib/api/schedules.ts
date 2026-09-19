import { api } from './client';

export type ScheduleFrequency = 'DAILY' | 'WEEKLY' | 'MONTHLY' | 'ONCE' | 'CRON';
export type ScheduleRunOption = 'SAME_TASK' | 'SEPARATE_TASK';

export interface ScheduleRun {
  id: number;
  schedule_id: number;
  task_id: number | null;
  status: string;
  error: string | null;
  started_at: string;
  completed_at: string | null;
  duration_seconds: number | null;
}

export interface Schedule {
  id: number;
  title: string;
  prompt: string;
  frequency: ScheduleFrequency;
  cron_expression: string | null;
  time_of_day: string;
  timezone: string;
  run_option: ScheduleRunOption;
  skip_confirmations: boolean;
  project_id: number | null;
  project_name: string | null;
  agent_id: number | null;
  agent_name: string | null;
  connectors: number[] | null;
  config: Record<string, unknown> | null;
  computer: string | null;
  is_active: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  end_date: string | null;
  run_count: number;
  max_runs: number | null;
  created_at: string;
  updated_at: string | null;
}

export interface ScheduleListResponse {
  schedules: Schedule[];
  total: number;
  page: number;
  page_size: number;
}

export interface CreateScheduleData {
  title: string;
  prompt: string;
  frequency?: ScheduleFrequency;
  cron_expression?: string;
  time_of_day: string;
  timezone?: string;
  run_option?: ScheduleRunOption;
  skip_confirmations?: boolean;
  project_id?: number;
  agent_id?: number;
  connectors?: number[];
  config?: Record<string, unknown>;
  computer?: string;
  end_date?: string;
  max_runs?: number;
}

export interface UpdateScheduleData {
  title?: string;
  prompt?: string;
  frequency?: ScheduleFrequency;
  cron_expression?: string;
  time_of_day?: string;
  timezone?: string;
  run_option?: ScheduleRunOption;
  skip_confirmations?: boolean;
  project_id?: number;
  agent_id?: number;
  connectors?: number[];
  config?: Record<string, unknown>;
  computer?: string;
  end_date?: string;
  max_runs?: number;
  is_active?: boolean;
}

export interface UpcomingSchedule {
  id: number;
  title: string;
  next_execution: string | null;
  frequency: string;
  status: string;
  project: string | null;
  agent: string | null;
  connectors: number[];
}

export const schedulesApi = {
  list: async (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    is_active?: boolean;
    project_id?: number;
    sort_by?: string;
    sort_order?: string;
  }): Promise<ScheduleListResponse> => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value));
        }
      });
    }
    return api.get<ScheduleListResponse>(`/schedules?${searchParams.toString()}`);
  },

  get: async (id: number): Promise<Schedule> => {
    return api.get<Schedule>(`/schedules/${id}`);
  },

  create: async (data: CreateScheduleData): Promise<Schedule> => {
    return api.post<Schedule>('/schedules', data);
  },

  update: async (id: number, data: UpdateScheduleData): Promise<Schedule> => {
    return api.patch<Schedule>(`/schedules/${id}`, data);
  },

  delete: async (id: number): Promise<{ message: string }> => {
    return api.delete<{ message: string }>(`/schedules/${id}`);
  },

  pause: async (id: number): Promise<{ message: string }> => {
    return api.post<{ message: string }>(`/schedules/${id}/pause`, {});
  },

  resume: async (id: number): Promise<{ message: string }> => {
    return api.post<{ message: string }>(`/schedules/${id}/resume`, {});
  },

  duplicate: async (id: number): Promise<Schedule> => {
    return api.post<Schedule>(`/schedules/${id}/duplicate`, {});
  },

  listRuns: async (scheduleId: number, page = 1, pageSize = 20): Promise<ScheduleRun[]> => {
    return api.get<ScheduleRun[]>(`/schedules/${scheduleId}/runs?page=${page}&page_size=${pageSize}`);
  },

  getUpcoming: async (limit = 10): Promise<UpcomingSchedule[]> => {
    return api.get<UpcomingSchedule[]>(`/schedules/upcoming/next?limit=${limit}`);
  },
};