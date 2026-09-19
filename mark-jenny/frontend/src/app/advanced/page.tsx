"use client";
import { useState, useEffect } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ProtectedLayout } from "@/components/layout/protected-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/toast";
import { advancedApi } from "@/lib/api/advanced";
import {
  Zap, GitBranch, RotateCcw, Users, Brain, AlertTriangle, Loader2, CheckCircle
} from "lucide-react";

interface Failure { id: number; task_id: number; error: string; created_at: string; }
interface SpecializedAgent { name: string; role: string; status: string; }

export default function AdvancedPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [failures, setFailures] = useState<Failure[]>([]);
  const [agents, setAgents] = useState<SpecializedAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"overview" | "failures" | "agents">("overview");
  const [taskId, setTaskId] = useState("");
  const [errorText, setErrorText] = useState("");
  const [recovering, setRecovering] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [f, a] = await Promise.all([
        advancedApi.getFailures().catch(() => []),
        advancedApi.listAgents().catch(() => []),
      ]);
      setFailures(Array.isArray(f) ? f : []);
      setAgents(Array.isArray(a) ? a : []);
    } catch {}
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleRecover = async () => {
    if (!taskId || !errorText) return;
    setRecovering(true);
    try {
      await advancedApi.recover(Number(taskId), errorText);
      toast.add({ title: "Recovery initiated", type: "success" });
      setTaskId(""); setErrorText("");
      load();
    } catch { toast.add({ title: "Recovery failed", type: "error" }); }
    finally { setRecovering(false); }
  };

  const handleSelfCheck = async () => {
    if (!taskId) return;
    try {
      await advancedApi.selfCheck(Number(taskId));
      toast.add({ title: "Self-check complete", type: "success" });
    } catch { toast.add({ title: "Self-check failed", type: "error" }); }
  };

  const tabs = [
    { id: "overview" as const, label: "Overview", icon: Zap },
    { id: "failures" as const, label: `Failures (${failures.length})`, icon: AlertTriangle },
    { id: "agents" as const, label: `Agents (${agents.length})`, icon: Users },
  ];

  return (
    <ProtectedLayout>
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex">
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <div className={`flex-1 flex flex-col min-w-0 transition-all ${sidebarOpen ? "ml-64" : "ml-16"}`}>
          <Header />
          <main className="flex-1 p-6 overflow-auto max-w-6xl mx-auto w-full">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-2xl font-semibold flex items-center gap-2"><Zap className="h-6 w-6" /> Advanced</h1>
                <p className="text-sm text-zinc-500 mt-1">Recovery, self-check, checkpointing, and specialized agents.</p>
              </div>
              <Button variant="outline" onClick={load}>Refresh</Button>
            </div>

            <div className="flex gap-1 mb-6 border-b">
              {tabs.map(t => (
                <button key={t.id} onClick={() => setActiveTab(t.id)}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === t.id ? "border-zinc-900 text-zinc-900 dark:border-zinc-100 dark:text-zinc-100" : "border-transparent text-zinc-500 hover:text-zinc-700"
                  }`}>
                  <t.icon className="h-4 w-4" /> {t.label}
                </button>
              ))}
            </div>

            {loading ? (
              <div className="flex justify-center p-12"><Loader2 className="h-6 w-6 animate-spin" /></div>
            ) : activeTab === "overview" ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card>
                  <CardHeader><CardTitle className="text-base flex items-center gap-2"><RotateCcw className="h-4 w-4" /> Task Recovery</CardTitle></CardHeader>
                  <CardContent className="space-y-3">
                    <Input placeholder="Task ID" value={taskId} onChange={e => setTaskId(e.target.value)} type="number" />
                    <textarea placeholder="Error message" value={errorText} onChange={e => setErrorText(e.target.value)}
                      className="w-full min-h-[60px] px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800" />
                    <div className="flex gap-2">
                      <Button onClick={handleRecover} disabled={recovering || !taskId || !errorText}>
                        {recovering ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <RotateCcw className="h-4 w-4 mr-2" />} Recover
                      </Button>
                      <Button variant="outline" onClick={handleSelfCheck} disabled={!taskId}>
                        <Brain className="h-4 w-4 mr-2" /> Self-Check
                      </Button>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader><CardTitle className="text-base flex items-center gap-2"><Users className="h-4 w-4" /> Specialized Agents</CardTitle></CardHeader>
                  <CardContent>
                    {agents.length === 0 ? <p className="text-sm text-zinc-500">No agents registered.</p> : (
                      <div className="space-y-2">
                        {agents.slice(0, 5).map((a, i) => (
                          <div key={i} className="flex items-center justify-between text-sm">
                            <span className="font-medium">{a.name}</span>
                            <Badge variant={a.status === "active" ? "default" : "secondary"} className="text-xs">{a.status}</Badge>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
                <Card className="md:col-span-2">
                  <CardHeader><CardTitle className="text-base">Quick Actions</CardTitle></CardHeader>
                  <CardContent className="flex flex-wrap gap-2">
                    <Button variant="outline" size="sm" onClick={() => setActiveTab("failures")}>
                      <AlertTriangle className="h-4 w-4 mr-2" /> View Failures
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => setActiveTab("agents")}>
                      <Users className="h-4 w-4 mr-2" /> Manage Agents
                    </Button>
                  </CardContent>
                </Card>
              </div>
            ) : activeTab === "failures" ? (
              failures.length === 0 ? (
                <Card className="p-12 text-center text-zinc-500">
                  <CheckCircle className="h-12 w-12 mx-auto mb-3 text-zinc-300" />
                  <p className="text-lg font-medium">No failures recorded</p>
                </Card>
              ) : (
                <div className="space-y-2">
                  {failures.map(f => (
                    <Card key={f.id}>
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="text-sm font-medium">Task #{f.task_id}</p>
                            <p className="text-sm text-red-600 mt-1">{f.error}</p>
                            <span className="text-xs text-zinc-400">{new Date(f.created_at).toLocaleString()}</span>
                          </div>
                          <Button variant="ghost" size="sm" onClick={async () => {
                            setTaskId(String(f.task_id)); setErrorText(f.error); setActiveTab("overview");
                          }}>Use</Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )
            ) : (
              agents.length === 0 ? (
                <Card className="p-12 text-center text-zinc-500">No agents found.</Card>
              ) : (
                <div className="space-y-2">
                  {agents.map((a, i) => (
                    <Card key={i}>
                      <CardContent className="p-4 flex items-center justify-between">
                        <div>
                          <p className="font-medium">{a.name}</p>
                          <p className="text-sm text-zinc-500">{a.role}</p>
                        </div>
                        <Badge variant={a.status === "active" ? "default" : "secondary"}>{a.status}</Badge>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )
            )}
          </main>
        </div>
      </div>
    </ProtectedLayout>
  );
}
