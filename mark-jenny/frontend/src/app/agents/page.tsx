"use client";
import { useState, useEffect } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ProtectedLayout } from "@/components/layout/protected-layout";
import { api } from "@/lib/api";
import { agentBrainApi, type BrainThink, type BrainRun, type BrainInsights } from "@/lib/api/agentBrain";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Bot, Loader2, Brain, Cpu, Wrench, Play, Eye, Lightbulb, CheckCircle2, XCircle } from "lucide-react";

interface Agent { id: number; name: string; agent_type: string; status: string; model_used: string | null; created_at: string; }

const agentIcons: Record<string, typeof Bot> = {
  planner: Brain, executor: Cpu, reviewer: Wrench, supervisor: Bot,
};

export default function AgentsPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);

  const [goal, setGoal] = useState("");
  const [busy, setBusy] = useState<"think" | "run" | null>(null);
  const [think, setThink] = useState<BrainThink | null>(null);
  const [run, setRun] = useState<BrainRun | null>(null);
  const [insights, setInsights] = useState<BrainInsights | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get<{ agents: Agent[] }>("/agents?page_size=50");
        setAgents(res.agents || []);
      } catch {} finally { setLoading(false); }
    })();
    agentBrainApi.insights().then(setInsights).catch(() => {});
  }, []);

  const doThink = async () => {
    if (!goal.trim() || busy) return;
    setBusy("think"); setError(""); setRun(null);
    try {
      setThink(await agentBrainApi.think(goal.trim()));
    } catch (e: any) { setError(e?.message || "Think failed"); } finally { setBusy(null); }
  };

  const doRun = async () => {
    if (!goal.trim() || busy) return;
    setBusy("run"); setError(""); setThink(null);
    try {
      const r = await agentBrainApi.run(goal.trim());
      setRun(r);
      agentBrainApi.insights().then(setInsights).catch(() => {});
    } catch (e: any) { setError(e?.message || "Run failed"); } finally { setBusy(null); }
  };

  return (
    <ProtectedLayout>
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex">
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <div className={`flex-1 flex flex-col min-w-0 transition-all ${sidebarOpen ? "ml-64" : "ml-16"}`}>
          <Header />
          <main className="flex-1 p-6 overflow-auto">
            <div className="mb-6">
              <h1 className="text-2xl font-semibold flex items-center gap-2"><Bot className="h-6 w-6" /> AI Agents</h1>
              <p className="text-sm text-zinc-500">Multi-agent system with 9 specialist agents, plus the Agent Brain for autonomous goals</p>
            </div>

            <Card className="mb-6">
              <CardHeader><CardTitle className="text-base flex items-center gap-2"><Brain className="h-4 w-4" /> Agent Brain — give Mark a goal</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <div className="flex gap-2">
                  <Input
                    value={goal}
                    onChange={(e) => setGoal(e.target.value)}
                    placeholder="e.g. Research EV pricing and build a comparison spreadsheet with a recommendation"
                    onKeyDown={(e) => { if (e.key === "Enter") doThink(); }}
                  />
                  <Button variant="outline" onClick={doThink} disabled={busy !== null || !goal.trim()}>
                    {busy === "think" ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <Eye className="mr-1.5 h-4 w-4" />}
                    Think
                  </Button>
                  <Button onClick={doRun} disabled={busy !== null || !goal.trim()}>
                    {busy === "run" ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <Play className="mr-1.5 h-4 w-4" />}
                    Run
                  </Button>
                </div>
                <p className="text-xs text-zinc-500">Think shows the reasoning trace without acting. Run executes a bounded plan → act → observe → reflect loop with real tools and saves what it learns.</p>
                {error && <p className="text-sm text-red-500">{error}</p>}

                {think && (
                  <div className="space-y-3 border-t pt-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="default">{think.intent.intent}</Badge>
                      <Badge variant="outline">confidence {think.intent.confidence}</Badge>
                      <Badge variant="outline">{think.intent.complexity}</Badge>
                      <Badge variant="secondary">{think.plan.strategy}</Badge>
                      {think.model && <Badge variant="outline">{think.model.name}</Badge>}
                    </div>
                    <div className="space-y-1">
                      {think.trace.map((t, i) => (
                        <p key={i} className="text-xs text-zinc-600 dark:text-zinc-400">• {t}</p>
                      ))}
                    </div>
                    <div className="space-y-2">
                      {think.plan.subtasks.map((s) => (
                        <div key={s.order} className="p-3 border rounded-lg">
                          <p className="text-sm font-medium">{s.order}. {s.title}</p>
                          <p className="text-xs text-zinc-500 mt-0.5">Accepts when: {s.acceptance}</p>
                          <div className="flex flex-wrap gap-1 mt-1.5">
                            {s.tools.map((t) => <Badge key={t} variant="secondary" className="text-[10px]">{t}</Badge>)}
                            {s.skills.map((t) => <Badge key={t} variant="outline" className="text-[10px]">{t}</Badge>)}
                          </div>
                        </div>
                      ))}
                    </div>
                    {think.recalled.length > 0 && (
                      <div>
                        <p className="text-sm font-medium mb-1.5">Recalled from memory ({think.recalled.length})</p>
                        <div className="space-y-1.5">
                          {think.recalled.map((r, i) => (
                            <div key={`${r.kind}-${r.id}-${i}`} className="text-xs p-2 border rounded-lg flex items-center justify-between gap-2">
                              <span className="truncate text-zinc-600 dark:text-zinc-400">{r.content}</span>
                              <Badge variant="outline" className="text-[10px] shrink-0">{r.type} · {r.score}</Badge>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {think.skills.gaps.length > 0 && (
                      <p className="text-xs text-amber-600">Skill gaps: {think.skills.gaps.join(", ")} — install from Skills to unlock.</p>
                    )}
                  </div>
                )}

                {run && (
                  <div className="space-y-3 border-t pt-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline">{run.plan_strategy}</Badge>
                      <Badge variant={run.steps.every((s) => s.passed) ? "default" : "secondary"}>{run.self_check}</Badge>
                      {run.artifacts.length > 0 && <Badge variant="outline">{run.artifacts.length} artifact(s)</Badge>}
                    </div>
                    <div className="space-y-2">
                      {run.steps.map((s) => (
                        <div key={s.order} className="p-3 border rounded-lg">
                          <p className="text-sm font-medium flex items-center gap-2">
                            {s.passed
                              ? <CheckCircle2 className="h-4 w-4 text-green-600 shrink-0" />
                              : <XCircle className="h-4 w-4 text-red-500 shrink-0" />}
                            {s.order}. {s.title}
                          </p>
                          <p className="text-xs text-zinc-500 mt-1">{s.action} — {s.observation}</p>
                          {s.files.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-1.5">
                              {s.files.map((f, i) => <Badge key={`${f.name}-${i}`} variant="secondary" className="text-[10px]">{f.name}</Badge>)}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                    <p className="text-sm text-zinc-600 dark:text-zinc-400">{run.summary}</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {insights && (
              <Card className="mb-6">
                <CardHeader><CardTitle className="text-base flex items-center gap-2"><Lightbulb className="h-4 w-4" /> Proactive briefing</CardTitle></CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    {(Object.entries(insights.memory_health) as [string, number][]).map(([k, v]) => (
                      <div key={k} className="p-3 border rounded-lg">
                        <p className="text-xs text-zinc-500 capitalize">{k}</p>
                        <p className="text-xl font-semibold">{v}</p>
                      </div>
                    ))}
                  </div>
                  <div className="space-y-1.5">
                    {insights.suggestions.map((s, i) => (
                      <p key={i} className="text-sm text-zinc-600 dark:text-zinc-400">• {s}</p>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {loading ? (
              <div className="flex justify-center p-8"><Loader2 className="h-6 w-6 animate-spin" /></div>
            ) : agents.length === 0 ? (
              <div className="grid gap-4 md:grid-cols-3">
                {["Planner", "Executor", "Reviewer", "Researcher", "Coder", "Writer", "Analyst", "Supervisor", "Memory Manager"].map((name) => (
                  <Card key={name}>
                    <CardContent className="p-4 flex items-center gap-3">
                      <div className="h-10 w-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                        <Bot className="h-5 w-5 text-blue-600" />
                      </div>
                      <div>
                        <p className="font-medium">{name}</p>
                        <Badge variant="outline">Ready</Badge>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {agents.map(a => {
                  const Icon = agentIcons[a.agent_type] || Bot;
                  return (
                    <Card key={a.id}>
                      <CardContent className="p-4 flex items-center gap-3">
                        <div className="h-10 w-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                          <Icon className="h-5 w-5 text-blue-600" />
                        </div>
                        <div>
                          <p className="font-medium">{a.name}</p>
                          <div className="flex gap-2 text-xs text-zinc-500">
                            <Badge variant="outline">{a.agent_type}</Badge>
                            <Badge variant={a.status === "active" ? "default" : "secondary"}>{a.status}</Badge>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </main>
        </div>
      </div>
    </ProtectedLayout>
  );
}


