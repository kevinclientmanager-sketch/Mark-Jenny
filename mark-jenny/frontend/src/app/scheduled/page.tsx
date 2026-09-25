"use client";
import { useState, useEffect, useCallback } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ProtectedLayout } from "@/components/layout/protected-layout";
import { schedulesApi, Schedule, ScheduleRun } from "@/lib/api/schedules";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/components/ui/toast";
import {
  Calendar, Clock, Play, Pause, RotateCcw, Trash2, Plus, Loader2,
  ChevronDown, ChevronUp, Search, Filter, MoreVertical, Copy, History
} from "lucide-react";
import {
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem,
} from "@/components/ui/dropdown-menu";

export default function ScheduledPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filterActive, setFilterActive] = useState<boolean | undefined>(undefined);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [runs, setRuns] = useState<ScheduleRun[]>([]);
  const [runsLoading, setRunsLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newPrompt, setNewPrompt] = useState("");
  const [newFreq, setNewFreq] = useState<"DAILY" | "WEEKLY" | "MONTHLY">("DAILY");
  const [newTime, setNewTime] = useState("09:00");
  const [showCreate, setShowCreate] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await schedulesApi.list({ search: search || undefined, is_active: filterActive, page_size: 100 });
      setSchedules(res.schedules);
    } catch { toast.add({ title: "Failed to load schedules", type: "error" }); }
    finally { setLoading(false); }
  }, [search, filterActive]);

  useEffect(() => { load(); }, [load]);

  const loadRuns = async (scheduleId: number) => {
    setRunsLoading(true);
    try {
      const r = await schedulesApi.listRuns(scheduleId);
      setRuns(r);
    } catch { toast.add({ title: "Failed to load run history", type: "error" }); }
    finally { setRunsLoading(false); }
  };

  const toggleExpand = (id: number) => {
    if (expandedId === id) { setExpandedId(null); setRuns([]); }
    else { setExpandedId(id); loadRuns(id); }
  };

  const handleToggle = async (s: Schedule) => {
    try {
      if (s.is_active) await schedulesApi.pause(s.id);
      else await schedulesApi.resume(s.id);
      toast.add({ title: s.is_active ? "Paused" : "Resumed", type: "success" });
      load();
    } catch { toast.add({ title: "Action failed", type: "error" }); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this schedule?")) return;
    try {
      await schedulesApi.delete(id);
      toast.add({ title: "Deleted", type: "success" });
      load();
    } catch { toast.add({ title: "Delete failed", type: "error" }); }
  };

  const handleDuplicate = async (id: number) => {
    try {
      await schedulesApi.duplicate(id);
      toast.add({ title: "Duplicated", type: "success" });
      load();
    } catch { toast.add({ title: "Duplicate failed", type: "error" }); }
  };

  const handleCreate = async () => {
    if (!newTitle.trim() || !newPrompt.trim()) return;
    setCreating(true);
    try {
      await schedulesApi.create({
        title: newTitle, prompt: newPrompt, frequency: newFreq,
        time_of_day: newTime, run_option: "SEPARATE_TASK",
      });
      toast.add({ title: "Schedule created", type: "success" });
      setShowCreate(false); setNewTitle(""); setNewPrompt("");
      load();
    } catch { toast.add({ title: "Create failed", type: "error" }); }
    finally { setCreating(false); }
  };

  const freqBadge = (f: string) => {
    const colors: Record<string, string> = {
      DAILY: "bg-blue-100 text-blue-700", WEEKLY: "bg-purple-100 text-purple-700",
      MONTHLY: "bg-amber-100 text-amber-700", ONCE: "bg-zinc-100 text-zinc-700", CRON: "bg-emerald-100 text-emerald-700",
    };
    return <Badge className={`text-xs ${colors[f] || ""}`}>{f}</Badge>;
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
                <h1 className="text-2xl font-semibold flex items-center gap-2"><Calendar className="h-6 w-6" /> Scheduled Tasks</h1>
                <p className="text-sm text-zinc-500 mt-1">Manage recurring and one-time scheduled agent tasks.</p>
              </div>
              <Button onClick={() => setShowCreate(!showCreate)} className="gap-2">
                <Plus className="h-4 w-4" /> New Schedule
              </Button>
            </div>

            {showCreate && (
              <Card className="mb-6">
                <CardHeader><CardTitle className="text-base">Create Schedule</CardTitle></CardHeader>
                <CardContent className="space-y-3">
                  <Input placeholder="Schedule title" value={newTitle} onChange={e => setNewTitle(e.target.value)} />
                  <textarea placeholder="What should the agent do?" value={newPrompt} onChange={e => setNewPrompt(e.target.value)}
                    className="w-full min-h-[80px] px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800" />
                  <div className="flex gap-3">
                    <select value={newFreq} onChange={e => setNewFreq(e.target.value as any)}
                      className="px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800">
                      <option value="DAILY">Daily</option><option value="WEEKLY">Weekly</option><option value="MONTHLY">Monthly</option>
                    </select>
                    <Input type="time" value={newTime} onChange={e => setNewTime(e.target.value)} className="w-40" />
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={handleCreate} disabled={creating || !newTitle.trim() || !newPrompt.trim()}>
                      {creating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Plus className="h-4 w-4 mr-2" />}
                      Create
                    </Button>
                    <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="flex gap-3 mb-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
                <Input placeholder="Search schedules..." value={search} onChange={e => setSearch(e.target.value)} className="pl-9" />
              </div>
              <select value={filterActive === undefined ? "" : String(filterActive)}
                onChange={e => setFilterActive(e.target.value === "" ? undefined : e.target.value === "true")}
                className="px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800">
                <option value="">All</option><option value="true">Active</option><option value="false">Paused</option>
              </select>
            </div>

            {loading ? (
              <div className="flex justify-center p-12"><Loader2 className="h-6 w-6 animate-spin" /></div>
            ) : schedules.length === 0 ? (
              <Card className="p-12 text-center text-zinc-500">
                <Calendar className="h-12 w-12 mx-auto mb-3 text-zinc-300" />
                <p className="text-lg font-medium">No schedules yet</p>
                <p className="text-sm mt-1">Create a schedule to automate recurring agent tasks.</p>
              </Card>
            ) : (
              <div className="space-y-3">
                {schedules.map(s => (
                  <Card key={s.id} className="hover:shadow-sm transition-shadow">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium truncate">{s.title}</span>
                            {freqBadge(s.frequency)}
                            <Badge variant={s.is_active ? "default" : "secondary"} className="text-xs">
                              {s.is_active ? "Active" : "Paused"}
                            </Badge>
                          </div>
                          <p className="text-sm text-zinc-500 truncate">{s.prompt}</p>
                          <div className="flex items-center gap-4 mt-2 text-xs text-zinc-400">
                            <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {s.time_of_day}</span>
                            <span>Runs: {s.run_count}</span>
                            {s.next_run_at && <span>Next: {new Date(s.next_run_at).toLocaleString()}</span>}
                            {s.project_name && <span>Project: {s.project_name}</span>}
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          <Button variant="ghost" size="sm" onClick={() => handleToggle(s)}
                            title={s.is_active ? "Pause" : "Resume"}>
                            {s.is_active ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => toggleExpand(s.id)} title="Run history">
                            <History className="h-4 w-4" />
                          </Button>
                          <DropdownMenu>
                            <DropdownMenuTrigger render={<Button variant="ghost" size="sm"><MoreVertical className="h-4 w-4" /></Button>}>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent>
                              <DropdownMenuItem onSelect={() => handleDuplicate(s.id)}>
                                <Copy className="h-4 w-4 mr-2" /> Duplicate
                              </DropdownMenuItem>
                              <DropdownMenuItem onSelect={() => handleDelete(s.id)} className="text-red-600">
                                <Trash2 className="h-4 w-4 mr-2" /> Delete
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      </div>
                      {expandedId === s.id && (
                        <div className="mt-3 pt-3 border-t">
                          <h4 className="text-sm font-medium mb-2">Run History</h4>
                          {runsLoading ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : runs.length === 0 ? (
                            <p className="text-xs text-zinc-500">No runs yet.</p>
                          ) : (
                            <div className="space-y-1">
                              {runs.map(r => (
                                <div key={r.id} className="flex items-center gap-3 text-xs">
                                  <Badge variant={r.status === "SUCCESS" ? "default" : r.status === "FAILED" ? "destructive" : "secondary"} className="text-xs">
                                    {r.status}
                                  </Badge>
                                  <span className="text-zinc-500">{new Date(r.started_at).toLocaleString()}</span>
                                  {r.duration_seconds != null && <span className="text-zinc-400">{r.duration_seconds}s</span>}
                                  {r.error && <span className="text-red-500 truncate flex-1">{r.error}</span>}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
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


