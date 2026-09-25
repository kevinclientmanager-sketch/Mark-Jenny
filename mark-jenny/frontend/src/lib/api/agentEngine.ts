import { api } from './client';

export interface ProcessRequest {
  request: string;
  context?: Record<string, unknown>;
  use_multi_agent?: boolean;
  max_iterations?: number;
}

export interface AgentStep {
  id: string;
  step_number: number;
  action: string;
  tool: string | null;
  input_data: Record<string, unknown>;
  output_data: Record<string, unknown> | null;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  error: string | null;
  retry_count: number;
}

export interface ProcessResult {
  status: string;
  task_id: string;
  complexity: string;
  iterations: number;
  steps: AgentStep[];
  timeline: Array<{ timestamp: string; action: string; detail: string }>;
  verification: {
    all_passed: boolean;
    results: Array<{ step_id: string; passed: boolean; reason: string }>;
    needs_correction: boolean;
  };
}

export interface SandboxExecRequest {
  code: string;
  language?: string;
  context?: Record<string, unknown>;
}

export interface SandboxResult {
  status: string;
  execution_id: string;
  exit_code: number;
  stdout: string;
  stderr: string;
  duration_ms: number;
  execution_status: string;
}

export interface RouteResult {
  status: string;
  routing: {
    domain: string;
    model: string | null;
    model_id: string | null;
    provider: string | null;
    score: number;
    alternatives: Array<{ model: string; model_id: string }>;
  };
}

export interface DecomposeResult {
  status: string;
  nodes: number;
  execution_order: string[];
  graph: string;
}

export interface ProactiveSuggestion {
  id: string;
  trigger: string;
  message: string;
  actions: string[];
  confidence: number;
}

export const agentEngineApi = {
  process: (req: ProcessRequest) =>
    api.post<ProcessResult>('/agent-engine/process', req),

  sandboxExecute: (req: SandboxExecRequest) =>
    api.post<SandboxResult>('/agent-engine/sandbox/execute', req),

  sandboxBrowse: (url: string) =>
    api.post<{ status: string; data: unknown }>('/agent-engine/sandbox/browse', { url }),

  route: (text: string, preferences?: Record<string, unknown>) =>
    api.post<RouteResult>('/agent-engine/route', { text, preferences: preferences || {} }),

  decompose: (request: string) =>
    api.post<DecomposeResult>('/agent-engine/decompose', { request }),

  proactiveEvaluate: (context: Record<string, unknown>) =>
    api.post<{ status: string; suggestions: ProactiveSuggestion[] }>('/agent-engine/proactive/evaluate', { context }),

  proactiveActive: () =>
    api.get<{ status: string; count: number; suggestions: ProactiveSuggestion[] }>('/agent-engine/proactive/active'),

  proactiveDismiss: (id: string) =>
    api.post<{ status: string }>(`/agent-engine/proactive/dismiss/${id}`, {}),

  routerStats: () =>
    api.get<{ status: string; stats: unknown }>('/agent-engine/router/stats'),

  routerClassify: (text: string) =>
    api.get<{ status: string; domain: string }>(`/agent-engine/router/classify?text=${encodeURIComponent(text)}`),
};
