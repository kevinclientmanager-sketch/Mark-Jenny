"use client";
import { useState, useEffect, useCallback } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ProtectedLayout } from "@/components/layout/protected-layout";
import { memoryApi, Memory, MemoryType } from "@/lib/api/memory";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/components/ui/toast";
import {
  Brain, Plus, Trash2, ToggleLeft, ToggleRight, Search, Loader2, X, ChevronDown
} from "lucide-react";

const MEMORY_TYPES: { value: MemoryType; label: string; color: string }[] = [
  { value: "WORKING", label: "Working", color: "bg-blue-100 text-blue-700" },
  { value: "SHORT_TERM", label: "Short-term", color: "bg-purple-100 text-purple-700" },
  { value: "EPISODIC", label: "Episodic", color: "bg-amber-100 text-amber-700" },
  { value: "SEMANTIC", label: "Semantic", color: "bg-emerald-100 text-emerald-700" },
  { value: "PROCEDURAL", label: "Procedural", color: "bg-cyan-100 text-cyan-700" },
  { value: "PROJECT", label: "Project", color: "bg-orange-100 text-orange-700" },
  { value: "USER_PREFERENCE", label: "Preference", color: "bg-pink-100 text-pink-700" },
  { value: "TASK", label: "Task", color: "bg-indigo-100 text-indigo-700" },
  { value: "FAILURE", label: "Failure", color: "bg-red-100 text-red-700" },
];

export default function MemoryPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<MemoryType | "">("");
  const [showCreate, setShowCreate] = useState(false);
  const [newType, setNewType] = useState<MemoryType>("WORKING");
  const [newContent, setNewContent] = useState("");
  const [newSource, setNewSource] = useState("");
  const [newImportance, setNewImportance] = useState(5);
  const [creating, setCreating] = useState(false);
  const [page, setPage] = useState(1);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await memoryApi.list({
        page, page_size: 20, search: search || undefined,
        type: (typeFilter as MemoryType) || undefined,
      });
      setMemories(res.memories);
      setTotal(res.total);
    } catch { toast.add({ title: "Failed to load memories", type: "error" }); }
    finally { setLoading(false); }
  }, [search, typeFilter, page]);

  useEffect(() => { load(); }, [load]);

  const handleToggle = async (m: Memory) => {
    try {
      await memoryApi.toggle(m.id);
      toast.add({ title: m.enabled ? "Disabled" : "Enabled", type: "success" });
      load();
    } catch { toast.add({ title: "Toggle failed", type: "error" }); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this memory?")) return;
    try {
      await memoryApi.delete(id);
      toast.add({ title: "Deleted", type: "success" });
      load();
    } catch { toast.add({ title: "Delete failed", type: "error" }); }
  };

  const handleCreate = async () => {
    if (!newContent.trim()) return;
    setCreating(true);
    try {
      await memoryApi.create({
        type: newType, content: newContent, source: newSource || undefined,
        importance: newImportance,
      });
      toast.add({ title: "Memory created", type: "success" });
      setShowCreate(false); setNewContent(""); setNewSource(""); setNewImportance(5);
      load();
    } catch { toast.add({ title: "Create failed", type: "error" }); }
    finally { setCreating(false); }
  };

  const getTypeInfo = (t: string) => MEMORY_TYPES.find(m => m.value === t) || { label: t, color: "bg-zinc-100 text-zinc-700" };
  const totalPages = Math.ceil(total / 20);

  return (
    <ProtectedLayout>
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex">
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <div className={`flex-1 flex flex-col min-w-0 transition-all ${sidebarOpen ? "ml-64" : "ml-16"}`}>
          <Header />
          <main className="flex-1 p-6 overflow-auto max-w-6xl mx-auto w-full">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-2xl font-semibold flex items-center gap-2"><Brain className="h-6 w-6" /> Memory</h1>
                <p className="text-sm text-zinc-500 mt-1">{total} memories across all types.</p>
              </div>
              <Button onClick={() => setShowCreate(!showCreate)} className="gap-2">
                <Plus className="h-4 w-4" /> New Memory
              </Button>
            </div>

            {showCreate && (
              <Card className="mb-6">
                <CardContent className="p-4 space-y-3">
                  <div className="flex gap-3">
                    <select value={newType} onChange={e => setNewType(e.target.value as MemoryType)}
                      className="px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800">
                      {MEMORY_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                    </select>
                    <Input placeholder="Source (optional)" value={newSource} onChange={e => setNewSource(e.target.value)} className="flex-1" />
                    <div className="flex items-center gap-2">
                      <label className="text-sm text-zinc-500">Importance:</label>
                      <input type="range" min="1" max="10" value={newImportance} onChange={e => setNewImportance(Number(e.target.value))} className="w-24" />
                      <span className="text-sm font-medium w-6 text-center">{newImportance}</span>
                    </div>
                  </div>
                  <textarea placeholder="Memory content..." value={newContent} onChange={e => setNewContent(e.target.value)}
                    className="w-full min-h-[80px] px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800" />
                  <div className="flex gap-2">
                    <Button onClick={handleCreate} disabled={creating || !newContent.trim()}>
                      {creating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Plus className="h-4 w-4 mr-2" />} Create
                    </Button>
                    <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="flex gap-3 mb-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
                <Input placeholder="Search memories..." value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} className="pl-9" />
              </div>
              <select value={typeFilter} onChange={e => { setTypeFilter(e.target.value as MemoryType | ""); setPage(1); }}
                className="px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800">
                <option value="">All Types</option>
                {MEMORY_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>

            {loading ? (
              <div className="flex justify-center p-12"><Loader2 className="h-6 w-6 animate-spin" /></div>
            ) : memories.length === 0 ? (
              <Card className="p-12 text-center text-zinc-500">
                <Brain className="h-12 w-12 mx-auto mb-3 text-zinc-300" />
                <p className="text-lg font-medium">No memories found</p>
                <p className="text-sm mt-1">Create memories to help the agent learn and remember.</p>
              </Card>
            ) : (
              <div className="space-y-2">
                {memories.map(m => {
                  const ti = getTypeInfo(m.type);
                  return (
                    <Card key={m.id} className={`hover:shadow-sm transition-shadow ${!m.enabled ? "opacity-50" : ""}`}>
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <Badge className={`text-xs ${ti.color}`}>{ti.label}</Badge>
                              {m.confidence != null && (
                                <span className="text-xs text-zinc-400">Confidence: {Math.round(m.confidence * 100)}%</span>
                              )}
                              {m.importance != null && (
                                <span className="text-xs text-zinc-400">Importance: {m.importance}/10</span>
                              )}
                              {m.project_name && <span className="text-xs text-zinc-400">Project: {m.project_name}</span>}
                            </div>
                            <p className="text-sm text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap">{m.content}</p>
                            {m.source && <p className="text-xs text-zinc-400 mt-1">Source: {m.source}</p>}
                          </div>
                          <div className="flex items-center gap-1">
                            <Button variant="ghost" size="sm" onClick={() => handleToggle(m)} title={m.enabled ? "Disable" : "Enable"}>
                              {m.enabled ? <ToggleRight className="h-4 w-4 text-green-600" /> : <ToggleLeft className="h-4 w-4 text-zinc-400" />}
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleDelete(m.id)} title="Delete">
                              <Trash2 className="h-4 w-4 text-red-500" />
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}

            {totalPages > 1 && (
              <div className="flex justify-center gap-2 mt-6">
                <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous</Button>
                <span className="text-sm text-zinc-500 py-1">Page {page} of {totalPages}</span>
                <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next</Button>
              </div>
            )}
          </main>
        </div>
      </div>
    </ProtectedLayout>
  );
}


