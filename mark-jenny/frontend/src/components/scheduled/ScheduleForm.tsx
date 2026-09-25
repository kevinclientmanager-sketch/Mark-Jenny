"use client";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { schedulesApi, Schedule, CreateScheduleData, UpdateScheduleData, ScheduleFrequency, ScheduleRunOption } from "@/lib/api/schedules";
import { projectsApi } from "@/lib/api/projects";
import { projectWorkspaceApi, Connector } from "@/lib/api/projectWorkspace";
import { Loader2, Shield } from "lucide-react";

interface ScheduleFormProps {
  schedule?: Schedule | null;
  onSuccess: (s: Schedule) => void;
  onCancel: () => void;
}

export function ScheduleForm({ schedule, onSuccess, onCancel }: ScheduleFormProps) {
  const isEdit = !!schedule;
  const [title, setTitle] = useState(schedule?.title || "");
  const [frequency, setFrequency] = useState<ScheduleFrequency>(schedule?.frequency || "DAILY");
  const [timeOfDay, setTimeOfDay] = useState(schedule?.time_of_day || "09:00");
  const [neverEnds, setNeverEnds] = useState(!schedule?.end_date);
  const [endDate, setEndDate] = useState(schedule?.end_date ? schedule.end_date.slice(0,10) : "");
  const [prompt, setPrompt] = useState(schedule?.prompt || "");
  const [skipConfirmations, setSkipConfirmations] = useState(schedule?.skip_confirmations || false);
  const [runOption, setRunOption] = useState<ScheduleRunOption>(schedule?.run_option || "SAME_TASK");
  const [projectId, setProjectId] = useState<number | undefined>(schedule?.project_id || undefined);
  const [agentId, setAgentId] = useState<number | undefined>(schedule?.agent_id || undefined);
  const [computer, setComputer] = useState(schedule?.computer || "");
  const [selectedConnectors, setSelectedConnectors] = useState<number[]>(schedule?.connectors || []);
  const [projects, setProjects] = useState<any[]>([]);
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(()=>{
    (async()=>{
      try {
        const [p, c] = await Promise.all([
          projectsApi.list({ page_size: 100 }),
          projectWorkspaceApi.listConnectors().catch(()=>[] as Connector[]),
        ]);
        setProjects(p.projects);
        setConnectors(c as Connector[]);
        // Agents: try to fetch if endpoint exists, else static fallback
        try {
          const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/agents`, { headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }});
          if (res.ok) {
            const data = await res.json();
            setAgents(Array.isArray(data) ? data : data.agents || []);
          } else throw new Error("no agents");
        } catch {
          setAgents([
            { id: 1, name: "System Agent" },
            { id: 2, name: "Research Agent" },
            { id: 3, name: "Coding Agent" },
            { id: 4, name: "Browser Agent" },
          ]);
        }
      } catch(e){ console.error(e); }
    })();
  },[]);

  const handleSubmit = async (e: React.FormEvent)=>{
    e.preventDefault();
    setError(null);
    if (!title.trim()) return setError("Title required");
    if (!prompt.trim()) return setError("Prompt required");
    if (!timeOfDay) return setError("Time required");
    setSaving(true);
    try {
      const data: CreateScheduleData = {
        title: title.trim(),
        prompt: prompt.trim(),
        frequency: frequency as ScheduleFrequency,
        time_of_day: timeOfDay,
        timezone: "UTC",
        run_option: runOption,
        skip_confirmations: skipConfirmations,
        project_id: projectId,
        agent_id: agentId,
        connectors: selectedConnectors,
        computer: computer || undefined,
        end_date: neverEnds ? undefined : (endDate ? new Date(endDate).toISOString() : undefined),
      };
      let res: Schedule;
      if (isEdit && schedule) {
        res = await schedulesApi.update(schedule.id, data as UpdateScheduleData);
      } else {
        res = await schedulesApi.create(data);
      }
      onSuccess(res);
    } catch(err:any){
      setError(err.message || "Failed to save");
    } finally { setSaving(false); }
  };

  const toggleConnector = (id:number)=>{
    setSelectedConnectors(prev=> prev.includes(id) ? prev.filter(x=>x!==id) : [...prev, id]);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <div className="p-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded">{error}</div>}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="md:col-span-2">
          <label className="text-sm font-medium">Title *</label>
          <Input value={title} onChange={e=>setTitle(e.target.value)} placeholder="e.g., Daily backup, Weekly research" required />
        </div>
        <div>
          <label className="text-sm font-medium">Repeat *</label>
          <select value={frequency} onChange={e=>setFrequency(e.target.value as ScheduleFrequency)} className="w-full mt-1 px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800">
            <option value="DAILY">Daily</option>
            <option value="WEEKLY">Weekly</option>
            <option value="MONTHLY">Monthly</option>
            <option value="ONCE">No repeat</option>
          </select>
        </div>
        <div>
          <label className="text-sm font-medium">Time *</label>
          <Input type="time" value={timeOfDay} onChange={e=>setTimeOfDay(e.target.value)} required />
        </div>
        <div className="flex items-center gap-2 mt-6">
          <input type="checkbox" id="neverEnds" checked={neverEnds} onChange={e=>setNeverEnds(e.target.checked)} className="h-4 w-4" />
          <label htmlFor="neverEnds" className="text-sm">Never Ends</label>
        </div>
        <div>
          <label className="text-sm font-medium">End Date {neverEnds && <span className="text-zinc-400">(disabled)</span>}</label>
          <Input type="date" value={endDate} onChange={e=>setEndDate(e.target.value)} disabled={neverEnds} />
        </div>
      </div>

      <div>
        <label className="text-sm font-medium">Prompt *</label>
        <textarea value={prompt} onChange={e=>setPrompt(e.target.value)} placeholder="Describe the task to run on schedule..." className="w-full mt-1 min-h-[90px] px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800" required />
        <p className="text-xs text-zinc-500 mt-1">This will be used as the agent's instruction when the schedule triggers.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-medium">Run Options</label>
          <div className="flex gap-4 mt-1">
            <label className="flex items-center gap-2 text-sm"><input type="radio" name="runOption" checked={runOption==="SAME_TASK"} onChange={()=>setRunOption("SAME_TASK")} /> Same task</label>
            <label className="flex items-center gap-2 text-sm"><input type="radio" name="runOption" checked={runOption==="SEPARATE_TASK"} onChange={()=>setRunOption("SEPARATE_TASK")} /> Separate task</label>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <input type="checkbox" id="skipConfirm" checked={skipConfirmations} onChange={e=>setSkipConfirmations(e.target.checked)} className="h-4 w-4" />
          <label htmlFor="skipConfirm" className="text-sm">Skip Confirmations {skipConfirmations && <Badge variant="destructive" className="ml-1">Risk</Badge>}</label>
        </div>
      </div>
      {!skipConfirmations && <p className="text-xs text-green-700 flex items-center gap-1"><Shield className="h-3 w-3"/> SAFE: Approvals required for sensitive actions (default).</p>}
      {skipConfirmations && <p className="text-xs text-amber-700">⚠️ With skip, MARK will run autonomously without asking.</p>}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-medium">Project</label>
          <select value={projectId || ""} onChange={e=>setProjectId(e.target.value?Number(e.target.value):undefined)} className="w-full mt-1 px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800">
            <option value="">General (no project)</option>
            {projects.map(p=> <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        <div>
          <label className="text-sm font-medium">Agent</label>
          <select value={agentId || ""} onChange={e=>setAgentId(e.target.value?Number(e.target.value):undefined)} className="w-full mt-1 px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800">
            <option value="">Auto (Model Router)</option>
            {agents.map((a:any)=> <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
        </div>
        <div>
          <label className="text-sm font-medium">Computer</label>
          <select value={computer} onChange={e=>setComputer(e.target.value)} className="w-full mt-1 px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800">
            <option value="">Cloud (default)</option>
            <option value="local">This Computer (paired)</option>
            <option value="cloud-browser">Cloud Browser</option>
          </select>
          <p className="text-xs text-zinc-500 mt-1">Requires <em>Connect My Computer</em> pairing for local.</p>
        </div>
        <div>
          <label className="text-sm font-medium">Connectors</label>
          <div className="mt-1 max-h-28 overflow-auto border rounded-lg p-2 space-y-1 bg-white dark:bg-zinc-800">
            {connectors.length===0 ? <p className="text-xs text-zinc-500">No connectors - add via Project Workspace → Connectors</p> :
              connectors.map(c=> (
                <label key={c.id} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={selectedConnectors.includes(c.id)} onChange={()=>toggleConnector(c.id)} className="h-3 w-3" />
                  {c.display_name || c.name} <span className="text-xs text-zinc-500">({c.type})</span>
                </label>
              ))
            }
          </div>
        </div>
      </div>

      <div className="flex gap-2 justify-end pt-2">
        <Button type="button" variant="outline" onClick={onCancel} disabled={saving}>Cancel</Button>
        <Button type="submit" disabled={saving} className="bg-blue-600 hover:bg-blue-700">
          {saving ? <><Loader2 className="mr-2 h-4 w-4 animate-spin"/>{isEdit?"Updating...":"Creating..."}</> : isEdit?"Update Schedule":"Create Schedule"}
        </Button>
      </div>
    </form>
  );
}

