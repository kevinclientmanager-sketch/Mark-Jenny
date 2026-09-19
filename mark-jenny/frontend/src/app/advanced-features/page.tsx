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
import { advancedFeaturesApi } from "@/lib/api/advancedFeatures";
import {
  Layers, GitBranch, Clock, CheckCircle, Image as ImageIcon, Loader2, Play, Eye
} from "lucide-react";

export default function AdvancedFeaturesPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeTab, setActiveTab] = useState<"blueprints" | "snapshots" | "knowledge">("blueprints");
  const [blueprints, setBlueprints] = useState<any[]>([]);
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [knowledgeGraph, setKnowledgeGraph] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [simPrompt, setSimPrompt] = useState("");
  const [simulating, setSimulating] = useState(false);
  const [simResult, setSimResult] = useState<any>(null);

  const load = async () => {
    setLoading(true);
    try {
      const [bp, sg, kg] = await Promise.all([
        advancedFeaturesApi.listBlueprints().catch(() => []),
        advancedFeaturesApi.listSnapshots(0).catch(() => []),
        advancedFeaturesApi.knowledgeGraph().catch(() => null),
      ]);
      setBlueprints(Array.isArray(bp) ? bp : []);
      setSnapshots(Array.isArray(sg) ? sg : []);
      setKnowledgeGraph(kg);
    } catch {}
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleSimulate = async () => {
    if (!simPrompt.trim()) return;
    setSimulating(true);
    try {
      const r = await advancedFeaturesApi.simulate(simPrompt);
      setSimResult(r);
      toast.add({ title: "Simulation complete", type: "success" });
    } catch { toast.add({ title: "Simulation failed", type: "error" }); }
    finally { setSimulating(false); }
  };

  const handleDryRun = async () => {
    if (!simPrompt.trim()) return;
    setSimulating(true);
    try {
      const r = await advancedFeaturesApi.dryRun(simPrompt);
      setSimResult(r);
      toast.add({ title: "Dry run complete", type: "success" });
    } catch { toast.add({ title: "Dry run failed", type: "error" }); }
    finally { setSimulating(false); }
  };

  const tabs = [
    { id: "blueprints" as const, label: "Blueprints", icon: Layers },
    { id: "snapshots" as const, label: "Snapshots", icon: ImageIcon },
    { id: "knowledge" as const, label: "Knowledge Graph", icon: GitBranch },
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
                <h1 className="text-2xl font-semibold flex items-center gap-2"><Layers className="h-6 w-6" /> Advanced Features</h1>
                <p className="text-sm text-zinc-500 mt-1">Blueprints, snapshots, knowledge graph, and simulation.</p>
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
            ) : activeTab === "blueprints" ? (
              <div className="space-y-4">
                <Card>
                  <CardHeader><CardTitle className="text-base">Simulate / Dry Run</CardTitle></CardHeader>
                  <CardContent className="space-y-3">
                    <textarea placeholder="Describe what the agent should do..." value={simPrompt} onChange={e => setSimPrompt(e.target.value)}
                      className="w-full min-h-[80px] px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800" />
                    <div className="flex gap-2">
                      <Button onClick={handleSimulate} disabled={simulating || !simPrompt.trim()}>
                        {simulating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Play className="h-4 w-4 mr-2" />} Simulate
                      </Button>
                      <Button variant="outline" onClick={handleDryRun} disabled={simulating || !simPrompt.trim()}>
                        <Eye className="h-4 w-4 mr-2" /> Dry Run
                      </Button>
                    </div>
                    {simResult && (
                      <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800 text-sm">
                        <pre className="whitespace-pre-wrap">{JSON.stringify(simResult, null, 2)}</pre>
                      </div>
                    )}
                  </CardContent>
                </Card>
                {blueprints.length === 0 ? (
                  <Card className="p-8 text-center text-zinc-500">No blueprints yet. Complete a task to auto-generate one.</Card>
                ) : (
                  <div className="space-y-2">
                    {blueprints.map((bp: any, i: number) => (
                      <Card key={i}>
                        <CardContent className="p-4">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="font-medium">{bp.name || `Blueprint #${bp.id || i + 1}`}</p>
                              <p className="text-sm text-zinc-500">{bp.description || bp.task_summary || "Auto-generated blueprint"}</p>
                            </div>
                            <Badge variant="secondary">{bp.status || "saved"}</Badge>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            ) : activeTab === "snapshots" ? (
              snapshots.length === 0 ? (
                <Card className="p-12 text-center text-zinc-500">
                  <ImageIcon className="h-12 w-12 mx-auto mb-3 text-zinc-300" />
                  <p className="text-lg font-medium">No snapshots yet</p>
                  <p className="text-sm mt-1">Create snapshots to save project state.</p>
                </Card>
              ) : (
                <div className="space-y-2">
                  {snapshots.map((s: any, i: number) => (
                    <Card key={i}>
                      <CardContent className="p-4 flex items-center justify-between">
                        <div>
                          <p className="font-medium">{s.name || `Snapshot ${s.id || i + 1}`}</p>
                          <span className="text-xs text-zinc-400">{new Date(s.created_at).toLocaleString()}</span>
                        </div>
                        <div className="flex gap-2">
                          <Button variant="outline" size="sm">Restore</Button>
                          <Button variant="outline" size="sm">Diff</Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )
            ) : (
              !knowledgeGraph ? (
                <Card className="p-12 text-center text-zinc-500">No knowledge graph data available.</Card>
              ) : (
                <Card>
                  <CardHeader><CardTitle className="text-base">Knowledge Graph</CardTitle></CardHeader>
                  <CardContent>
                    <pre className="text-sm whitespace-pre-wrap">{JSON.stringify(knowledgeGraph, null, 2)}</pre>
                  </CardContent>
                </Card>
              )
            )}
          </main>
        </div>
      </div>
    </ProtectedLayout>
  );
}
