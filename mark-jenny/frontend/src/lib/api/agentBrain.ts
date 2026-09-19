import { api } from './client';

export interface BrainIntent {
  intent: string;
  confidence: number;
  signals: Record<string, number>;
  entities: { urls: string[]; dates: string[]; numbers: string[]; files: string[] };
  complexity: string;
  multi_step: boolean;
}

export interface BrainRecalled {
  kind: string;
  id: number;
  type: string;
  content: string;
  score: number;
}

export interface BrainSubtask {
  order: number;
  title: string;
  kind: string;
  tools: string[];
  skills: string[];
  depends_on: number[];
  acceptance: string;
}

export interface BrainThink {
  goal: string;
  intent: BrainIntent;
  recalled: BrainRecalled[];
  skills: { assigned: { name: string; display_name: string; score: number; tools: string[] }[]; gaps: string[] };
  model: { name: string; provider: string } | null;
  plan: { subtasks: BrainSubtask[]; context: string; strategy: string; estimated_steps: number };
  inventory: { code: string[]; browser: Record<string, unknown>; connectors: { name: string; status: string }[]; skills: number };
  trace: string[];
}

export interface BrainStep {
  order: number;
  title: string;
  action: string;
  passed: boolean;
  acceptance: string;
  observation: string;
  files: { id?: number; name: string; path?: string }[];
}

export interface BrainRun {
  goal: string;
  intent: BrainIntent;
  plan_strategy: string;
  steps: BrainStep[];
  artifacts: { id?: number; name: string }[];
  summary: string;
  recalled: BrainRecalled[];
  self_check: string;
}

export interface BrainInsights {
  failure_patterns: { pattern: string; count: number }[];
  memory_health: { memories: number; knowledge: number; preferences: number; skills: number };
  suggestions: string[];
}

export const agentBrainApi = {
  think: (goal: string, project_id?: number): Promise<BrainThink> =>
    api.post<BrainThink>('/agent-brain/think', { goal, project_id }),
  run: (goal: string, project_id?: number, max_iterations = 5): Promise<BrainRun> =>
    api.post<BrainRun>('/agent-brain/run', { goal, project_id, max_iterations }),
  insights: (): Promise<BrainInsights> => api.get<BrainInsights>('/agent-brain/insights'),
};
