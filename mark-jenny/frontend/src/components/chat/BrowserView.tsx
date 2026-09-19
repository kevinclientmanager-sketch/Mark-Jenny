"use client";

import { useState, useRef, useCallback } from "react";
import {
  Globe, MessageSquare, ListChecks, Loader2, ExternalLink, RefreshCw,
  CheckCircle2, Circle, ArrowLeft, ArrowRight, Star, Share2, Download,
  MoreHorizontal, Plus, X, Search, Shield, Bookmark, Code, Copy
} from "lucide-react";
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

interface BrowserTab {
  id: string;
  title: string;
  url: string;
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
  const containerRef = useRef<HTMLDivElement>(null);
  const taskSteps = parseBrowserSteps(messages);
  const browserUrl = extractBrowserUrl(messages);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const [browserTabs, setBrowserTabs] = useState<BrowserTab[]>([
    { id: "1", title: "New Tab", url: "" }
  ]);
  const [activeBrowserTab, setActiveBrowserTab] = useState("1");
  const [urlInput, setUrlInput] = useState("");
  const [bookmarked, setBookmarked] = useState(false);
  const [showDevtools, setShowDevtools] = useState(false);

  const currentUrl = browserTabs.find((t) => t.id === activeBrowserTab)?.url || browserUrl || "";

  const navigateTo = useCallback((url: string) => {
    let finalUrl = url;
    if (!url.startsWith("http://") && !url.startsWith("https://")) {
      finalUrl = "https://" + url;
    }
    setBrowserTabs((prev) => prev.map((t) => t.id === activeBrowserTab ? { ...t, url: finalUrl, title: finalUrl.replace(/https?:\/\//, "").split("/")[0] } : t));
    setUrlInput(finalUrl);
  }, [activeBrowserTab]);

  const addTab = useCallback(() => {
    const id = Date.now().toString();
    setBrowserTabs((prev) => [...prev, { id, title: "New Tab", url: "" }]);
    setActiveBrowserTab(id);
  }, []);

  const closeTab = useCallback((tabId: string) => {
    setBrowserTabs((prev) => {
      const next = prev.filter((t) => t.id !== tabId);
      if (next.length === 0) {
        const id = Date.now().toString();
        setActiveBrowserTab(id);
        return [{ id, title: "New Tab", url: "" }];
      }
      if (activeBrowserTab === tabId) {
        setActiveBrowserTab(next[next.length - 1].id);
      }
      return next;
    });
  }, [activeBrowserTab]);

  const startDrag = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    draggingRef.current = true;
    const container = containerRef.current;
    if (!container) return;
    const rect = container.getBoundingClientRect();
    const onMove = (ev: MouseEvent) => {
      const x = ev.clientX - rect.left;
      const pct = (x / rect.width) * 100;
      setChatWidth(Math.min(80, Math.max(20, pct)));
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
    <div ref={containerRef} className="flex-1 flex min-h-0">
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

      {/* Right: real browser */}
      <div className="flex flex-col min-w-0" style={{ width: `${100 - chatWidth}%` }}>
        {/* Browser tabs bar */}
        <div className="h-8 shrink-0 bg-zinc-100 dark:bg-zinc-800 flex items-end gap-0.5 px-1 overflow-x-auto scrollbar-none">
          {browserTabs.map((tab) => (
            <div
              key={tab.id}
              onClick={() => setActiveBrowserTab(tab.id)}
              className={cn(
                "group flex items-center gap-1.5 rounded-t-lg px-2.5 py-1 text-[11px] cursor-pointer max-w-[160px] shrink-0 border-b-2 transition-colors",
                tab.id === activeBrowserTab
                  ? "bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 border-blue-500"
                  : "text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 border-transparent"
              )}
            >
              <Globe className="h-3 w-3 shrink-0" />
              <span className="truncate flex-1">{tab.title}</span>
              <button onClick={(e) => { e.stopPropagation(); closeTab(tab.id); }} className="shrink-0 rounded p-0.5 opacity-0 group-hover:opacity-100 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-opacity">
                <X className="h-2.5 w-2.5" />
              </button>
            </div>
          ))}
          <button onClick={addTab} className="shrink-0 rounded-t-lg p-1.5 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-colors" title="New tab">
            <Plus className="h-3 w-3" />
          </button>
        </div>

        {/* Browser toolbar */}
        <div className="h-10 shrink-0 bg-white dark:bg-zinc-900 border-b flex items-center gap-1 px-2">
          {/* Nav buttons */}
          <button onClick={() => iframeRef.current?.contentWindow?.history.back()} className="p-1.5 rounded-md text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-800 dark:hover:text-zinc-200 transition-colors" title="Back">
            <ArrowLeft className="h-4 w-4" />
          </button>
          <button onClick={() => iframeRef.current?.contentWindow?.history.forward()} className="p-1.5 rounded-md text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-800 dark:hover:text-zinc-200 transition-colors" title="Forward">
            <ArrowRight className="h-4 w-4" />
          </button>
          <button onClick={() => iframeRef.current?.contentWindow?.location.reload()} className="p-1.5 rounded-md text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-800 dark:hover:text-zinc-200 transition-colors" title="Refresh">
            <RefreshCw className="h-4 w-4" />
          </button>

          {/* URL bar */}
          <div className="flex-1 flex items-center gap-1.5 bg-zinc-100 dark:bg-zinc-800 rounded-lg px-2.5 py-1 mx-1">
            <Shield className="h-3.5 w-3.5 text-zinc-400 shrink-0" />
            <input
              type="text"
              value={urlInput || currentUrl}
              onChange={(e) => setUrlInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && urlInput) navigateTo(urlInput); }}
              placeholder="Search or enter URL"
              className="flex-1 bg-transparent text-xs text-zinc-700 dark:text-zinc-300 outline-none placeholder:text-zinc-400"
            />
            {urlInput && (
              <button onClick={() => navigateTo(urlInput)} className="shrink-0 text-zinc-400 hover:text-blue-500">
                <Search className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          {/* Action buttons */}
          <button onClick={() => setBookmarked(!bookmarked)} className={cn("p-1.5 rounded-md transition-colors", bookmarked ? "text-yellow-500" : "text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-800 dark:hover:text-zinc-200")} title="Bookmark this page">
            <Star className={cn("h-4 w-4", bookmarked && "fill-current")} />
          </button>
          <button onClick={() => { navigator.clipboard.writeText(currentUrl); }} className="p-1.5 rounded-md text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-800 dark:hover:text-zinc-200 transition-colors" title="Copy link">
            <Copy className="h-4 w-4" />
          </button>
          <button onClick={() => { if (currentUrl) window.open(currentUrl, "_blank"); }} className="p-1.5 rounded-md text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-800 dark:hover:text-zinc-200 transition-colors" title="Open in new window">
            <ExternalLink className="h-4 w-4" />
          </button>
          <button onClick={() => { if (currentUrl) { const a = document.createElement("a"); a.href = currentUrl; a.download = ""; a.click(); } }} className="p-1.5 rounded-md text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-800 dark:hover:text-zinc-200 transition-colors" title="Download">
            <Download className="h-4 w-4" />
          </button>
          <button onClick={() => setShowDevtools(!showDevtools)} className={cn("p-1.5 rounded-md transition-colors", showDevtools ? "text-blue-500 bg-blue-50 dark:bg-blue-900/30" : "text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-800 dark:hover:text-zinc-200")} title="DevTools">
            <Code className="h-4 w-4" />
          </button>
        </div>

        {/* Browser content */}
        <div className="flex-1 min-h-0 bg-white dark:bg-zinc-950 relative">
          {currentUrl ? (
            <iframe ref={iframeRef} src={currentUrl} className="w-full h-full border-0" title="Browser view" sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-downloads" />
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <Globe className="h-12 w-12 text-zinc-200 dark:text-zinc-800 mb-3" />
              <p className="text-sm font-medium text-zinc-400">New Tab</p>
              <p className="text-xs text-zinc-300 mt-1">Search or enter a URL to start browsing</p>
            </div>
          )}

          {/* DevTools panel */}
          {showDevtools && currentUrl && (
            <div className="absolute bottom-0 left-0 right-0 h-48 bg-zinc-900 border-t border-zinc-700 overflow-auto p-3 font-mono text-xs text-zinc-300">
              <div className="flex items-center gap-2 mb-2">
                <Code className="h-3 w-3 text-green-400" />
                <span className="text-green-400 font-semibold">DevTools</span>
                <button onClick={() => setShowDevtools(false)} className="ml-auto text-zinc-500 hover:text-zinc-300"><X className="h-3 w-3" /></button>
              </div>
              <div className="space-y-1 text-[11px]">
                <p><span className="text-zinc-500">URL:</span> <span className="text-blue-400">{currentUrl}</span></p>
                <p><span className="text-zinc-500">Status:</span> <span className="text-green-400">Loaded</span></p>
                <p><span className="text-zinc-500">Session:</span> <span className="text-zinc-400">{sessions[0]?.id?.slice(0, 12) || "None"}</span></p>
                <p className="text-zinc-500 mt-2">Console output and page inspection available when connected to live session.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
