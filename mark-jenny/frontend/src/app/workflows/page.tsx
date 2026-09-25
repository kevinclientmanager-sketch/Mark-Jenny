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
import { api } from "@/lib/api/client";
import {
  Workflow, Play, Loader2, CheckCircle, XCircle, Clock, Plus, ChevronDown
} from "lucide-react";

interface WorkflowItem {
  id: number;
  name: string;
  description: string;
  status: string;
  steps: number;
  created_at: string;
  last_run: string | null;
}

export default function WorkflowsPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [workflows, setWorkflows] = useState<WorkflowItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [creating, setCreating] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.get<{ workflows: WorkflowItem[] }>("/workflows").catch(() => ({ workflows: [] }));
      setWorkflows(res.workflows || []);
    } catch {}
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await api.post("/workflows", { name: newName, description: newDesc });
      toast.add({ title: "Workflow created", type: "success" });
      setShowCreate(false); setNewName(""); setNewDesc("");
      load();
    } catch { toast.add({ title: "Create failed", type: "error" }); }
    finally { setCreating(false); }
  };

  const statusIcon = (s: string) => {
    switch (s) {
      case "completed": return <CheckCircle className="h-4 w-4 text-green-600" />;
      case "running": return <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />;
      case "failed": return <XCircle className="h-4 w-4 text-red-600" />;
      default: return <Clock className="h-4 w-4 text-zinc-400" />;
    }
  };

  return (
    <ProtectedLayout>
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex">
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <div className={`flex-1 flex flex-col min-w-0 transition-all ${sidebarOpen ? "ml-64" : "ml-16"}`}>
          <Header />
          <main className="flex-1 p-6 overflow-auto max-w-6xl mx-auto w-full">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-2xl font-semibold flex items-center gap-2"><Workflow className="h-6 w-6" /> Workflows</h1>
                <p className="text-sm text-zinc-500 mt-1">Multi-step agent workflows with checkpoints and recovery.</p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={load}>Refresh</Button>
                <Button onClick={() => setShowCreate(!showCreate)} className="gap-2">
                  <Plus className="h-4 w-4" /> New Workflow
                </Button>
              </div>
            </div>

            {showCreate && (
              <Card className="mb-6">
                <CardHeader><CardTitle className="text-base">Create Workflow</CardTitle></CardHeader>
                <CardContent className="space-y-3">
                  <Input placeholder="Workflow name" value={newName} onChange={e => setNewName(e.target.value)} />
                  <textarea placeholder="Description (optional)" value={newDesc} onChange={e => setNewDesc(e.target.value)}
                    className="w-full min-h-[60px] px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800" />
                  <div className="flex gap-2">
                    <Button onClick={handleCreate} disabled={creating || !newName.trim()}>
                      {creating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Plus className="h-4 w-4 mr-2" />} Create
                    </Button>
                    <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {loading ? (
              <div className="flex justify-center p-12"><Loader2 className="h-6 w-6 animate-spin" /></div>
            ) : workflows.length === 0 ? (
              <Card className="p-12 text-center text-zinc-500">
                <Workflow className="h-12 w-12 mx-auto mb-3 text-zinc-300" />
                <p className="text-lg font-medium">No workflows yet</p>
                <p className="text-sm mt-1">Create a workflow to chain multiple agent steps.</p>
              </Card>
            ) : (
              <div className="space-y-3">
                {workflows.map(w => (
                  <Card key={w.id} className="hover:shadow-sm transition-shadow">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          {statusIcon(w.status)}
                          <div>
                            <p className="font-medium">{w.name}</p>
                            <p className="text-sm text-zinc-500">{w.description || "No description"}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-zinc-400">
                          <span>{w.steps} steps</span>
                          {w.last_run && <span>Last: {new Date(w.last_run).toLocaleDateString()}</span>}
                          <Badge variant={w.status === "completed" ? "default" : w.status === "running" ? "secondary" : "outline"}>
                            {w.status}
                          </Badge>
                          <Button variant="ghost" size="sm"><Play className="h-4 w-4" /></Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </main>
        </div>
      </div>
    </ProtectedLayout>
  );
}


