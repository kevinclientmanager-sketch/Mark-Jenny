"use client";
import { useState, useEffect, useRef } from "react";
import { Globe, FileText, Search, Code2, Loader2, ChevronDown, ChevronRight, Monitor } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ActivityEntry {
  id: string;
  type: "search" | "browse" | "read" | "write" | "code" | "think" | "tool" | "complete";
  label: string;
  detail?: string;
  url?: string;
  timestamp: number;
  status: "active" | "done" | "error";
}

const iconMap: Record<string, any> = {
  search: Search,
  browse: Globe,
  read: FileText,
  write: FileText,
  code: Code2,
  think: Loader2,
  tool: Monitor,
  complete: Loader2,
};

export function ActivityLog({ entries, isOpen, onToggle }: { entries: ActivityEntry[]; isOpen: boolean; onToggle: () => void }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [entries]);

  if (entries.length === 0) return null;

  return (
    <div className="border-t border-zinc-200 dark:border-zinc-800">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-4 py-2 text-xs font-medium text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors"
      >
        {isOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        <Monitor className="h-3.5 w-3.5" />
        <span>Agent Activity</span>
        <span className="ml-auto text-zinc-400">{entries.length} steps</span>
        {entries.some(e => e.status === "active") && (
          <span className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
        )}
      </button>
      {isOpen && (
        <div ref={scrollRef} className="max-h-48 overflow-y-auto px-4 pb-3 space-y-1">
          {entries.map((entry) => {
            const Icon = iconMap[entry.type] || Loader2;
            return (
              <div
                key={entry.id}
                className={cn(
                  "flex items-start gap-2 py-1.5 px-2 rounded-md text-xs",
                  entry.status === "active" && "bg-blue-50 dark:bg-blue-950/20",
                  entry.status === "done" && "opacity-60"
                )}
              >
                <Icon className={cn(
                  "h-3.5 w-3.5 mt-0.5 shrink-0",
                  entry.status === "active" ? "text-blue-500 animate-pulse" : "text-zinc-400"
                )} />
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-zinc-700 dark:text-zinc-300 truncate">{entry.label}</p>
                  {entry.detail && (
                    <p className="text-zinc-500 truncate">{entry.detail}</p>
                  )}
                  {entry.url && (
                    <p className="text-blue-500 truncate text-[10px]">{entry.url}</p>
                  )}
                </div>
                <span className="text-[10px] text-zinc-400 shrink-0">
                  {new Date(entry.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function ComputerPanel({
  isActive,
  currentUrl,
  screenshotUrl,
  step,
  totalSteps,
}: {
  isActive: boolean;
  currentUrl?: string;
  screenshotUrl?: string;
  step?: number;
  totalSteps?: number;
}) {
  const [expanded, setExpanded] = useState(false);

  if (!isActive && !screenshotUrl) return null;

  return (
    <div className={cn(
      "border-t border-zinc-200 dark:border-zinc-800 transition-all duration-300",
      expanded ? "h-64" : "h-20"
    )}>
      <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-200 dark:border-zinc-800">
        <div className="flex items-center gap-2">
          <Monitor className="h-4 w-4 text-blue-500" />
          <span className="text-xs font-medium">Agent Computer</span>
          {isActive && <span className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />}
          {step && totalSteps && (
            <span className="text-[10px] text-zinc-500 ml-1">{step}/{totalSteps}</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {currentUrl && (
            <span className="text-[10px] text-zinc-400 max-w-[200px] truncate">{currentUrl}</span>
          )}
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-1 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded"
          >
            {expanded ? <Monitor className="h-3 w-3" /> : <Monitor className="h-3 w-3" />}
          </button>
        </div>
      </div>
      {expanded && screenshotUrl && (
        <div className="p-2 h-full">
          <img src={screenshotUrl} alt="Agent view" className="w-full h-full object-contain rounded" />
        </div>
      )}
      {expanded && !screenshotUrl && (
        <div className="flex items-center justify-center h-full text-xs text-zinc-400">
          {isActive ? "Agent is working..." : "No active session"}
        </div>
      )}
    </div>
  );
}

