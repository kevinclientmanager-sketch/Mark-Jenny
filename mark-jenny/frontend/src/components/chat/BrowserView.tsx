"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Globe, MessageSquare, ListChecks, Loader2, ExternalLink, RefreshCw, CheckCircle2, Circle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Message } from "@/lib/api/chat";
import { ChatInput } from "@/components/chat/ChatInput";

interface BrowserViewProps {
  messages: Message[];
  sessions: { id: string; url?: string; status?: string; name?: string }[];
  onSend: (text: string) => void;
  sending: boolean;
  activeChatId: number | null;
  onFile: (file: File) => void;
}

interface TaskStep {
  label: string;
  status: "done" | "active" | "pending";
}

function parseBrowserSteps(messages: Message[]): TaskStep[] {
  const steps: TaskStep[] = [];
  for (const msg of messages) {
    if (msg.role === "ASSISTANT" && msg.content) {
      const lines = msg.content.split("\n");
      for (const line of lines) {
        const trimmed = line.trim();
        if (/^\d+[\.\)]\s/.test(trimmed) || /^[-•]\s/.test(trimmed)) {
          const label = trimmed.replace(/^[\d\.\)•-]+\s*/, "");
          if (label.length > 5) steps.push({ label, status: "done" });
        }
      }
    }
  }
  if (steps.length === 0) {
    steps.push({ label: "Waiting for agent to start browsing...", status: "active" });
  } else {
    steps[steps.length - 1].status = "active";
  }
  return steps;
}

function extractBrowserUrl(messages: Message[]): string | null {
  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i];
    if (msg.role === "ASSISTANT" && msg.content) {
      const urlMatch = msg.content.match(/https?:\/\/[^\s\)]+/);
      if (urlMatch) return urlMatch[0];
    }
  }
  return null;
}

export function BrowserView({ messages, sessions, onSend, sending, activeChatId, onFile }: BrowserViewProps) {
  const [chatWidth, setChatWidth] = useState(45);
  const draggingRef = useRef(false);
  const taskSteps = parseBrowserSteps(messages);
  const browserUrl = extractBrowserUrl(messages);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const startDrag = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    draggingRef.current = true;
    const onMove = (ev: MouseEvent) => {
      const pct = (ev.clientX / window.innerWidth) * 100;
      setChatWidth(Math.min(75, Math.max(25, pct)));
    };
    const onUp = () => {
      draggingRef.current = false;
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, []);

  return (
    <div className="flex-1 flex min-h-0">
      {/* Left: chat with agent */}
      <div className="flex flex-col min-w-0" style={{ width: `${chatWidth}%` }}>
        <div className="h-9 shrink-0 border-b bg-white dark:bg-zinc-900 flex items-center gap-2 px-3">
          <MessageSquare className="h-3.5 w-3.5 text-blue-500" />
          <span className="text-xs font-medium">Agent Chat</span>
          {messages.length > 0 && (
            <Badge variant="secondary" className="text-[10px] px-1.5 py-0 ml-auto">{messages.length}</Badge>
          )}
        </div>

        {taskSteps.length > 0 && (
          <div className="shrink-0 border-b bg-zinc-50 dark:bg-zinc-900/50 px-3 py-2 max-h-36 overflow-y-auto">
            <div className="flex items-center gap-1.5 mb-1.5">
              <ListChecks className="h-3 w-3 text-zinc-400" />
              <span className="text-[10px] font-semibold uppercase tracking-wide text-zinc-400">Browse Plan</span>
            </div>
            <div className="space-y-1">
              {taskSteps.map((step, i) => (
                <div key={i} className="flex items-start gap-2 text-xs">
                  {step.status === "done" ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-green-500 shrink-0 mt-0.5" />
                  ) : step.status === "active" ? (
                    <Loader2 className="h-3.5 w-3.5 text-blue-500 shrink-0 mt-0.5 animate-spin" />
                  ) : (
                    <Circle className="h-3.5 w-3.5 text-zinc-300 shrink-0 mt-0.5" />
                  )}
                  <span className={cn("leading-tight", step.status === "active" ? "text-zinc-900 dark:text-zinc-100 font-medium" : "text-zinc-500")}>
                    {step.label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-3">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <Globe className="h-8 w-8 text-zinc-300 dark:text-zinc-700 mb-2" />
              <p className="text-sm font-medium text-zinc-500">What should I browse?</p>
              <p className="text-xs text-zinc-400 mt-1">Tell me a website to open or a topic to research</p>
            </div>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className={cn("flex", msg.role === "USER" ? "justify-end" : "justify-start")}>
                <div className={cn("max-w-[85%] rounded-lg px-3 py-2 text-sm", msg.role === "USER" ? "bg-blue-600 text-white" : "bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100")}>
                  <p className="whitespace-pre-wrap break-words leading-relaxed">{msg.content}</p>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="shrink-0 border-t">
          <ChatInput onSend={onSend} onFile={onFile} disabled={sending || !activeChatId} mode="browse" />
        </div>
      </div>

      {/* Draggable divider */}
      <div onMouseDown={startDrag} className="w-1.5 cursor-col-resize hover:bg-blue-400 bg-zinc-200 dark:bg-zinc-700 shrink-0 transition-colors" title="Drag to resize" />

      {/* Right: browser view */}
      <div className="flex flex-col min-w-0" style={{ width: `${100 - chatWidth}%` }}>
        <div className="h-9 shrink-0 border-b bg-white dark:bg-zinc-900 flex items-center gap-2 px-3">
          <Globe className="h-3.5 w-3.5 text-blue-500" />
          <span className="text-xs font-medium">Browser</span>
          {browserUrl && (
            <div className="flex-1 flex items-center gap-1.5 bg-zinc-100 dark:bg-zinc-800 rounded-md px-2 py-0.5 min-w-0">
              <span className="truncate text-[11px] text-zinc-500">{browserUrl}</span>
              <a href={browserUrl} target="_blank" rel="noopener noreferrer" className="shrink-0 text-zinc-400 hover:text-zinc-600">
                <ExternalLink className="h-3 w-3" />
              </a>
            </div>
          )}
          {browserUrl && (
            <Button variant="ghost" size="sm" className="h-6 px-2 text-[11px] ml-auto" onClick={() => iframeRef.current?.contentWindow?.location.reload()}>
              <RefreshCw className="h-3 w-3 mr-1" /> Refresh
            </Button>
          )}
        </div>

        <div className="flex-1 min-h-0 bg-white dark:bg-zinc-950">
          {browserUrl ? (
            <iframe ref={iframeRef} src={browserUrl} className="w-full h-full border-0" title="Browser view" sandbox="allow-same-origin allow-scripts allow-forms allow-popups" />
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <Globe className="h-10 w-10 text-zinc-200 dark:text-zinc-800 mb-2" />
              <p className="text-sm text-zinc-400">No page loaded yet</p>
              <p className="text-xs text-zinc-300 mt-1">Agent will open pages here as you browse</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
