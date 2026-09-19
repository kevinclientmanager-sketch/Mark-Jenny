"use client";
import { useState, useEffect, useCallback } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ProtectedLayout } from "@/components/layout/protected-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/toast";
import { advancedApi } from "@/lib/api/advanced";
import { advancedFeaturesApi } from "@/lib/api/advancedFeatures";
import {
  Zap, GitBranch, RotateCcw, Users, Brain, AlertTriangle, Loader2, CheckCircle,
  Layers, ImageIcon, Eye, Play, Trash2, RefreshCw, Network, ChevronRight
} from "lucide-react";

type Tab = "recovery" | "blueprints" | "snapshots" | "agents" | "knowledge" | "simulate";

interface Failure { id: number; task_id: number; error: string; created_at: string; }
interface SpecializedAgent { name: string; role: string; status: string; }

export default function AdvancedPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>("recovery");
  const [loading, setLoading] = useState(true);

  // Recovery state
  const [failures, setFailures] = useState<Failure[]>([]);
  const [taskId, setTaskId] = useState("");
  const [errorText, setErrorText] = useState("");
  const [recovering, setRecovering] = useState(false);

  // Agents state
  const [agents, setAgents] = useState<SpecializedAgent[]>([]);

  // Blueprints state
  const [blueprints, setBlueprints] = useState<any[]>([]);
  const [selectedBlueprint, setSelectedBlueprint] = useState<any>(null);

  // Snapshots state
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [snapshotName, setSnapshotName] = useState("");
  const [snapshotProjectId, setSnapshotProjectId] = useState("");
  const [creatingSnapshot, setCreatingSnapshot] = useState(false);

  // Knowledge graph state
  const [knowledgeGraph, setKnowledgeGraph] = useState<any>(null);
  const [kgProjectId, setKgProjectId] = useState("");

  // Simulate state
  const [simPrompt, setSimPrompt] = useState("");
  const [simProjectId, setSimProjectId] = useState("");
  const [simulating, setSimulating] = useState(false);
  const [simResult, setSimResult] = useState<any>(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [f, a, bp, kg] = await Promise.all([
        advancedApi.getFailures().catch(() => []),
        advancedApi.listAgents().catch(() => []),
        advancedFeaturesApi.listBlueprints().catch(() => []),
        advancedFeaturesApi.knowledgeGraph().catch(() => null),
      ]);
      setFailures(Array.isArray(f) ? f : []);
      setAgents(Array.isArray(a) ? a : []);
      setBlueprints(Array.isArray(bp) ? bp : []);
      setKnowledgeGraph(kg);
    } catch {}
    finally { setLoading(false); }
  }, []);

  const loadSnapshots = useCallback(async (projectId: number) => {
    try {
      const sg = await advancedFeaturesApi.listSnapshots(projectId);
      setSnapshots(Array.isArray(sg) ? sg : []);
    } catch { setSnapshots([]); }
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);
  useEffect(() => {
    if (activeTab === "snapshots" && snapshotProjectId) {
      loadSnapshots(Number(snapshotProjectId));
    }
  }, [activeTab, snapshotProjectId, loadSnapshots]);

  // Recovery handlers
  const handleRecover = async () => {
    if (!taskId || !errorText) return;
    setRecovering(true);
    try {
      await advancedApi.recover(Number(taskId), errorText);
      toast.add({ title: "Recovery initiated", type: "success" });
      setTaskId(""); setErrorText("");
      loadAll();
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

  // Snapshot handlers
  const handleCreateSnapshot = async () => {
    if (!snapshotProjectId || !snapshotName.trim()) return;
    setCreatingSnapshot(true);
    try {
      await advancedFeaturesApi.createSnapshot(Number(snapshotProjectId), snapshotName);
      toast.add({ title: "Snapshot created", type: "success" });
      setSnapshotName("");
      loadSnapshots(Number(snapshotProjectId));
    } catch { toast.add({ title: "Snapshot failed", type: "error" }); }
    finally { setCreatingSnapshot(false); }
  };

  const handleRestoreSnapshot = async (snapshotId: string) => {
    if (!snapshotProjectId) return;
    try {
      await advancedFeaturesApi.restoreSnapshot(Number(snapshotProjectId), snapshotId);
      toast.add({ title: "Snapshot restored", type: "success" });
    } catch { toast.add({ title: "Restore failed", type: "error" }); }
  };

  // Knowledge graph
  const loadKnowledgeGraph = async () => {
    try {
      const kg = await advancedFeaturesApi.knowledgeGraph(kgProjectId ? Number(kgProjectId) : undefined);
      setKnowledgeGraph(kg);
    } catch { toast.add({ title: "Failed to load knowledge graph", type: "error" }); }
  };

  // Simulate handlers
  const handleSimulate = async () => {
    if (!simPrompt.trim()) return;
    setSimulating(true);
    try {
      const r = await advancedFeaturesApi.simulate(simPrompt, simProjectId ? Number(simProjectId) : undefined);
      setSimResult(r);
      toast.add({ title: "Simulation complete", type: "success" });
    } catch { toast.add({ title: "Simulation failed", type: "error" }); }
    finally { setSimulating(false); }
  };

  const handleDryRun = async () => {
    if (!simPrompt.trim()) return;
    setSimulating(true);
    try {
      const r = await advancedFeaturesApi.dryRun(simPrompt, simProjectId ? Number(simProjectId) : undefined);
      setSimResult(r);
      toast.add({ title: "Dry run complete", type: "success" });
    } catch { toast.add({ title: "Dry run failed", type: "error" }); }
    finally { setSimulating(false); }
  };

  const tabs: { id: Tab; label: string; icon: any; count?: number }[] = [
    { id: "recovery", label: "Recovery", icon: RotateCcw, count: failures.length },
    { id: "blueprints", label: "Blueprints", icon: Layers, count: blueprints.length },
    { id: "snapshots", label: "Snapshots", icon: ImageIcon },
    { id: "agents", label: "Agents", icon: Users, count: agents.length },
    { id: "knowledge", label: "Knowledge", icon: Network },
    { id: "simulate", label: "Simulate", icon: Play },
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
                <p className="text-sm text-zinc-500 mt-1">Recovery, blueprints, snapshots, agents, knowledge graph, and simulation.</p>
              </div>
              <Button variant="outline" onClick={loadAll} className="gap-2"><RefreshCw className="h-4 w-4" /> Refresh</Button>
            </div>

            <div className="flex gap-1 mb-6 border-b overflow-x-auto">
              {tabs.map(t => (
                <button key={t.id} onClick={() => setActiveTab(t.id)}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                    activeTab === t.id ? "border-zinc-900 text-zinc-900 dark:border-zinc-100 dark:text-zinc-100" : "border-transparent text-zinc-500 hover:text-zinc-700"
                  }`}>
                  <t.icon className="h-4 w-4" /> {t.label}
                  {t.count !== undefined && <Badge variant="secondary" className="text-xs ml-1">{t.count}</Badge>}
                </button>
              ))}
            </div>

            {loading ? (
              <div className="flex justify-center p-12"><Loader2 className="h-6 w-6 animate-spin" /></div>
            ) : activeTab === "recovery" ? (
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
                  <CardHeader><CardTitle className="text-base">Recent Failures</CardTitle></CardHeader>
                  <CardContent>
                    {failures.length === 0 ? (
                      <div className="text-center py-4"><CheckCircle className="h-8 w-8 mx-auto text-green-500 mb-2" /><p className="text-sm text-zinc-500">No failures</p></div>
                    ) : (
                      <div className="space-y-2 max-h-64 overflow-auto">
                        {failures.slice(0, 10).map(f => (
                          <div key={f.id} className="flex items-start justify-between text-sm p-2 rounded-lg bg-zinc-50 dark:bg-zinc-800">
                            <div className="min-w-0">
                              <p className="font-medium">Task #{f.task_id}</p>
                              <p className="text-red-600 text-xs truncate">{f.error}</p>
                            </div>
                            <Button variant="ghost" size="sm" className="shrink-0" onClick={() => {
                              setTaskId(String(f.task_id)); setErrorText(f.error);
                            }}>Use</Button>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            ) : activeTab === "blueprints" ? (
              <div className="space-y-4">
                {blueprints.length === 0 ? (
                  <Card className="p-12 text-center text-zinc-500">
                    <Layers className="h-12 w-12 mx-auto mb-3 text-zinc-300" />
                    <p className="text-lg font-medium">No blueprints yet</p>
                    <p className="text-sm mt-1">Complete tasks to auto-generate reusable blueprints.</p>
                  </Card>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {blueprints.map((bp: any, i: number) => (
                      <Card key={i} className="hover:shadow-md transition-shadow cursor-pointer"
                        onClick={() => setSelectedBlueprint(selectedBlueprint?.id === bp.id ? null : bp)}>
                        <CardHeader className="pb-2">
                          <div className="flex items-center justify-between">
                            <CardTitle className="text-base">{bp.name || `Blueprint ${bp.id || i + 1}`}</CardTitle>
                            <Badge variant="secondary">{bp.status || "saved"}</Badge>
                          </div>
                        </CardHeader>
                        <CardContent>
                          <p className="text-sm text-zinc-500">{bp.description || bp.task_summary || "Auto-generated from completed task."}</p>
                          {bp.steps && <p className="text-xs text-zinc-400 mt-2">{Array.isArray(bp.steps) ? bp.steps.length : "?"} steps</p>}
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
                {selectedBlueprint && (
                  <Card>
                    <CardHeader><CardTitle className="text-base flex items-center gap-2"><Eye className="h-4 w-4" /> Blueprint Detail</CardTitle></CardHeader>
                    <CardContent>
                      <pre className="text-sm whitespace-pre-wrap bg-zinc-50 dark:bg-zinc-800 p-3 rounded-lg max-h-64 overflow-auto">
                        {JSON.stringify(selectedBlueprint, null, 2)}
                      </pre>
                    </CardContent>
                  </Card>
                )}
              </div>
            ) : activeTab === "snapshots" ? (
              <div className="space-y-4">
                <Card>
                  <CardHeader><CardTitle className="text-base">Create Snapshot</CardTitle></CardHeader>
                  <CardContent className="flex gap-3">
                    <Input placeholder="Project ID" value={snapshotProjectId} onChange={e => setSnapshotProjectId(e.target.value)} type="number" className="w-32" />
                    <Input placeholder="Snapshot name" value={snapshotName} onChange={e => setSnapshotName(e.target.value)} className="flex-1" />
                    <Button onClick={handleCreateSnapshot} disabled={creatingSnapshot || !snapshotProjectId || !snapshotName.trim()}>
                      {creatingSnapshot ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <ImageIcon className="h-4 w-4 mr-2" />} Create
                    </Button>
                  </CardContent>
                </Card>
                {!snapshotProjectId ? (
                  <Card className="p-8 text-center text-zinc-500">Enter a project ID to view snapshots.</Card>
                ) : snapshots.length === 0 ? (
                  <Card className="p-8 text-center text-zinc-500">No snapshots for this project.</Card>
                ) : (
                  <div className="space-y-2">
                    {snapshots.map((s: any, i: number) => (
                      <Card key={i}>
                        <CardContent className="p-4 flex items-center justify-between">
                          <div>
                            <p className="font-medium">{s.name || `Snapshot ${i + 1}`}</p>
                            <span className="text-xs text-zinc-400">{new Date(s.created_at).toLocaleString()}</span>
                          </div>
                          <Button variant="outline" size="sm" onClick={() => handleRestoreSnapshot(s.id)}>Restore</Button>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            ) : activeTab === "agents" ? (
              agents.length === 0 ? (
                <Card className="p-12 text-center text-zinc-500">
                  <Users className="h-12 w-12 mx-auto mb-3 text-zinc-300" />
                  <p className="text-lg font-medium">No agents registered</p>
                </Card>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {agents.map((a, i) => (
                    <Card key={i} className="p-4">
                      <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                          <Brain className="h-5 w-5 text-blue-600" />
                        </div>
                        <div>
                          <p className="font-medium">{a.name}</p>
                          <p className="text-xs text-zinc-500">{a.role}</p>
                        </div>
                        <Badge variant={a.status === "active" ? "default" : "secondary"} className="ml-auto text-xs">{a.status}</Badge>
                      </div>
                    </Card>
                  ))}
                </div>
              )
            ) : activeTab === "knowledge" ? (
              <div className="space-y-4">
                <Card>
                  <CardContent className="p-4 flex gap-3">
                    <Input placeholder="Project ID (optional)" value={kgProjectId} onChange={e => setKgProjectId(e.target.value)} type="number" className="w-48" />
                    <Button onClick={loadKnowledgeGraph}><Network className="h-4 w-4 mr-2" /> Load Graph</Button>
                  </CardContent>
                </Card>
                {!knowledgeGraph ? (
                  <Card className="p-12 text-center text-zinc-500">
                    <Network className="h-12 w-12 mx-auto mb-3 text-zinc-300" />
                    <p className="text-lg font-medium">No knowledge graph loaded</p>
                    <p className="text-sm mt-1">Enter a project ID and click Load to view the knowledge graph.</p>
                  </Card>
                ) : (
                  <Card>
                    <CardHeader><CardTitle className="text-base">Knowledge Graph</CardTitle></CardHeader>
                    <CardContent>
                      <pre className="text-sm whitespace-pre-wrap bg-zinc-50 dark:bg-zinc-800 p-3 rounded-lg max-h-96 overflow-auto">
                        {JSON.stringify(knowledgeGraph, null, 2)}
                      </pre>
                    </CardContent>
                  </Card>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                <Card>
                  <CardHeader><CardTitle className="text-base">Simulate / Dry Run</CardTitle></CardHeader>
                  <CardContent className="space-y-3">
                    <textarea placeholder="Describe what the agent should do..." value={simPrompt} onChange={e => setSimPrompt(e.target.value)}
                      className="w-full min-h-[100px] px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800" />
                    <div className="flex gap-3">
                      <Input placeholder="Project ID (optional)" value={simProjectId} onChange={e => setSimProjectId(e.target.value)} type="number" className="w-48" />
                      <Button onClick={handleSimulate} disabled={simulating || !simPrompt.trim()}>
                        {simulating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Play className="h-4 w-4 mr-2" />} Simulate
                      </Button>
                      <Button variant="outline" onClick={handleDryRun} disabled={simulating || !simPrompt.trim()}>
                        <Eye className="h-4 w-4 mr-2" /> Dry Run
                      </Button>
                    </div>
                  </CardContent>
                </Card>
                {simResult && (
                  <Card>
                    <CardHeader><CardTitle className="text-base">Result</CardTitle></CardHeader>
                    <CardContent>
                      <pre className="text-sm whitespace-pre-wrap bg-zinc-50 dark:bg-zinc-800 p-3 rounded-lg max-h-96 overflow-auto">
                        {JSON.stringify(simResult, null, 2)}
                      </pre>
                    </CardContent>
                  </Card>
                )}
              </div>
            )}
          </main>
        </div>
      </div>
    </ProtectedLayout>
  );
}
