"use client";
import { useState } from "react";
import { ChevronDown, ChevronRight, CheckCircle2, XCircle, Loader2, Terminal, Code, Globe, Database, Shield, Wrench, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

type StepStatus = "running" | "done" | "failed" | "skipped";

interface ConsoleStep {
  label: string;
  status: StepStatus;
  detail?: string;
  code?: string;
  lang?: string;
  output?: string;
  duration_ms?: number;
  tool?: string;
}

interface ToolConsoleProps {
  steps: ConsoleStep[];
  title?: string;
  strategy?: string;
  model?: string;
  compact?: boolean;
}

const STATUS_ICONS: Record<StepStatus, typeof Loader2> = {
  running: Loader2,
  done: CheckCircle2,
  failed: XCircle,
  skipped: ChevronRight,
};

const STATUS_COLORS: Record<StepStatus, string> = {
  running: "text-blue-500",
  done: "text-emerald-500",
  failed: "text-red-500",
  skipped: "text-zinc-400",
};

const TOOL_ICONS: Record<string, typeof Wrench> = {
  web_search: Globe,
  browser_navigate: Globe,
  code_execute: Code,
  file_read: Terminal,
  file_write: Terminal,
  connector_execute: Database,
  security_scan: Shield,
};

function formatDuration(ms?: number): string {
  if (!ms) return "";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function StepRow({ step, index }: { step: ConsoleStep; index: number }) {
  const [open, setOpen] = useState(step.status === "running");
  const Icon = STATUS_ICONS[step.status];
  const ToolIcon = step.tool ? TOOL_ICONS[step.tool] || Wrench : Wrench;
  const hasExpandable = step.code || step.output;

  return (
    <div className="border-b border-zinc-200/50 dark:border-zinc-700/50 last:border-0">
      <button
        onClick={() => hasExpandable && setOpen(!open)}
        className={cn(
          "flex w-full items-center gap-2 px-3 py-2 text-left text-xs transition-colors",
          hasExpandable ? "hover:bg-zinc-100 dark:hover:bg-zinc-800/50 cursor-pointer" : "cursor-default"
        )}
      >
        <Icon className={cn("h-3.5 w-3.5 shrink-0", STATUS_COLORS[step.status], step.status === "running" && "animate-spin")} />
        <ToolIcon className="h-3 w-3 shrink-0 text-zinc-400" />
        <span className="font-mono text-[10px] text-zinc-400 shrink-0">{String(index + 1).padStart(2, "0")}</span>
        <span className="flex-1 truncate text-zinc-700 dark:text-zinc-300">{step.label}</span>
        {step.duration_ms != null && (
          <Badge variant="outline" className="text-[9px] shrink-0 ml-auto">
            <Clock className="mr-0.5 h-2.5 w-2.5" />{formatDuration(step.duration_ms)}
          </Badge>
        )}
        {hasExpandable && (
          open ? <ChevronDown className="h-3 w-3 shrink-0 text-zinc-400" /> : <ChevronRight className="h-3 w-3 shrink-0 text-zinc-400" />
        )}
      </button>
      {open && hasExpandable && (
        <div className="px-3 pb-2 space-y-1.5">
          {step.code && (
            <div className="rounded-lg bg-zinc-950 overflow-x-auto">
              <div className="flex items-center gap-1.5 px-2.5 py-1 border-b border-zinc-800">
                <Terminal className="h-3 w-3 text-zinc-500" />
                <span className="text-[10px] text-zinc-500 font-mono">{step.lang || "code"}</span>
              </div>
              <pre className="p-2.5 text-[11px] leading-relaxed font-mono text-zinc-300 whitespace-pre-wrap break-all">
                {step.code}
              </pre>
            </div>
          )}
          {step.output && (
            <div className="rounded-lg bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 overflow-x-auto">
              <div className="flex items-center gap-1.5 px-2.5 py-1 border-b border-zinc-200 dark:border-zinc-800">
                <span className="text-[10px] text-zinc-500 font-mono">output</span>
              </div>
              <pre className="p-2.5 text-[11px] leading-relaxed font-mono text-zinc-600 dark:text-zinc-400 whitespace-pre-wrap break-all">
                {step.output}
              </pre>
            </div>
          )}
          {step.detail && !step.code && !step.output && (
            <p className="text-[11px] text-zinc-500 dark:text-zinc-400 px-1">{step.detail}</p>
          )}
        </div>
      )}
    </div>
  );
}

export function ToolConsole({ steps, title, strategy, model, compact }: ToolConsoleProps) {
  const [expanded, setExpanded] = useState(!compact);
  const running = steps.some((s) => s.status === "running");
  const passed = steps.filter((s) => s.status === "done").length;
  const failed = steps.filter((s) => s.status === "failed").length;

  if (steps.length === 0) return null;

  return (
    <div className={cn(
      "rounded-xl border overflow-hidden",
      running
        ? "border-blue-300 dark:border-blue-700 bg-blue-50/30 dark:bg-blue-950/20"
        : failed > 0
          ? "border-red-200 dark:border-red-900 bg-red-50/30 dark:bg-red-950/10"
          : "border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/50"
    )}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-zinc-100 dark:hover:bg-zinc-800/50 transition-colors"
      >
        <Terminal className="h-3.5 w-3.5 shrink-0 text-zinc-500" />
        {running && <Loader2 className="h-3 w-3 animate-spin text-blue-500" />}
        <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300 flex-1">
          {title || "Agent execution"}
        </span>
        {strategy && <Badge variant="outline" className="text-[9px] shrink-0">{strategy}</Badge>}
        {model && <Badge variant="secondary" className="text-[9px] shrink-0">{model}</Badge>}
        <Badge variant={failed > 0 ? "destructive" : "outline"} className="text-[9px] shrink-0">
          {passed}/{steps.length}
        </Badge>
        {expanded
          ? <ChevronDown className="h-3 w-3 shrink-0 text-zinc-400" />
          : <ChevronRight className="h-3 w-3 shrink-0 text-zinc-400" />
        }
      </button>
      {expanded && (
        <div className="border-t border-zinc-200 dark:border-zinc-800">
          {steps.map((step, i) => (
            <StepRow key={i} step={step} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}

/* ---- helpers for building steps from message data ---- */

export function parseToolSteps(
  toolCalls: any[] | null | undefined,
  content: string | null | undefined,
  metadata: Record<string, any> | null | undefined
): ConsoleStep[] {
  const steps: ConsoleStep[] = [];

  // From tool_calls array
  if (Array.isArray(toolCalls)) {
    for (const tc of toolCalls) {
      steps.push({
        label: tc.name || tc.function?.name || "tool call",
        status: tc.error ? "failed" : "done",
        tool: tc.name || tc.function?.name,
        code: tc.arguments || tc.function?.arguments || undefined,
        output: typeof tc.result === "string" ? tc.result : (tc.result ? JSON.stringify(tc.result, null, 2) : undefined),
        detail: tc.error,
        duration_ms: tc.duration_ms,
      });
    }
  }

  // From metadata (agent brain trace, plan steps)
  if (metadata?.plan?.subtasks) {
    for (const st of metadata.plan.subtasks) {
      steps.push({
        label: st.title || st.name || `Step ${st.order || steps.length + 1}`,
        status: "done",
        tool: st.tools?.[0],
        detail: st.acceptance || st.description,
      });
    }
  }

  // From metadata.steps (ReAct loop results)
  if (Array.isArray(metadata?.steps)) {
    for (const st of metadata.steps) {
      steps.push({
        label: st.title || `Step ${st.order || steps.length + 1}`,
        status: st.passed ? "done" : "failed",
        tool: st.action,
        detail: st.observation,
        output: st.files?.length ? st.files.map((f: any) => f.name).join(", ") : undefined,
      });
    }
  }

  // If no structured data, parse content for code blocks
  if (steps.length === 0 && content) {
    const codeBlocks = content.match(/```(\w+)?\n([\s\S]*?)```/g);
    if (codeBlocks) {
      for (const block of codeBlocks) {
        const match = block.match(/```(\w+)?\n([\s\S]*?)```/);
        if (match) {
          steps.push({
            label: `Code block (${match[1] || "text"})`,
            status: "done",
            lang: match[1] || "text",
            code: match[2].trim(),
          });
        }
      }
    }
  }

  return steps;
}

export function parseReasoningTrace(
  metadata: Record<string, any> | null | undefined
): string[] {
  if (!metadata) return [];
  if (Array.isArray(metadata.trace)) return metadata.trace;
  if (metadata.plan?.strategy) return [`Strategy: ${metadata.plan.strategy}`];
  return [];
}

