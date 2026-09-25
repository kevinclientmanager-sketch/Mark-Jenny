"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { CheckCircle2, Code2, ExternalLink, FileCode2, Globe2, Loader2, Lock, Package, Play, Rocket, RotateCcw, SquareTerminal, Smartphone, Monitor, XCircle } from "lucide-react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ProtectedLayout } from "@/components/layout/protected-layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "@/components/ui/toast";
import { buildTargets, selfBuildApi, type BuildSession } from "@/lib/api/self-build";

const targetIcons = { web: Globe2, android: Smartphone, windows: Monitor };

export default function BuildPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [prompt, setPrompt] = useState("");
  const [previewUrl, setPreviewUrl] = useState("");
  const [target, setTarget] = useState<"web" | "android" | "windows">("web");
  const [session, setSession] = useState<BuildSession | null>(null);
  const [logs, setLogs] = useState<Array<{ timestamp?: string; level?: string; message?: string }>>([]);
  const [files, setFiles] = useState<Array<{ path?: string; name?: string; size?: number }>>([]);
  const [starting, setStarting] = useState(false);
  const [access, setAccess] = useState<{ allowed: boolean; is_master: boolean } | null>(null);

  useEffect(() => { selfBuildApi.access().then(setAccess).catch(() => setAccess({ allowed: false, is_master: false })); }, []);

  const sessionId = String(session?.session_id || session?.id || "");
  const refresh = useCallback(async () => {
    if (!sessionId) return;
    try {
      const [nextSession, nextLogs, nextFiles] = await Promise.all([selfBuildApi.session(sessionId), selfBuildApi.logs(sessionId), selfBuildApi.files(sessionId)]);
      setSession(nextSession); setLogs(nextLogs.logs || []); setFiles(nextFiles.files || []);
    } catch { /* the console retains the last known state */ }
  }, [sessionId]);

  useEffect(() => { if (!sessionId) return; refresh(); const timer = window.setInterval(refresh, 1500); return () => window.clearInterval(timer); }, [sessionId, refresh]);
  const start = async () => {
    if (access && !access.allowed) return toast.add({ title: "No builder access", description: "Ask a master admin to enable the self-builder for your account.", type: "error" });
    if (!prompt.trim()) return toast.add({ title: "Describe the build", description: "Tell Mark what to create.", type: "error" });
    setStarting(true); setLogs([]); setFiles([]);
    try {
      const result = await selfBuildApi.start(prompt.trim(), target);
      setSession({ session_id: result.session_id, status: "RUNNING", user_request: prompt });
      toast.add({ title: "Build started", description: "The live console is now streaming progress.", type: "success" });
    } catch (error: any) { toast.add({ title: "Build failed to start", description: error?.message || "Try again.", type: "error" }); }
    finally { setStarting(false); }
  };

  const status = String(session?.status || "READY").toUpperCase();
  const statusIcon = status === "FAILED" ? <XCircle className="h-4 w-4 text-red-500" /> : status === "COMPLETED" || status === "SUCCESS" ? <CheckCircle2 className="h-4 w-4 text-emerald-500" /> : status === "READY" ? <SquareTerminal className="h-4 w-4 text-zinc-400" /> : <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
  const activeTarget = useMemo(() => buildTargets.find((item) => item.id === target) || buildTargets[0], [target]);

  return <ProtectedLayout><div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex"><Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} /><div className={`flex-1 min-w-0 flex flex-col transition-all ${sidebarOpen ? "ml-64" : "ml-16"}`}><Header /><main className="flex-1 overflow-auto p-4 lg:p-6"><div className="mx-auto max-w-[1500px] space-y-4">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><div className="flex items-center gap-2"><Code2 className="h-5 w-5 text-blue-500" /><h1 className="text-2xl font-semibold">Build workspace</h1><Badge variant="outline">live</Badge></div><p className="mt-1 text-sm text-zinc-500">Build, inspect, preview, package, deploy, and push from one autonomous workspace.</p></div><Button onClick={start} disabled={starting || !prompt.trim() || (access !== null && !access.allowed)} className="bg-blue-600 hover:bg-blue-700"><Play className="mr-2 h-4 w-4" />{starting ? "Starting…" : "Start build"}</Button></div>
    {access !== null && !access.allowed && (
      <div className="flex items-center gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 p-4">
        <Lock className="h-5 w-5 text-amber-600 shrink-0" />
        <div><p className="text-sm font-medium">Self-builder is locked for your account</p><p className="text-xs text-zinc-500">Only a master admin can grant access. Ask kevin.clientmanager@gmail.com or mamun.rashid5957@gmail.com to enable it for you in Settings → Admin.</p></div>
      </div>
    )}
    <div className="grid gap-4 xl:grid-cols-[minmax(320px,0.8fr)_minmax(500px,1.2fr)]">
      <Card className="overflow-hidden"><CardHeader className="border-b pb-3"><CardTitle className="text-sm">Build brief</CardTitle></CardHeader><CardContent className="space-y-4 p-4"><Textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Build a property maintenance CRM with authentication, dashboard, mobile layout, and deployment configuration…" className="min-h-32 resize-y" /><div><p className="mb-2 text-xs font-medium text-zinc-500">Output target</p><div className="grid gap-2">{buildTargets.map((item) => { const Icon = targetIcons[item.id as keyof typeof targetIcons]; return <button key={item.id} onClick={() => setTarget(item.id)} className={`flex items-start gap-3 rounded-lg border p-3 text-left transition-colors ${target === item.id ? "border-blue-500 bg-blue-500/5" : "hover:bg-zinc-100 dark:hover:bg-zinc-800"}`}><Icon className="mt-0.5 h-4 w-4 text-blue-500" /><span><span className="block text-sm font-medium">{item.label}</span><span className="block text-xs text-zinc-500">{item.detail}</span></span>{target === item.id && <CheckCircle2 className="ml-auto h-4 w-4 text-blue-500" />}</button>; })}</div></div><div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-3"><p className="text-sm font-medium">Web sandbox</p><p className="mt-1 text-xs text-zinc-500">Isolated browser-based build workspace with live logs, previews, and artifacts. Docker execution can be added later as an optional backend runtime.</p></div><div className="rounded-lg border bg-zinc-50 p-3 text-xs dark:bg-zinc-900"><p className="font-medium">{activeTarget.label} capability</p><p className="mt-1 text-zinc-500">Mark generates source and configuration, runs checks, records artifacts, and leaves the project ready for platform-specific signing or store credentials.</p></div></CardContent></Card>
      <Card className="overflow-hidden"><CardHeader className="flex-row items-center justify-between border-b pb-3"><CardTitle className="flex items-center gap-2 text-sm"><SquareTerminal className="h-4 w-4" />Live build console</CardTitle><div className="flex items-center gap-2">{statusIcon}<Badge variant="outline">{status}</Badge></div></CardHeader><CardContent className="flex min-h-[390px] flex-col p-0"><div className="flex-1 overflow-auto bg-zinc-950 p-4 font-mono text-xs text-zinc-300">{logs.length ? logs.map((log, index) => <div key={`${log.timestamp}-${index}`} className="mb-2 flex gap-3"><span className="shrink-0 text-zinc-600">{log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : "--:--:--"}</span><span className={log.level === "error" ? "text-red-400" : log.level === "success" ? "text-emerald-400" : "text-zinc-300"}>{log.message || JSON.stringify(log)}</span></div>) : <div className="flex h-full min-h-56 items-center justify-center text-zinc-600">{session ? "Waiting for build events…" : "$ Mark build output will appear here"}</div>}</div><div className="flex items-center justify-between border-t px-3 py-2 text-xs text-zinc-500"><span>{files.length} artifact{files.length === 1 ? "" : "s"} detected</span><span>{sessionId ? `Session ${sessionId.slice(0, 12)}` : "No active session"}</span></div></CardContent></Card>
    </div>
    <div className="grid gap-4 lg:grid-cols-2"><Card><CardHeader className="pb-3"><CardTitle className="flex items-center gap-2 text-sm"><Globe2 className="h-4 w-4" />Preview surface</CardTitle></CardHeader><CardContent className="space-y-3"><div className="flex gap-2"><Input value={previewUrl} onChange={(event) => setPreviewUrl(event.target.value)} placeholder="https://preview.example.com" /><Button variant="outline" onClick={() => previewUrl && window.open(previewUrl, "_blank", "noopener,noreferrer")} disabled={!previewUrl}><ExternalLink className="mr-2 h-4 w-4" />Open</Button></div>{previewUrl ? <iframe title="Build preview" src={previewUrl} className="h-56 w-full rounded-lg border bg-white" /> : <div className="flex h-56 items-center justify-center rounded-lg border border-dashed text-sm text-zinc-500">Paste a deployed or local preview URL to inspect it beside the console.</div>}</CardContent></Card><Card><CardHeader className="pb-3"><CardTitle className="flex items-center gap-2 text-sm"><Package className="h-4 w-4" />Artifacts and delivery</CardTitle></CardHeader><CardContent className="space-y-3"><div className="max-h-36 space-y-2 overflow-auto">{files.length ? files.map((file, index) => <div key={`${file.path}-${index}`} className="flex items-center gap-2 rounded-md border p-2 text-xs"><FileCode2 className="h-3.5 w-3.5 text-blue-500" /><span className="min-w-0 flex-1 truncate">{file.path || file.name}</span><span className="text-zinc-500">{file.size ? `${Math.ceil(file.size / 1024)} KB` : ""}</span></div>) : <p className="text-sm text-zinc-500">Generated files will be listed here.</p>}</div><div className="flex flex-wrap gap-2"><Button variant="outline" size="sm" disabled={!sessionId} onClick={async () => { await selfBuildApi.integrate(sessionId); toast.add({ title: "Integrated", description: "Build changes applied to the workspace.", type: "success" }); }}><Rocket className="mr-2 h-3.5 w-3.5" />Integrate</Button><Button variant="outline" size="sm" disabled={!sessionId} onClick={async () => { await selfBuildApi.rollback(sessionId); toast.add({ title: "Rolled back", description: "The latest build changes were reverted.", type: "success" }); }}><RotateCcw className="mr-2 h-3.5 w-3.5" />Rollback</Button><Badge variant="secondary" className="px-2 py-1">GitHub/Vercel via connectors</Badge></div></CardContent></Card></div>
  </div></main></div></div></ProtectedLayout>;
}
