"use client";

import { useState } from "react";
import {
  Code2, Terminal, Globe, FileText, Layers, X, ChevronDown,
  FolderOpen, File, FileCode, RefreshCw, ExternalLink, Maximize2, Minimize2,
  Clock, MessageSquare
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type RightPanelTab = "code" | "terminal" | "browser" | "files" | "context" | "history";

interface FileEntry {
  name: string;
  path: string;
  type: "file" | "folder";
  status?: "added" | "modified" | "deleted";
  children?: FileEntry[];
}

interface RightPanelProps {
  taskUpdate?: {
    task: {
      id: number;
      title?: string;
      status: string;
      current_step: number;
      total_steps: number;
      error?: string | null;
      result?: unknown;
    };
  } | null;
  connected: boolean;
  browserUrl?: string;
  projectFiles?: FileEntry[];
  chatHistory?: { id: number; title?: string; last_message?: string; created_at: string }[];
  onClose: () => void;
}

const TABS: { id: RightPanelTab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "code", label: "Code", icon: Code2 },
  { id: "terminal", label: "Terminal", icon: Terminal },
  { id: "browser", label: "Browser", icon: Globe },
  { id: "files", label: "Files", icon: FileText },
  { id: "context", label: "Context", icon: Layers },
  { id: "history", label: "History", icon: Clock },
];

function CodeTab({ taskUpdate }: { taskUpdate?: RightPanelProps["taskUpdate"] }) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-3 py-2 border-b text-xs">
        <span className="font-medium text-zinc-700 dark:text-zinc-300">Files Changed</span>
        {taskUpdate && (
          <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
            {taskUpdate.task.current_step}/{taskUpdate.task.total_steps}
          </Badge>
        )}
      </div>
      <div className="flex-1 overflow-auto p-3">
        {taskUpdate?.task.result ? (
          <pre className="text-xs text-zinc-600 dark:text-zinc-400 whitespace-pre-wrap font-mono leading-relaxed">
            {typeof taskUpdate.task.result === "string"
              ? taskUpdate.task.result
              : JSON.stringify(taskUpdate.task.result, null, 2)}
          </pre>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-zinc-400 gap-2">
            <Code2 className="h-8 w-8" />
            <p className="text-xs text-center">Code changes will appear here as Mark builds.</p>
          </div>
        )}
      </div>
    </div>
  );
}

function TerminalTab({ connected }: { connected: boolean }) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-3 py-2 border-b text-xs">
        <span className="font-medium text-zinc-700 dark:text-zinc-300">Terminal</span>
        <span className={cn("h-2 w-2 rounded-full", connected ? "bg-green-500" : "bg-zinc-400")} />
        <span className="text-zinc-500">{connected ? "live" : "offline"}</span>
      </div>
      <div className="flex-1 overflow-auto p-3 font-mono text-xs bg-zinc-950 text-green-400">
        <p className="text-zinc-500">$ awaiting commands...</p>
      </div>
    </div>
  );
}

function BrowserTab({ browserUrl }: { browserUrl?: string }) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-3 py-2 border-b text-xs">
        <span className="font-medium text-zinc-700 dark:text-zinc-300">Browser</span>
        {browserUrl && (
          <span className="truncate text-zinc-500 max-w-[200px]">{browserUrl}</span>
        )}
      </div>
      <div className="flex-1 flex flex-col items-center justify-center text-zinc-400 gap-2 p-3">
        <Globe className="h-8 w-8" />
        <p className="text-xs text-center">Live browser preview appears here when Mark opens a page.</p>
        {browserUrl && (
          <a href={browserUrl} target="_blank" rel="noopener noreferrer"
            className="flex items-center gap-1 text-blue-500 hover:underline text-xs">
            <ExternalLink className="h-3 w-3" /> Open in new tab
          </a>
        )}
      </div>
    </div>
  );
}

function FilesTab({ projectFiles }: { projectFiles?: FileEntry[] }) {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());

  const toggleFolder = (path: string) => {
    setExpandedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const renderEntry = (entry: FileEntry, depth: number = 0) => {
    const isFolder = entry.type === "folder";
    const isExpanded = expandedFolders.has(entry.path);

    return (
      <div key={entry.path}>
        <button
          onClick={() => isFolder && toggleFolder(entry.path)}
          className={cn(
            "w-full flex items-center gap-1.5 px-2 py-1 text-xs hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors text-left",
            entry.status === "added" && "text-green-600",
            entry.status === "modified" && "text-amber-600",
            entry.status === "deleted" && "text-red-600 line-through"
          )}
          style={{ paddingLeft: `${depth * 12 + 8}px` }}
        >
          {isFolder ? (
            <ChevronDown className={cn("h-3 w-3 shrink-0 transition-transform", !isExpanded && "-rotate-90")} />
          ) : (
            <FileCode className="h-3 w-3 shrink-0 text-zinc-400" />
          )}
          <span className="truncate">{entry.name}</span>
          {entry.status && (
            <Badge variant="outline" className={cn(
              "ml-auto text-[9px] px-1 py-0 shrink-0",
              entry.status === "added" && "border-green-300 text-green-600",
              entry.status === "modified" && "border-amber-300 text-amber-600",
              entry.status === "deleted" && "border-red-300 text-red-600"
            )}>
              {entry.status[0].toUpperCase()}
            </Badge>
          )}
        </button>
        {isFolder && isExpanded && entry.children?.map((child) => renderEntry(child, depth + 1))}
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-3 py-2 border-b text-xs">
        <FolderOpen className="h-3.5 w-3.5 text-zinc-500" />
        <span className="font-medium text-zinc-700 dark:text-zinc-300">Project Files</span>
      </div>
      <div className="flex-1 overflow-auto">
        {projectFiles && projectFiles.length > 0 ? (
          projectFiles.map((entry) => renderEntry(entry))
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-zinc-400 gap-2 p-3">
            <FolderOpen className="h-8 w-8" />
            <p className="text-xs text-center">Project files will appear here as Mark creates them.</p>
          </div>
        )}
      </div>
    </div>
  );
}

function HistoryTab({ chatHistory }: { chatHistory?: RightPanelProps["chatHistory"] }) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-3 py-2 border-b text-xs">
        <Clock className="h-3.5 w-3.5 text-zinc-500" />
        <span className="font-medium text-zinc-700 dark:text-zinc-300">Chat History</span>
      </div>
      <div className="flex-1 overflow-auto">
        {chatHistory && chatHistory.length > 0 ? (
          <div className="space-y-0.5 p-1">
            {chatHistory.map((chat) => (
              <div
                key={chat.id}
                className="flex items-start gap-2 rounded-lg p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors cursor-pointer"
              >
                <MessageSquare className="h-3.5 w-3.5 shrink-0 text-zinc-400 mt-0.5" />
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium truncate">{chat.title || "Untitled"}</p>
                  <p className="text-[11px] text-zinc-500 truncate">{chat.last_message || "No messages"}</p>
                  <p className="text-[10px] text-zinc-400 mt-0.5">
                    {new Date(chat.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-zinc-400 gap-2 p-3">
            <Clock className="h-8 w-8" />
            <p className="text-xs text-center">Chat history for this project will appear here.</p>
          </div>
        )}
      </div>
    </div>
  );
}

function ContextTab({ taskUpdate, connected }: { taskUpdate?: RightPanelProps["taskUpdate"]; connected: boolean }) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-3 py-2 border-b text-xs">
        <Layers className="h-3.5 w-3.5 text-zinc-500" />
        <span className="font-medium text-zinc-700 dark:text-zinc-300">Context</span>
      </div>
      <div className="flex-1 overflow-auto p-3 space-y-3">
        {taskUpdate ? (
          <>
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium truncate">{taskUpdate.task.title || `Task #${taskUpdate.task.id}`}</span>
                <Badge variant={taskUpdate.task.status === "RUNNING" ? "default" : "secondary"} className="text-[10px]">
                  {taskUpdate.task.status}
                </Badge>
              </div>
              <div className="h-1.5 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-600 rounded-full transition-[width]"
                  style={{ width: `${(taskUpdate.task.current_step / Math.max(1, taskUpdate.task.total_steps)) * 100}%` }}
                />
              </div>
              <p className="text-[10px] text-zinc-500">
                Step {taskUpdate.task.current_step}/{taskUpdate.task.total_steps} — {connected ? "● live" : "○ offline"}
              </p>
            </div>
            {taskUpdate.task.error && (
              <div className="p-2 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                <p className="text-[11px] text-red-600 dark:text-red-400">{taskUpdate.task.error}</p>
              </div>
            )}
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-zinc-400 gap-2">
            <Layers className="h-8 w-8" />
            <p className="text-xs text-center">Task context and progress will appear here.</p>
          </div>
        )}
      </div>
    </div>
  );
}

export function RightPanel({
  taskUpdate,
  connected,
  browserUrl,
  projectFiles,
  chatHistory,
  onClose,
}: RightPanelProps) {
  const [activeTab, setActiveTab] = useState<RightPanelTab>("code");

  return (
    <div className="flex flex-col h-full bg-white dark:bg-zinc-900">
      {/* Tab bar */}
      <div className="flex items-center border-b shrink-0">
        <div className="flex items-center gap-0.5 px-1 py-1 overflow-x-auto flex-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors shrink-0",
                activeTab === tab.id
                  ? "bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100"
                  : "text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 hover:bg-zinc-50 dark:hover:bg-zinc-800/50"
              )}
            >
              <tab.icon className="h-3.5 w-3.5" />
              {tab.label}
            </button>
          ))}
        </div>
        <Button
          size="icon"
          variant="ghost"
          className="h-7 w-7 shrink-0 mr-1"
          onClick={onClose}
          title="Close panel"
        >
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Tab content */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {activeTab === "code" && <CodeTab taskUpdate={taskUpdate} />}
        {activeTab === "terminal" && <TerminalTab connected={connected} />}
        {activeTab === "browser" && <BrowserTab browserUrl={browserUrl} />}
        {activeTab === "files" && <FilesTab projectFiles={projectFiles} />}
        {activeTab === "context" && <ContextTab taskUpdate={taskUpdate} connected={connected} />}
        {activeTab === "history" && <HistoryTab chatHistory={chatHistory} />}
      </div>
    </div>
  );
}
