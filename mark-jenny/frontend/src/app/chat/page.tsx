"use client";
import { useEffect, useState, useCallback, useRef } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { ChatTopBar } from "@/components/chat/ChatTopBar";
import { SessionTabs } from "@/components/chat/SessionTabs";
import { RightPanel } from "@/components/chat/RightPanel";
import { ProtectedLayout } from "@/components/layout/protected-layout";
import { MessageList } from "@/components/chat/MessageList";
import { ChatInput } from "@/components/chat/ChatInput";
import { browserApi } from "@/lib/api/browser";
import { chatApi, Chat, Message } from "@/lib/api/chat";
import { filesApi } from "@/lib/api/files";
import { projectsApi, Project } from "@/lib/api/projects";
import { useTaskRealTime } from "@/lib/hooks/useTaskWebSocket";
import { Button } from "@/components/ui/button";
import {
  Code2, Search, FileText, BarChart3, Palette, BrainCircuit,
  Loader2, PanelRight, Globe, X, Zap, MessageSquare, CalendarClock,
  Library, Plug, CloudUpload, Image as ImageIcon, Video, Music, Table,
  Presentation, Plus, AppWindow
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter, SheetClose,
} from "@/components/ui/sheet";
import { toast } from "@/components/ui/toast";

const SUGGESTIONS = [
  { label: "Create a to-do app", icon: Code2, prompt: "Create a simple to-do application with React and Tailwind" },
  { label: "Research a topic", icon: Search, prompt: "Research the latest developments in AI agents and summarize key findings" },
  { label: "Write a report", icon: FileText, prompt: "Write a professional quarterly business report for Q2 2026" },
  { label: "Analyze data", icon: BarChart3, prompt: "Create a sample sales dashboard with charts and key metrics" },
  { label: "Design a landing page", icon: Palette, prompt: "Design a modern SaaS landing page with hero section, features, and pricing" },
  { label: "Plan a project", icon: BrainCircuit, prompt: "Help me plan and structure a new web application project" },
];

const WORK_SUGGESTIONS = [
  { label: "Build an app", icon: Code2, prompt: "Build a to-do application with React and Tailwind" },
  { label: "REST API", icon: CloudUpload, prompt: "Create a REST API with a SQLite backend and API docs" },
  { label: "Landing page", icon: Palette, prompt: "Build a landing page for my business with pricing" },
  { label: "Desktop app", icon: AppWindow, prompt: "Build a Windows desktop app to track expenses" },
  { label: "Connect an API", icon: Plug, prompt: "Connect my project to the Stripe API" },
  { label: "Prepare deploy", icon: CloudUpload, prompt: "Prepare this project for deployment with step-by-step instructions" },
];

const WORK_CHIPS = [
  { label: "New Build", icon: Plus, prompt: "Start a new build: " },
  { label: "Push / Sync", icon: CloudUpload, prompt: "Push this to GitHub as a pull request: " },
  { label: "Libraries", icon: Library, prompt: "Add a reusable library for: " },
  { label: "Connections", icon: Plug, prompt: "Set up a connection to: " },
];

const BROWSE_SUGGESTIONS = [
  { label: "Research a topic", icon: Search, prompt: "Wide Research: research the latest developments in AI agents and summarize key findings" },
  { label: "Summarize a site", icon: FileText, prompt: "Open the browser and summarize the main content of " },
  { label: "Compare results", icon: BarChart3, prompt: "Open the browser, search and compare the top options for " },
  { label: "Find sources", icon: Globe, prompt: "Find and list credible sources about " },
  { label: "Track a page", icon: CalendarClock, prompt: "Monitor this page and report changes: " },
  { label: "Extract data", icon: Table, prompt: "Open the browser and extract the table/data from " },
];

const PIN_KEY = "mark.pinnedChats";

function loadPinned(): number[] {
  try { return JSON.parse(localStorage.getItem(PIN_KEY) || "[]"); } catch { return []; }
}

function routeIntent(text: string): { tool: string; icon: React.ReactNode } {
  const t = text.toLowerCase();
  if (/\b(image|photo|picture|logo|art|poster|thumbnail|banner)\b/.test(t))
    return { tool: "Image generation", icon: <ImageIcon className="h-3.5 w-3.5" /> };
  if (/\b(video|animation|clip)\b/.test(t))
    return { tool: "Video generation", icon: <Video className="h-3.5 w-3.5" /> };
  if (/\b(audio|music|song|voiceover|podcast)\b/.test(t))
    return { tool: "Audio generation", icon: <Music className="h-3.5 w-3.5" /> };
  if (/\b(slide|presentation|deck)\b/.test(t))
    return { tool: "Slides", icon: <Presentation className="h-3.5 w-3.5" /> };
  if (/\b(spreadsheet|excel|csv|sheet)\b/.test(t))
    return { tool: "Spreadsheet", icon: <Table className="h-3.5 w-3.5" /> };
  if (/\b(research|compare|latest|recent|news|investigate|analyze|statistics)\b/.test(t))
    return { tool: "Deep research", icon: <Search className="h-3.5 w-3.5" /> };
  if (/\b(build|make|create|develop|design|code|app|website|landing|page|component|function|api|cli|tool|script)\b/.test(t))
    return { tool: "Build something", icon: <Code2 className="h-3.5 w-3.5" /> };
  if (/\b(plan|structure|organize|schedule|roadmap)\b/.test(t))
    return { tool: "Planning", icon: <BrainCircuit className="h-3.5 w-3.5" /> };
  if (/\b(summarize|summary|report|write|draft)\b/.test(t))
    return { tool: "Writing", icon: <FileText className="h-3.5 w-3.5" /> };
  return { tool: "General assistant", icon: <BrainCircuit className="h-3.5 w-3.5" /> };
}

function suggestProjectName(text: string): string {
  const cleaned = text
    .replace(/\b(please|can you|could you|i need|i want|help me|lets|let's|make me)\b/gi, " ")
    .replace(/\b(a|an|the|for|with|that|and|of)\b/gi, " ")
    .trim();
  const words = cleaned.split(/\s+/).filter(Boolean).slice(0, 4);
  const name = words.join(" ").replace(/[.,;!?]+$/, "");
  const trimmed = (name[0]?.toUpperCase() + name.slice(1) || cleaned.slice(0, 40)).slice(0, 40);
  return trimmed || "New project";
}

export default function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeChatId, setActiveChatId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loadingChats, setLoadingChats] = useState(true);
  const [loadingMsgs, setLoadingMsgs] = useState(false);
  const [sending, setSending] = useState(false);
  const [projectId, setProjectId] = useState<number | undefined>(undefined);
  const [projects, setProjects] = useState<Project[]>([]);
  const [taskId, setTaskId] = useState<number | undefined>(undefined);
  const { taskUpdate, connected } = useTaskRealTime(taskId);
  const [pinned, setPinned] = useState<number[]>([]);
  const [workOpen, setWorkOpen] = useState(false);
  const [workWidth, setWorkWidth] = useState(420);
  const draggingRef = useRef(false);
  const [mode, setMode] = useState<"chat" | "work" | "browse">(() => {
    try {
      const v = localStorage.getItem("mark.sidebarMode");
      return v === "work" || v === "browse" ? v : "chat";
    } catch {
      return "chat";
    }
  });
  const [routeNote, setRouteNote] = useState<{ tool: string; icon: React.ReactNode; project?: { id: number; name: string }; think?: boolean } | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Chat | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [browseSessions, setBrowseSessions] = useState<{ id: string; url?: string; status?: string; name?: string }[]>([]);
  const [openTabs, setOpenTabs] = useState<{ id: number; title: string }[]>([]);

  const isPinned = (id: number) => pinned.includes(id);

  const togglePin = (id: number) => {
    setPinned((prev) => {
      const next = prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id];
      localStorage.setItem(PIN_KEY, JSON.stringify(next));
      return next;
    });
  };

  const startResize = (e: React.MouseEvent) => {
    e.preventDefault();
    draggingRef.current = true;
    const onMove = (ev: MouseEvent) => {
      const navWidth = sidebarOpen ? 256 : 64;
      const total = window.innerWidth;
      setWorkWidth(Math.min(720, Math.max(280, total - navWidth - ev.clientX)));
    };
    const onUp = () => {
      draggingRef.current = false;
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  };

  const fetchMsgs = useCallback(async (id: number) => {
    setLoadingMsgs(true);
    try {
      const detail = await chatApi.get(id);
      setMessages(detail.messages);
      const last = detail.messages[detail.messages.length - 1];
      if (last?.message_metadata?.task_id) setTaskId(last.message_metadata.task_id);
    } catch (e) { console.error(e); } finally { setLoadingMsgs(false); }
  }, []);

  const fetchProjects = useCallback(async () => {
    try { const r = await projectsApi.list({ page_size: 100 }); setProjects(r.projects); } catch {}
  }, []);

  const fetchBrowseSessions = useCallback(async () => {
    try { setBrowseSessions(await browserApi.listSessions()); } catch { setBrowseSessions([]); }
  }, []);

  // --- Tab management (no forward deps) ---
  const openTab = useCallback((chatId: number, title?: string) => {
    setOpenTabs((prev) => {
      if (prev.some((t) => t.id === chatId)) return prev;
      return [...prev, { id: chatId, title: title || "New session" }];
    });
  }, []);

  const handleNewChat = useCallback(async () => {
    const c = await chatApi.create({ project_id: projectId });
    setChats((prev) => [c, ...prev]);
    setActiveChatId(c.id);
    setMessages([]);
    setRouteNote(null);
    openTab(c.id, c.title || "New session");
  }, [projectId, openTab]);

  const closeTab = useCallback((chatId: number) => {
    setOpenTabs((prev) => {
      const next = prev.filter((t) => t.id !== chatId);
      if (activeChatId === chatId && next.length > 0) {
        setActiveChatId(next[next.length - 1].id);
      } else if (next.length === 0) {
        // All tabs closed — create a fresh chat
        chatApi.create({}).then((c) => {
          setChats((prev) => [c, ...prev]);
          setActiveChatId(c.id);
          setMessages([]);
          setOpenTabs([{ id: c.id, title: c.title || "New session" }]);
        });
      }
      return next;
    });
  }, [activeChatId]);

  const handleTabSelect = useCallback((chatId: number) => {
    setActiveChatId(chatId);
  }, []);

  const handleNewTab = useCallback(async () => {
    try {
      const c = await chatApi.create({ project_id: projectId });
      setChats((prev) => [c, ...prev]);
      setActiveChatId(c.id);
      setMessages([]);
      openTab(c.id, c.title || "New session");
    } catch {
      toast.add({ title: "Couldn't create new session", type: "error" });
    }
  }, [projectId, openTab]);

  // --- Data fetching (depends on openTab) ---
  const fetchChats = useCallback(async () => {
    setLoadingChats(true);
    try {
      const res = await chatApi.list({ page: 1, page_size: 50 });
      setChats(res.chats);
      setPinned(loadPinned());
      if (!activeChatId && res.chats.length) {
        setActiveChatId(res.chats[0].id);
        openTab(res.chats[0].id, res.chats[0].title ?? undefined);
      }
      if (!res.chats.length) {
        const c = await chatApi.create({});
        setChats([c]);
        setActiveChatId(c.id);
        openTab(c.id, c.title || "New session");
      }
    } catch (e) { console.error(e); } finally { setLoadingChats(false); }
  }, [activeChatId, openTab]);

  useEffect(() => { try { localStorage.setItem("mark.sidebarMode", mode); } catch {} }, [mode]);
  useEffect(() => {
    if (mode === "browse") {
      setWorkOpen(true);
      fetchBrowseSessions();
    } else {
      setWorkOpen(false);
    }
  }, [mode, fetchBrowseSessions]);

  useEffect(() => { fetchChats(); fetchProjects(); }, [fetchChats, fetchProjects]);
  useEffect(() => { if (activeChatId) fetchMsgs(activeChatId); }, [activeChatId, fetchMsgs]);
  useEffect(() => { if (taskUpdate && activeChatId) fetchMsgs(activeChatId); }, [taskUpdate, activeChatId, fetchMsgs]);

  const handleNewProject = async () => {
    try {
      const p = await projectsApi.create({ name: "New project" });
      setProjectId(p.id);
      fetchProjects();
      setMode("work");
      window.location.href = `/projects/${p.id}`;
    } catch {
      toast.add({ title: "Couldn't create project", type: "error" });
    }
  };

  const confirmDeleteChat = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await chatApi.delete(deleteTarget.id);
      setChats((prev) => prev.filter((c) => c.id !== deleteTarget.id));
      if (activeChatId === deleteTarget.id) {
        setActiveChatId(chats.find((c) => c.id !== deleteTarget.id)?.id || null);
        setMessages([]);
      }
      toast.add({ title: "Chat deleted", type: "success" });
    } catch {
      toast.add({ title: "Couldn't delete chat", type: "error" });
    } finally {
      setDeleting(false);
      setDeleteTarget(null);
    }
  };

  const ensureProject = async (text: string, routeTool: string) => {
    if (projectId !== undefined) return undefined;
    if (mode !== "work" && routeTool !== "Build something") return undefined;
    try {
      const created = await projectsApi.create({ name: suggestProjectName(text) });
      setProjectId(created.id);
      toast.add({
        title: "Project created for you",
        description: `“${created.name}” — Mark routed this request there.`,
        type: "success",
        timeout: 8000,
        actionProps: { children: "Open", onClick: () => { window.location.href = `/projects/${created.id}`; } },
      });
      return created;
    } catch {
      return undefined;
    }
  };

  const handleSend = async (text: string, opts?: { think?: boolean }) => {
    if (!activeChatId) return;
    setSending(true);
    try {
      const route = routeIntent(text);
      const created = await ensureProject(text, route.tool);
      const targetProjectId = created?.id ?? projectId;
      setRouteNote({
        tool: route.tool,
        icon: route.icon,
        think: opts?.think,
        project: created ? { id: created.id, name: created.name } : undefined,
      });
      if (created) fetchProjects();
      await chatApi.sendMessage(activeChatId, { content: text, project_id: targetProjectId });
      await fetchMsgs(activeChatId);
      const res = await chatApi.list({ page: 1, page_size: 50 });
      setChats(res.chats);
    } catch (e) {
      console.error(e);
      toast.add({ title: "Send failed", description: "Mark couldn't process that request.", type: "error" });
    } finally { setSending(false); }
  };

  const handleFile = async (f: File) => {
    try {
      const uploaded = await filesApi.uploadFile(f, { project_id: projectId });
      if (activeChatId) {
        await chatApi.sendMessage(activeChatId, { content: `[File: ${uploaded.original_name}]`, attachments: [uploaded.id], project_id: projectId });
        fetchMsgs(activeChatId);
      }
    } catch (e) { toast.add({ title: "Upload failed", type: "error" }); }
  };

  const handleSuggestion = (prompt: string) => handleSend(prompt);

  const handleModeChange = async (m: "chat" | "work" | "browse") => {
    if (m === mode) return;
    setMode(m);
    try {
      const c = await chatApi.create({ project_id: projectId });
      setChats((prev) => [c, ...prev]);
      setActiveChatId(c.id);
      setMessages([]);
      setRouteNote(null);
    } catch {
      toast.add({ title: "Couldn't start a new session", type: "error" });
    }
  };

  return (
    <ProtectedLayout>
      <div className="h-dvh overflow-hidden bg-zinc-50 dark:bg-zinc-950 flex">
        <Sidebar
          isOpen={sidebarOpen}
          onToggle={() => setSidebarOpen(!sidebarOpen)}
          chatData={{
            mode,
            onModeChange: handleModeChange,
            chats,
            loadingChats,
            activeChatId,
            onSelectChat: (id) => { setActiveChatId(id); openTab(id, chats.find((c) => c.id === id)?.title ?? undefined); },
            onNewChat: handleNewChat,
            pinned,
            onTogglePin: togglePin,
            onDelete: setDeleteTarget,
            projects,
            projectId,
            onSelectProject: (id) => setProjectId(id),
            onNewProject: handleNewProject,
            browseSessions,
            onRenameProject: (id, name) => {
              setProjects((prev) => prev.map((p) => p.id === id ? { ...p, name } : p));
            },
            onDeleteProject: (id) => {
              setProjects((prev) => prev.filter((p) => p.id !== id));
              if (projectId === id) setProjectId(undefined);
            },
          }}
        />
        <div className={`flex-1 flex flex-col min-w-0 transition-all ${sidebarOpen ? "ml-64" : "ml-16"}`}>
          <ChatTopBar
            tabs={openTabs.map((t) => ({ id: t.id, title: t.title, active: t.id === activeChatId }))}
            onTabSelect={handleTabSelect}
            onTabClose={closeTab}
            onTabNew={handleNewTab}
            rightPanelOpen={workOpen}
            onToggleRightPanel={() => setWorkOpen((v) => !v)}
            activeProjectName={projects.find((p) => p.id === projectId)?.name}
          />
          <div className="flex-1 flex min-h-0">
            {/* Main column */}
            <div className="flex-1 flex flex-col min-w-0 bg-zinc-50 dark:bg-zinc-950">
              {/* Slim context bar */}
              <div className="h-11 shrink-0 border-b bg-white dark:bg-zinc-900 flex items-center gap-3 px-4">
                <div className="flex-1 min-w-0 flex items-center gap-2">
                  {routeNote ? (
                    <div className="flex items-center gap-2 rounded-full border bg-white dark:bg-zinc-900 py-1 pl-3 pr-1 text-xs text-zinc-600 dark:text-zinc-300 shadow-sm">
                      <Zap className="h-3.5 w-3.5 text-blue-500" />
                      <span>Mark routed → <span className="font-medium">{routeNote.tool}</span></span>
                      {routeNote.think && (
                        <span className="rounded-full bg-blue-600/10 px-1.5 py-0.5 text-[10px] font-semibold text-blue-600">Think</span>
                      )}
                      {routeNote.project && (
                        <span className="text-muted-foreground">· project: <span className="font-medium text-zinc-800 dark:text-zinc-100">{routeNote.project.name}</span></span>
                      )}
                      <button onClick={() => setRouteNote(null)} className="rounded-full p-1 text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 hover:text-zinc-700" title="Dismiss"><X className="h-3 w-3" /></button>
                    </div>
                  ) : (
                    <span className="truncate text-xs text-zinc-400">
                      {mode === "work"
                        ? "Work mode — Mark plans, builds and runs it. Open the Agent panel to watch live."
                        : mode === "browse"
                          ? "Browse mode — Mark opens the browser, searches, reads pages and reports back live."
                          : "Chat — Mark reads your request, routes it, and does the work."}
                    </span>
                  )}
                </div>
                <select
                  value={projectId ?? ""}
                  onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : undefined)}
                  className="h-8 max-w-[180px] cursor-pointer rounded-lg border bg-transparent px-2 text-xs text-zinc-600 dark:text-zinc-300 dark:bg-zinc-900"
                  title="Project context"
                >
                  <option value="">General (no project)</option>
                  {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
                <Button
                  variant={workOpen ? "default" : "outline"}
                  size="sm"
                  className={cn("h-8 gap-1.5", workOpen && "bg-blue-600 text-white hover:bg-blue-700")}
                  onClick={() => setWorkOpen((v) => !v)}
                  title="Toggle Agent / Browser panel"
                >
                  <PanelRight className="h-3.5 w-3.5" /> Agent panel
                  {taskUpdate && <span className="animate-pulse rounded-full bg-blue-500" style={{ width: 6, height: 6 }} />}
                </Button>
              </div>

              {/* Messages */}
              <div className="flex-1 min-h-0">
                {loadingMsgs ? (
                  <div className="flex h-full items-center justify-center"><Loader2 className="h-6 w-6 animate-spin" /></div>
                ) : messages.length === 0 ? (
                  <div className="flex h-full flex-col overflow-y-auto">
                    <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6">
                      {mode === "work"
                        ? <Code2 className="h-10 w-10 text-zinc-300 dark:text-zinc-700" />
                        : mode === "browse"
                          ? <Globe className="h-10 w-10 text-zinc-300 dark:text-zinc-700" />
                          : <BrainCircuit className="h-10 w-10 text-zinc-300 dark:text-zinc-700" />}
                      <h2 className="text-2xl font-semibold tracking-tight">
                        {mode === "work" ? "What should I build?" : mode === "browse" ? "What should I browse?" : "What can I help you build?"}
                      </h2>
                      <p className="max-w-md text-center text-sm text-zinc-500">
                        {mode === "work"
                          ? "Work mode is the builder — Mark plans, writes code, runs tools, and reports back live. Just describe the app and it handles the rest."
                          : mode === "browse"
                            ? "Browse mode gives Mark a real browser — it can search the web, read pages, compare options, extract data, and bring back answers."
                            : "Describe what you want in plain words — Mark reads it, decides what's needed, and does it while you watch. No technical knowledge required."}
                      </p>
                    </div>
                    <div className="mx-auto w-full max-w-3xl px-4 pb-2">
                      <div className="flex flex-wrap justify-center gap-2">
                        {(mode === "work" ? WORK_SUGGESTIONS : mode === "browse" ? BROWSE_SUGGESTIONS : SUGGESTIONS).map((s) => (
                          <button
                            key={s.label}
                            onClick={() => handleSuggestion(s.prompt)}
                            className="group flex items-center gap-2 rounded-full border px-3.5 py-2 text-sm font-medium text-zinc-700 dark:text-zinc-300 transition-colors hover:bg-white dark:hover:bg-zinc-900 hover:border-zinc-300 dark:hover:border-zinc-700"
                          >
                            <s.icon className="h-4 w-4 text-zinc-400 group-hover:text-blue-500" />
                            {s.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <MessageList
                    messages={messages}
                    chatId={activeChatId || 0}
                    onMessagesChanged={() => fetchMsgs(activeChatId!)}
                  />
                )}
              </div>

              <ChatInput
                onSend={handleSend}
                onFile={handleFile}
                disabled={sending || !activeChatId}
                mode={mode}
                chips={mode === "work" ? WORK_CHIPS : []}
              />
              {taskId && <div className="px-3 pb-1 text-xs text-zinc-500 text-center">Pipeline: Intent → Decompose → Plan → Skill/Model → Tool → Execute → Validate → Memory → Storage | Task #{taskId} {connected ? "● WS live" : "○ WS offline"}</div>}
            </div>

            {/* Right panel — multi-tab live view (Code, Terminal, Browser, Files, Context) */}
            {workOpen && (
              <>
                <div onMouseDown={startResize} className="w-1 cursor-col-resize hover:bg-blue-400 bg-zinc-200 dark:bg-zinc-700 shrink-0" title="Drag to resize" />
                <div className="border-l shrink-0" style={{ width: workWidth }}>
                  <RightPanel
                    taskUpdate={taskUpdate ?? undefined}
                    connected={connected}
                    projectFiles={undefined}
                    onClose={() => setWorkOpen(false)}
                  />
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Delete chat confirmation */}
      <Sheet open={!!deleteTarget} onOpenChange={(o) => { if (!o) setDeleteTarget(null); }}>
        <SheetContent side="bottom" className="mx-auto max-w-md rounded-t-2xl">
          <SheetHeader>
            <SheetTitle>Delete this chat?</SheetTitle>
            <SheetDescription>
              “{deleteTarget?.title || "Untitled"}” and its messages will be permanently removed. Files and projects are kept.
            </SheetDescription>
          </SheetHeader>
          <SheetFooter>
            <SheetClose render={<Button variant="outline" />}>Cancel</SheetClose>
            <Button variant="destructive" onClick={confirmDeleteChat} disabled={deleting}>
              {deleting && <Loader2 className="h-4 w-4 animate-spin" />} Delete
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </ProtectedLayout>
  );
}