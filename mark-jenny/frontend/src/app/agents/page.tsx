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

interface Agent {
  id: number;
  name: string;
  agent_type: string;
  status: string;
  model_used: string | null;
  description?: string | null;
  available_tools?: string[];
  role?: string;
  parent?: string | null;
  created_at: string;
}

const agentIcons: Record<string, typeof Bot> = {
  planner: Brain, executor: Cpu, reviewer: Wrench, supervisor: Bot,
};

const LEAD_STYLE: Record<string, { icon: typeof Bot; ring: string; tint: string }> = {
  Imti: { icon: Brain, ring: "ring-violet-500/30", tint: "bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300" },
  Mark: { icon: Wrench, ring: "ring-blue-500/30", tint: "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300" },
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

  // Roster leads are the agents with no parent: Imti and Mark.
  const leads = agents.filter((a) => !a.parent);

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
              <p className="text-sm text-zinc-500">The Agent Brain plans and runs your goals, then shows its reasoning, the tools it used, and what it learned.</p>
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
            ) : leads.length === 0 ? (
              <div className="rounded-lg border border-dashed p-8 text-center">
                <Bot className="mx-auto h-6 w-6 text-zinc-400" />
                <p className="mt-2 text-sm font-medium">No agents registered yet</p>
                <p className="mx-auto mt-1 max-w-md text-xs text-zinc-500">
                  The Imti and Mark crews appear here once they are registered. Until then the
                  Agent Brain above is what actually runs your goals &mdash; give it a goal and
                  press Think or Run.
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {leads.map((lead) => {
                  const style = LEAD_STYLE[lead.name] || LEAD_STYLE.Imti;
                  const LeadIcon = style.icon;
                  const children = agents.filter((a) => a.parent === lead.name);
                  return (
                    <div key={lead.id}>
                      <div className="mb-2 flex items-center gap-2">
                        <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${style.tint}`}>
                          <LeadIcon className="h-4 w-4" />
                        </div>
                        <div>
                          <h2 className="text-sm font-semibold">{lead.name}</h2>
                          <p className="text-[11px] text-zinc-500">
                            {lead.role === "coding" ? "Coding & building" : "Agent"}
                          </p>
                        </div>
                        <Badge variant="outline" className="ml-auto text-[10px]">
                          {children.length} sub-agent{children.length === 1 ? "" : "s"}
                        </Badge>
                      </div>
                      {lead.description && (
                        <p className="mb-3 text-xs text-zinc-500">{lead.description}</p>
                      )}
                      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                        {children.map((a) => {
                          const Icon = agentIcons[a.role || ""] || Bot;
                          return (
                            <Card key={a.id} className={`ring-1 ${style.ring}`}>
                              <CardContent className="p-4">
                                <div className="flex items-center gap-3">
                                  <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${style.tint}`}>
                                    <Icon className="h-4 w-4" />
                                  </div>
                                  <div className="min-w-0">
                                    <p className="truncate text-sm font-medium">{a.name}</p>
                                    <p className="truncate text-[11px] text-zinc-500 capitalize">{a.role || a.agent_type}</p>
                                  </div>
                                </div>
                                {a.description && (
                                  <p className="mt-2 text-[11px] leading-relaxed text-zinc-500">{a.description}</p>
                                )}
                                {a.available_tools && a.available_tools.length > 0 && (
                                  <div className="mt-2 flex flex-wrap gap-1">
                                    {a.available_tools.map((t) => (
                                      <Badge key={t} variant="secondary" className="text-[9px]">{t}</Badge>
                                    ))}
                                  </div>
                                )}
                              </CardContent>
                            </Card>
                          );
                        })}
                      </div>
                    </div>
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


