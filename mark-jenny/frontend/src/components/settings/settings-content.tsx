"use client";
import { useState, useEffect, useRef } from "react";
import { useAuth } from "@/lib/auth/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useTheme } from "next-themes";
import { api } from "@/lib/api";
import { settingsApi } from "@/lib/api/settings";
import { schedulesApi } from "@/lib/api/schedules";
import { cn } from "@/lib/utils";
import { toast } from "@/components/ui/toast";
import { CoreLawsPanel } from "./core-laws-panel";
import {
  Sun, User, Loader2, CheckCircle2, Shield, ShieldCheck, Database, Info,
  Calendar, Code, Globe, Monitor, Lock, BookOpen, Network, Users, Bot,
  Play, Plug, Cpu, ExternalLink, Brain, Search, FileText, ImageIcon,
  Video, Music, Wifi, WifiOff, Plus, Pencil, Trash2, Copy, Power,
  Pause, Link2, X, Save, ShieldAlert
} from "lucide-react";

function Toggle({ checked, onChange, disabled }: { checked: boolean; onChange: (v: boolean) => void; disabled?: boolean }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative h-6 w-11 shrink-0 rounded-full transition-colors",
        checked ? "bg-blue-600" : "bg-zinc-300 dark:bg-zinc-700",
        disabled && "opacity-50 cursor-not-allowed"
      )}
    >
      <span className={cn("absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform", checked && "translate-x-5")} />
    </button>
  );
}

function SettingRow({ title, desc, control }: { title: string; desc?: string; control: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 p-3 border rounded-lg">
      <div className="min-w-0">
        <p className="text-sm font-medium">{title}</p>
        {desc && <p className="text-xs text-zinc-500 mt-0.5">{desc}</p>}
      </div>
      <div className="shrink-0">{control}</div>
    </div>
  );
}

function Stat({ icon, label, value }: { icon?: React.ReactNode; label: string; value: number | string }) {
  return (
    <div className="p-3 border rounded-lg flex items-center gap-3">
      {icon && <span className="text-zinc-400 shrink-0">{icon}</span>}
      <div className="min-w-0">
        <p className="text-xs text-zinc-500 truncate">{label}</p>
        <p className="text-xl font-semibold mt-0.5">{value}</p>
      </div>
    </div>
  );
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-sm font-medium block">{label}</label>
      {hint && <p className="text-xs text-zinc-500 mb-1">{hint}</p>}
      <div className="mt-1.5">{children}</div>
    </div>
  );
}

export function SettingsContent() {
  const { user } = useAuth();
  const { theme, setTheme } = useTheme();
  const [language, setLanguage] = useState("en");
  const [fullName, setFullName] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [tab, setTab] = useState("profile");
  const [search, setSearch] = useState("");

  const [schedules, setSchedules] = useState<any[]>([]);
  const [execCode, setExecCode] = useState("print('Hello from MARK')");
  const [execLang, setExecLang] = useState("python");
  const [execResult, setExecResult] = useState<any>(null);
  const [executing, setExecuting] = useState(false);
  const [users, setUsers] = useState<any[]>([]);
  const [prefs, setPrefs] = useState<Record<string, any>>({});
  const [dataOverview, setDataOverview] = useState<any>(null);
  const [skills, setSkills] = useState<any[]>([]);
  const [officialSkills, setOfficialSkills] = useState<any[]>([]);
  const [connectors, setConnectors] = useState<any[]>([]);
  const [userConnectors, setUserConnectors] = useState<any[]>([]);
  const [mcpConnectors, setMcpConnectors] = useState<any[]>([]);
  const [customConnectors, setCustomConnectors] = useState<any[]>([]);
  const [knowledge, setKnowledge] = useState<any[]>([]);
  const [catCfg, setCatCfg] = useState<Record<string, Record<string, any>>>({});
  const [busy, setBusy] = useState(false);

  const [scheduleForm, setScheduleForm] = useState<any>(null);

  const connectedNames = userConnectors.map((c: any) => c.connector_name);

  const cat = (name: string) => catCfg[name] || {};
  const setCat = (name: string, key: string, value: any) => {
    const next = { ...cat(name), [key]: value };
    setCatCfg((prev) => ({ ...prev, [name]: next }));
    settingsApi.update(name, next).catch(() => toast.add({ title: `Couldn't save ${name} setting`, type: "error" }));
  };
  const catFlag = (name: string, key: string, fallback = true) => {
    const v = cat(name)[key];
    return v === undefined ? fallback : Boolean(v);
  };

  const updatePrefs = async (key: string, value: any) => {
    const next = { ...prefs, [key]: value };
    setPrefs(next);
    try {
      await settingsApi.update("preferences", next);
    } catch {
      toast.add({ title: "Couldn't save preference", type: "error" });
    }
  };

  useEffect(() => {
    settingsApi.get("preferences").then((r: any) => {
      if (r?.preferences) setPrefs(r.preferences);
    }).catch(() => {});
    ["computer", "browser", "security", "agents", "advanced"].forEach((c) => {
      settingsApi.get(c).then((r: any) => {
        if (r && r[c]) setCatCfg((prev) => ({ ...prev, [c]: r[c] }));
      }).catch(() => {});
    });
  }, []);

  useEffect(() => {
    if (user) setFullName(user.full_name || "");
  }, [user]);

  useEffect(() => {
    api.get("/schedules?page_size=20").then((r: any) => setSchedules(r.schedules || [])).catch(() => {});
  }, []);

  useEffect(() => {
    if (user?.role === "ADMIN") {
      api.get("/admin/users?page_size=50").then((r: any) => setUsers(r.users || [])).catch(() => {});
    }
  }, [user]);

  useEffect(() => {
    api.get("/settings/data-controls/overview").then(setDataOverview).catch(() => {});
    api.get("/skills?page_size=50").then((r: any) => setSkills(r.skills || [])).catch(() => {});
    api.get("/skills/official").then((r: any) => setOfficialSkills(r || [])).catch(() => {});
    api.get("/connectors").then((r: any) => setConnectors(r || [])).catch(() => {});
    api.get("/connectors/user").then((r: any) => setUserConnectors(r || [])).catch(() => {});
    api.get("/connectors/mcp").then((r: any) => setMcpConnectors(r || [])).catch(() => {});
    api.get("/connectors/custom-api").then((r: any) => setCustomConnectors(r || [])).catch(() => {});
    api.get("/knowledge?page_size=50").then((r: any) => setKnowledge(r.knowledge || [])).catch(() => {});
  }, []);

  const handleSaveProfile = async () => {
    setSaving(true);
    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const token = localStorage.getItem("access_token");
      await fetch(`${API_BASE}/auth/me`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ full_name: fullName }),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) { console.error(e); } finally { setSaving(false); }
  };

  const handleExecCode = async () => {
    setExecuting(true); setExecResult(null);
    try {
      const r = await api.post("/execution/run", { language: execLang, code: execCode, timeout_seconds: 30 });
      setExecResult(r);
    } catch (e: any) { setExecResult({ success: false, error: e.message }); } finally { setExecuting(false); }
  };

  const reloadSchedules = () => api.get("/schedules?page_size=50").then((r: any) => setSchedules(r.schedules || [])).catch(() => {});
  const reloadSkills = () => {
    api.get("/skills?page_size=50").then((r: any) => setSkills(r.skills || [])).catch(() => {});
    api.get("/skills/official").then((r: any) => setOfficialSkills(r || [])).catch(() => {});
  };
  const reloadConnectors = () => {
    api.get("/connectors/user").then((r: any) => setUserConnectors(r || [])).catch(() => {});
    api.get("/connectors/mcp").then((r: any) => setMcpConnectors(r || [])).catch(() => {});
    api.get("/connectors/custom-api").then((r: any) => setCustomConnectors(r || [])).catch(() => {});
  };
  const reloadKnowledge = () => api.get("/knowledge?page_size=50").then((r: any) => setKnowledge(r.knowledge || [])).catch(() => {});

  const openScheduleForm = (item?: any) => setScheduleForm(item ? { ...item } : {
    title: "", prompt: "", frequency: "DAILY", time_of_day: "09:00", timezone: "UTC",
    cron_expression: "", max_runs: "", skip_confirmations: false, computer: "",
  });
  const saveSchedule = async () => {
    if (!scheduleForm?.title || !scheduleForm?.prompt) {
      toast.add({ title: "Title and prompt are required", type: "error" });
      return;
    }
    setBusy(true);
    const data: any = {
      title: scheduleForm.title,
      prompt: scheduleForm.prompt,
      frequency: scheduleForm.frequency,
      time_of_day: scheduleForm.time_of_day,
      timezone: scheduleForm.timezone || "UTC",
      skip_confirmations: Boolean(scheduleForm.skip_confirmations),
      computer: scheduleForm.computer || undefined,
    };
    if (scheduleForm.frequency === "CRON") data.cron_expression = scheduleForm.cron_expression || "0 9 * * *";
    if (scheduleForm.max_runs) data.max_runs = Number(scheduleForm.max_runs);
    try {
      if (scheduleForm.id) {
        await schedulesApi.update(scheduleForm.id, data);
      } else {
        await schedulesApi.create(data);
      }
      toast.add({ title: "Schedule saved", type: "success" });
      setScheduleForm(null);
      reloadSchedules();
    } catch (e: any) {
      toast.add({ title: e?.message || "Failed to save schedule", type: "error" });
    } finally { setBusy(false); }
  };
  const toggleSchedule = async (id: number, active: boolean) => {
    try {
      if (active) await schedulesApi.pause(id); else await schedulesApi.resume(id);
      reloadSchedules();
    } catch { toast.add({ title: "Failed to update schedule", type: "error" }); }
  };
  const duplicateSchedule = async (id: number) => {
    try { await schedulesApi.duplicate(id); reloadSchedules(); } catch { toast.add({ title: "Failed to duplicate", type: "error" }); }
  };
  const deleteSchedule = async (id: number) => {
    if (!confirm("Delete this schedule?")) return;
    try { await schedulesApi.delete(id); reloadSchedules(); } catch { toast.add({ title: "Failed to delete", type: "error" }); }
  };

  const installSkill = async (name: string) => {
    try { await api.post(`/skills/official/${name}/install`, {}); toast.add({ title: `${name} installed`, type: "success" }); reloadSkills(); } catch { toast.add({ title: "Install failed", type: "error" }); }
  };
  const setSkillState = async (id: number, action: "enable" | "disable") => {
    try {
      await api.post(`/skills/${id}/${action}`, {});
      toast.add({ title: `Skill ${action}d`, type: "success" });
      reloadSkills();
    } catch { toast.add({ title: `Failed to ${action} skill`, type: "error" }); }
  };
  const removeSkill = async (id: number) => {
    if (!confirm("Remove this skill?")) return;
    try {
      await api.delete(`/skills/${id}`);
      toast.add({ title: "Skill removed", type: "success" });
      reloadSkills();
    } catch { toast.add({ title: "Failed to remove skill", type: "error" }); }
  };

  const connectConnector = async (connectorId: number) => {
    const conn = connectors.find((c: any) => c.id === connectorId);
    if (!conn) return;
    const key = prompt(`Paste an API key/token for ${conn.display_name} (or empty for OAuth/None):`) || "";
    try {
      await api.post("/connectors/connect", {
        connector_id: connectorId,
        auth_type: key ? "API_KEY" : "NONE",
        credentials: key ? { api_key: key } : {},
      });
      toast.add({ title: `${conn.display_name} connected`, type: "success" });
      reloadConnectors();
    } catch (e: any) { toast.add({ title: e?.message || "Connect failed", type: "error" }); }
  };
  const removeConnector = async (credentialId: number) => {
    if (!confirm("Disconnect this connector?")) return;
    try { await api.delete(`/connectors/credentials/${credentialId}`); reloadConnectors(); } catch { toast.add({ title: "Disconnect failed", type: "error" }); }
  };
  const addCustomApi = async () => {
    const name = prompt("Custom API name:") || "";
    const baseUrl = prompt("Base URL:") || "";
    if (!name || !baseUrl) { toast.add({ title: "Name and base URL required", type: "error" }); return; }
    try {
      await api.post("/connectors/custom-api", { name, base_url: baseUrl, auth_type: "API_KEY" });
      toast.add({ title: "Custom API added", type: "success" });
      reloadConnectors();
    } catch (e: any) { toast.add({ title: e?.message || "Failed to add", type: "error" }); }
  };
  const addMcp = async () => {
    const name = prompt("MCP server name:") || "";
    const command = prompt("Command (e.g. npx -y @some/mcp-server):") || "";
    if (!name || !command) { toast.add({ title: "Name and command required", type: "error" }); return; }
    try {
      await api.post("/connectors/mcp", { name, command });
      toast.add({ title: "MCP server added", type: "success" });
      reloadConnectors();
    } catch (e: any) { toast.add({ title: e?.message || "Failed to add", type: "error" }); }
  };

  const toggleKnowledge = async (id: number) => {
    try { await api.post(`/knowledge/${id}/toggle`, {}); reloadKnowledge(); } catch { toast.add({ title: "Failed to update knowledge", type: "error" }); }
  };
  const deleteKnowledge = async (id: number) => {
    if (!confirm("Delete this knowledge entry?")) return;
    try { await api.delete(`/knowledge/${id}`); reloadKnowledge(); } catch { toast.add({ title: "Failed to delete", type: "error" }); }
  };
  const addKnowledge = async () => {
    const name = prompt("Knowledge name:") || "";
    const content = prompt("Content / instructions:") || "";
    if (!name || !content) return;
    try {
      await api.post("/knowledge", { name, content, enabled: true });
      toast.add({ title: "Knowledge added", type: "success" });
      reloadKnowledge();
    } catch (e: any) { toast.add({ title: e?.message || "Failed to add", type: "error" }); }
  };

  const setUserRole = async (id: number, role: "ADMIN" | "USER") => {
    try {
      await api.patch(`/admin/users/${id}/role`, { role });
      toast.add({ title: "Role updated", type: "success" });
      api.get("/admin/users?page_size=50").then((r: any) => setUsers(r.users || [])).catch(() => {});
    } catch { toast.add({ title: "Failed to update role", type: "error" }); }
  };

  const tabs = [
    { id: "profile", label: "Profile", icon: User },
    { id: "appearance", label: "Appearance", icon: Sun },
    { id: "scheduled", label: "Scheduled", icon: Calendar },
    { id: "execution", label: "Execution", icon: Code },
    { id: "browser", label: "Browser", icon: Globe },
    { id: "computer", label: "Computer", icon: Monitor },
    { id: "security", label: "Security", icon: Lock },
    { id: "core-laws", label: "Core Laws", icon: ShieldAlert },
    { id: "blueprints", label: "Blueprints", icon: BookOpen },
    { id: "advanced", label: "Advanced", icon: Network },
    { id: "users", label: "Users", icon: Users },
    { id: "data", label: "Data", icon: Database },
    { id: "skills", label: "Skills", icon: Brain },
    { id: "connectors", label: "Connectors", icon: Plug },
    { id: "knowledge", label: "Knowledge", icon: BookOpen },
    { id: "memory", label: "Memory", icon: Brain },
    { id: "agents", label: "Agents", icon: Bot },
    { id: "ai-models", label: "AI Studio", icon: Cpu },
    { id: "admin", label: "Admin", icon: ShieldCheck },
    { id: "about", label: "About", icon: Info },
  ];

  const filteredTabs = tabs.filter((t) =>
    t.label.toLowerCase().includes(search.trim().toLowerCase())
  );

  const listRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = 0;
  }, [search]);

  return (
    <div className="flex h-full items-start gap-4 min-h-0 flex-1">
      <Tabs value={tab} onValueChange={setTab} orientation="vertical" className="flex h-full w-full gap-4 min-h-0">
        <div className="flex flex-col w-[28%] shrink-0 min-h-0 gap-2 border-r border-zinc-200 dark:border-zinc-800">
          <div className="relative shrink-0 py-0.5">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search…"
              className="pl-8 h-9 text-sm rounded-full border-2 border-zinc-300 bg-white dark:bg-zinc-800 dark:border-zinc-600 focus:border-blue-500 dark:focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
            />
          </div>
          <div ref={listRef} className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-zinc-400 dark:[&::-webkit-scrollbar-thumb]:bg-zinc-500">
            <TabsList style={{ height: "auto" }} className="flex flex-col w-full space-y-0.5 bg-transparent p-0">
              {filteredTabs.map(t => (
                <TabsTrigger key={t.id} value={t.id} className="justify-start pl-5 gap-2 w-full text-left text-base py-1.5 mr-2">
                  <t.icon className="h-4 w-4 shrink-0" />{t.label}
                </TabsTrigger>
              ))}
              {filteredTabs.length === 0 && (
                <p className="px-2 py-2 text-xs text-zinc-400">No settings match “{search}”.</p>
              )}
            </TabsList>
          </div>
        </div>

        <div className="flex-1 min-w-0 min-h-0 overflow-y-auto">
          <TabsContent value="profile">
            <Card><CardHeader><CardTitle className="text-base">Your Profile</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div><label className="text-sm font-medium">Email</label><Input value={user?.email || ""} disabled className="mt-1 bg-zinc-50 dark:bg-zinc-800/50" /></div>
                <div><label className="text-sm font-medium">Full Name</label><Input value={fullName} onChange={e => setFullName(e.target.value)} placeholder="Your name" className="mt-1" /></div>
                <div><label className="text-sm font-medium">Role</label><div className="mt-1"><Badge variant="outline">{user?.role || "USER"}</Badge></div></div>
                <Button onClick={handleSaveProfile} disabled={saving}>
                  {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : saved ? <CheckCircle2 className="mr-2 h-4 w-4" /> : null}
                  {saved ? "Saved!" : "Save Changes"}
                </Button>
                <div className="border-t pt-4 space-y-4">
                  <div>
                    <label className="text-sm font-medium block">Custom instructions</label>
                    <p className="text-xs text-zinc-500">Additional behavior, style, and tone preferences.</p>
                    <textarea
                      value={prefs.customInstructions || ""}
                      onChange={(e) => updatePrefs("customInstructions", e.target.value)}
                      rows={3}
                      placeholder="e.g. Always answer in plain words, then show the technical details…"
                      className="w-full mt-1.5 px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800"
                    />
                  </div>
                  <p className="text-sm font-medium pt-2">About you</p>
                  <div>
                    <label className="text-sm font-medium block">Nickname</label>
                    <p className="text-xs text-zinc-500">What should Mark-Imti call you?</p>
                    <Input value={prefs.nickname || ""} onChange={(e) => updatePrefs("nickname", e.target.value)} placeholder="Your nickname" className="mt-1.5" />
                  </div>
                  <div>
                    <label className="text-sm font-medium block">Occupation</label>
                    <select value={prefs.occupation || ""} onChange={(e) => updatePrefs("occupation", e.target.value)} className="mt-1.5 w-full px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800">
                      <option value="">Select…</option>
                      <option>Student</option>
                      <option>Professional</option>
                      <option>Programmer</option>
                      <option>Developer</option>
                      <option>Researcher</option>
                      <option>Entrepreneur</option>
                      <option>Teacher</option>
                      <option>Other</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-sm font-medium block">More about you</label>
                    <p className="text-xs text-zinc-500">Interests, values, or preferences to keep in mind.</p>
                    <textarea
                      value={prefs.moreAboutYou || ""}
                      onChange={(e) => updatePrefs("moreAboutYou", e.target.value)}
                      rows={3}
                      placeholder="e.g. I care about clean design, privacy, and shipping fast…"
                      className="w-full mt-1.5 px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="appearance">
            <Card><CardHeader><CardTitle className="text-base">Appearance</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div><label className="text-sm font-medium mb-2 block">Theme</label>
                  <div className="flex gap-2">{["light", "dark", "system"].map(t => (
                    <Button key={t} variant={theme === t ? "default" : "outline"} onClick={() => setTheme(t)} className="capitalize">{t}</Button>
                  ))}</div></div>
                <div><label className="text-sm font-medium mb-2 block">Language</label>
                  <select value={language} onChange={e => setLanguage(e.target.value)} className="px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800">
                    <option value="en">English</option><option value="es">Español</option><option value="ja">日本語</option><option value="de">Deutsch</option><option value="fr">Français</option>
                  </select></div>
                <div>
                  <label className="text-sm font-medium block">Choose additional customizations</label>
                  <p className="text-xs text-zinc-500 mb-2">Customizations on top of your base style and tone.</p>
                  <select value={prefs.styleTone || "Professional"} onChange={e => updatePrefs("styleTone", e.target.value)} className="w-full px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800">
                    <option>Professional</option><option>Formal</option><option>Casual</option><option>Friendly</option><option>Concise</option><option>Detailed</option>
                  </select>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="scheduled">
            <Card><CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="text-base flex items-center gap-2"><Calendar className="h-4 w-4" /> Scheduled Tasks</CardTitle>
              <Button size="sm" onClick={() => openScheduleForm()}>
                <Plus className="mr-1.5 h-4 w-4" /> New Schedule
              </Button>
            </CardHeader>
              <CardContent className="space-y-3">
                {scheduleForm && (
                  <form onSubmit={(e) => { e.preventDefault(); saveSchedule(); }} className="border rounded-lg p-3 space-y-3 bg-zinc-50 dark:bg-zinc-900/50">
                    <p className="text-sm font-medium">{scheduleForm.id ? "Edit schedule" : "New schedule"}</p>
                    <Field label="Title"><Input value={scheduleForm.title} onChange={(e) => setScheduleForm({ ...scheduleForm, title: e.target.value })} placeholder="e.g. Morning briefing" /></Field>
                    <Field label="Prompt"><textarea value={scheduleForm.prompt} onChange={(e) => setScheduleForm({ ...scheduleForm, prompt: e.target.value })} rows={2} placeholder="What Mark should do each run…" className="w-full px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800" /></Field>
                    <div className="grid grid-cols-2 gap-3">
                      <Field label="Frequency">
                        <select value={scheduleForm.frequency} onChange={(e) => setScheduleForm({ ...scheduleForm, frequency: e.target.value })} className="w-full px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800">
                          <option value="DAILY">Daily</option><option value="WEEKLY">Weekly</option><option value="MONTHLY">Monthly</option><option value="ONCE">Once</option><option value="CRON">Cron</option>
                        </select>
                      </Field>
                      <Field label="Time of day (HH:MM)"><Input value={scheduleForm.time_of_day} onChange={(e) => setScheduleForm({ ...scheduleForm, time_of_day: e.target.value })} placeholder="09:00" /></Field>
                    </div>
                    {scheduleForm.frequency === "CRON" && (
                      <Field label="Cron expression" hint="e.g. 0 9 * * 1-5">
                        <Input value={scheduleForm.cron_expression} onChange={(e) => setScheduleForm({ ...scheduleForm, cron_expression: e.target.value })} placeholder="0 9 * * *" />
                      </Field>
                    )}
                    <div className="grid grid-cols-2 gap-3">
                      <Field label="Timezone"><Input value={scheduleForm.timezone} onChange={(e) => setScheduleForm({ ...scheduleForm, timezone: e.target.value })} placeholder="UTC" /></Field>
                      <Field label="Max runs (optional)"><Input type="number" value={scheduleForm.max_runs} onChange={(e) => setScheduleForm({ ...scheduleForm, max_runs: e.target.value })} placeholder="Unlimited" /></Field>
                    </div>
                    <SettingRow title="Skip confirmations" desc="Run without waiting for manual approval." control={<Toggle checked={Boolean(scheduleForm.skip_confirmations)} onChange={(v) => setScheduleForm({ ...scheduleForm, skip_confirmations: v })} />} />
                    <div className="flex gap-2">
                      <Button type="submit" size="sm" disabled={busy}>
                        {busy ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <Save className="mr-1.5 h-4 w-4" />}
                        {busy ? "Saving…" : "Save"}
                      </Button>
                      <Button type="button" size="sm" variant="outline" onClick={() => setScheduleForm(null)}><X className="mr-1.5 h-4 w-4" /> Cancel</Button>
                    </div>
                  </form>
                )}
                {schedules.length === 0 ? (
                  <p className="text-sm text-zinc-500">No scheduled tasks yet. Create one to automate recurring work.</p>
                ) : (
                  <div className="space-y-2">{schedules.map((s: any) => (
                    <div key={s.id} className="flex items-center justify-between gap-3 p-3 border rounded-lg">
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{s.title || `Schedule #${s.id}`}</p>
                        <p className="text-xs text-zinc-500">{s.frequency}{s.cron_expression ? ` • ${s.cron_expression}` : ""} • {s.time_of_day} {s.timezone} {s.next_run_at ? `• next ${new Date(s.next_run_at).toLocaleString()}` : ""}</p>
                        {s.prompt && <p className="text-xs text-zinc-400 mt-0.5 truncate">{s.prompt}</p>}
                      </div>
                      <div className="flex items-center gap-1.5 shrink-0">
                        <Badge variant={s.is_active ? "default" : "secondary"}>{s.is_active ? "Active" : "Paused"}</Badge>
                        <Button size="icon" variant="ghost" className="h-8 w-8" title={s.is_active ? "Pause" : "Resume"} onClick={() => toggleSchedule(s.id, s.is_active)}>
                          {s.is_active ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                        </Button>
                        <Button size="icon" variant="ghost" className="h-8 w-8" title="Edit" onClick={() => openScheduleForm(s)}><Pencil className="h-4 w-4" /></Button>
                        <Button size="icon" variant="ghost" className="h-8 w-8" title="Duplicate" onClick={() => duplicateSchedule(s.id)}><Copy className="h-4 w-4" /></Button>
                        <Button size="icon" variant="ghost" className="h-8 w-8 text-red-500" title="Delete" onClick={() => deleteSchedule(s.id)}><Trash2 className="h-4 w-4" /></Button>
                      </div>
                    </div>
                  ))}</div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="execution">
            <Card><CardHeader><CardTitle className="text-base flex items-center gap-2"><Code className="h-4 w-4" /> Code Execution</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <div className="flex gap-2">
                  <select value={execLang} onChange={e => setExecLang(e.target.value)} className="px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800">
                    <option value="python">Python</option><option value="javascript">JavaScript</option><option value="shell">Shell</option>
                  </select>
                </div>
                <textarea value={execCode} onChange={e => setExecCode(e.target.value)} className="w-full min-h-[120px] px-3 py-2 text-sm font-mono border rounded-lg dark:bg-zinc-800" placeholder="Write code..." />
                <Button onClick={handleExecCode} disabled={executing}>
                  {executing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
                  {executing ? "Running..." : "Run Code"}
                </Button>
                {execResult && (
                  <div className={`p-3 rounded-lg text-sm font-mono ${execResult.success !== false ? "bg-green-50 dark:bg-green-900/20" : "bg-red-50 dark:bg-red-900/20"}`}>
                    {execResult.stdout || execResult.error || JSON.stringify(execResult)}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="browser">
            <Card><CardHeader><CardTitle className="text-base flex items-center gap-2"><Globe className="h-4 w-4" /> Browser Automation</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-zinc-500">Control a headless browser for web scraping, form filling, and automation.</p>
                <SettingRow title="Web search" desc="Let Mark-Imti automatically search the web for current answers." control={<Toggle checked={catFlag("browser", "web_search", prefs.webSearch !== false)} onChange={(v) => { setCat("browser", "web_search", v); updatePrefs("webSearch", v); }} />} />
                <SettingRow title="Dark web browsing" desc="Let Mark-Imti explore deep and dark web sources through Tor for advanced research." control={<Toggle checked={catFlag("browser", "dark_web", prefs.darkWeb !== false)} onChange={(v) => { setCat("browser", "dark_web", v); updatePrefs("darkWeb", v); }} />} />
                <SettingRow title="Browser enabled" desc="Enable the built-in browser for agents and scheduled tasks." control={<Toggle checked={catFlag("browser", "enabled")} onChange={(v) => setCat("browser", "enabled", v)} />} />
                <SettingRow title="Headless mode" desc="Run the browser in the background without a visible window." control={<Toggle checked={catFlag("browser", "headless")} onChange={(v) => setCat("browser", "headless", v)} />} />
                <SettingRow title="Incognito / private" desc="Do not persist cookies, history, or logins between sessions." control={<Toggle checked={catFlag("browser", "incognito", false)} onChange={(v) => setCat("browser", "incognito", v)} />} />
                <Field label="Max concurrent sessions" hint="How many browser sessions agents may open at once.">
                  <Input type="number" min={1} value={cat("browser").max_concurrency || 3} onChange={(e) => setCat("browser", "max_concurrency", Number(e.target.value))} className="w-32" />
                </Field>
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 border rounded-lg"><p className="text-sm font-medium">Status</p><Badge variant="outline" className="mt-1">{catFlag("browser", "enabled") ? "Configured" : "Disabled"}</Badge></div>
                  <div className="p-3 border rounded-lg"><p className="text-sm font-medium">Capability check</p><Badge variant="outline" className="mt-1"><a href="/chat?mode=browse" className="flex items-center gap-1">Test <ExternalLink className="h-3 w-3" /></a></Badge></div>
                </div>
                <SettingRow title="Library search" desc="Allow Mark to search uploaded files for answers." control={<Toggle checked={prefs.librarySearch !== false} onChange={(v) => updatePrefs("librarySearch", v)} />} />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="computer">
            <Card><CardHeader><CardTitle className="text-base flex items-center gap-2"><Monitor className="h-4 w-4" /> Computer Control</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-zinc-500">Allow the agent to control mouse, keyboard, and take screenshots.</p>
                <SettingRow title="Mouse control" desc="Let the agent move the cursor and click, drag, and select." control={<Toggle checked={catFlag("computer", "mouse")} onChange={(v) => setCat("computer", "mouse", v)} />} />
                <SettingRow title="Keyboard control" desc="Let the agent type and press keys on your computer." control={<Toggle checked={catFlag("computer", "keyboard")} onChange={(v) => setCat("computer", "keyboard", v)} />} />
                <SettingRow title="Screenshots" desc="Allow the agent to capture screenshots to understand your screen." control={<Toggle checked={catFlag("computer", "screenshots")} onChange={(v) => setCat("computer", "screenshots", v)} />} />
                <SettingRow title="OS commands" desc="Run shell/OS commands on this machine. Recommended to keep off." control={<Toggle checked={catFlag("computer", "os_commands", false)} onChange={(v) => setCat("computer", "os_commands", v)} />} />
                <Field label="Autonomy level" hint="How much the agent may act without asking first.">
                  <select value={cat("computer").autonomy || "supervised"} onChange={(e) => setCat("computer", "autonomy", e.target.value)} className="w-full px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800">
                    <option value="manual">Manual — always ask first</option>
                    <option value="supervised">Supervised — ask for risky actions</option>
                    <option value="autonomous">Autonomous — act on its own</option>
                  </select>
                </Field>
                <p className="text-xs text-zinc-400">Changes apply to new tasks immediately.</p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="security">
            <Card><CardHeader><CardTitle className="text-base flex items-center gap-2"><Lock className="h-4 w-4" /> Security</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <SettingRow title="Password policy" desc="Enforce a strong-password policy (min 8 chars, complexity)." control={<Toggle checked={catFlag("security", "password_policy")} onChange={(v) => setCat("security", "password_policy", v)} />} />
                <SettingRow title="Rate limiting" desc="Protect API and auth endpoints from brute force and abuse." control={<Toggle checked={catFlag("security", "rate_limiting")} onChange={(v) => setCat("security", "rate_limiting", v)} />} />
                <SettingRow title="JWT tokens" desc="Access + refresh token authentication for API clients." control={<Toggle checked={catFlag("security", "jwt")} onChange={(v) => setCat("security", "jwt", v)} />} />
                <SettingRow title="RBAC" desc="Role-based access control (ADMIN / USER)." control={<Toggle checked={catFlag("security", "rbac")} onChange={(v) => setCat("security", "rbac", v)} />} />
                <Field label="Session timeout (minutes)" hint="How long a login stays valid before re-authentication.">
                  <Input type="number" min={5} value={cat("security").session_timeout_min || 60} onChange={(e) => setCat("security", "session_timeout_min", Number(e.target.value))} className="w-32" />
                </Field>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="core-laws">
            <CoreLawsPanel />
          </TabsContent>

          <TabsContent value="blueprints">
            <Card><CardHeader><CardTitle className="text-base flex items-center gap-2"><BookOpen className="h-4 w-4" /> Blueprints</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-zinc-500">Reusable task templates. Define once, run anytime.</p>
                <div className="p-4 border-2 border-dashed rounded-lg text-center text-zinc-400">
                  <BookOpen className="h-8 w-8 mx-auto mb-2" />
                  <p className="text-sm">No blueprints yet. Create one by saving a task as a blueprint.</p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="advanced">
            <Card><CardHeader><CardTitle className="text-base flex items-center gap-2"><Network className="h-4 w-4" /> Advanced Settings</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <SettingRow title="Canvas" desc="Collaborate with Mark-Imti on shared text and code documents." control={<Toggle checked={prefs.canvas !== false} onChange={(v) => updatePrefs("canvas", v)} />} />
                <SettingRow title="Multi-agent orchestration" desc="Supervisor agent coordinates specialist agents for complex tasks." control={<Toggle checked={catFlag("agents", "multi_agent")} onChange={(v) => setCat("agents", "multi_agent", v)} />} />
                <SettingRow title="Memory engine" desc="Agent remembers context across conversations and tasks." control={<Toggle checked={catFlag("advanced", "memory_engine")} onChange={(v) => setCat("advanced", "memory_engine", v)} />} />
                <SettingRow title="Task recovery" desc="Automatic retry and rollback on failed tasks." control={<Toggle checked={catFlag("advanced", "task_recovery")} onChange={(v) => setCat("advanced", "task_recovery", v)} />} />
                <SettingRow title="Self-evolution" desc="Agent improves its own prompts and workflows over time." control={<Toggle checked={catFlag("advanced", "self_evolution", false)} onChange={(v) => setCat("advanced", "self_evolution", v)} />} />
                <SettingRow title="Blueprints enabled" desc="Reusable task templates. Define once, run anytime." control={<Toggle checked={catFlag("advanced", "blueprints_enabled")} onChange={(v) => setCat("advanced", "blueprints_enabled", v)} />} />
                <Field label="Approval mode" hint="When the agent must pause for human approval.">
                  <select value={cat("advanced").approval_mode || "auto"} onChange={(e) => setCat("advanced", "approval_mode", e.target.value)} className="w-full px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800">
                    <option value="auto">Auto — only destructive actions</option>
                    <option value="ask">Ask — every action needs approval</option>
                    <option value="off">Off — always run</option>
                  </select>
                </Field>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="users">
            <Card><CardHeader><CardTitle className="text-base flex items-center gap-2"><Users className="h-4 w-4" /> User Management</CardTitle></CardHeader>
              <CardContent>
                {user?.role !== "ADMIN" ? (
                  <p className="text-sm text-zinc-500">Admin access required.</p>
                ) : users.length === 0 ? (
                  <p className="text-sm text-zinc-500">No users found.</p>
                ) : (
                  <div className="space-y-2">{users.map((u: any) => (
                    <div key={u.id} className="flex items-center justify-between gap-3 p-3 border rounded-lg">
                      <div className="min-w-0">
                        <p className="text-sm font-medium">{u.full_name || u.email}</p>
                        <p className="text-xs text-zinc-500">{u.email}</p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        {u.id === user?.id ? (
                          <Badge variant="outline">You</Badge>
                        ) : (
                          <select
                            value={u.role}
                            onChange={(e) => setUserRole(u.id, e.target.value as "ADMIN" | "USER")}
                            className="px-2 py-1.5 text-xs border rounded-lg dark:bg-zinc-800"
                          >
                            <option value="USER">USER</option>
                            <option value="ADMIN">ADMIN</option>
                          </select>
                        )}
                        <Badge variant={u.role === "ADMIN" ? "default" : "outline"}>{u.role}</Badge>
                      </div>
                    </div>
                  ))}</div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="data">
            <Card><CardHeader><CardTitle className="text-base flex items-center gap-2"><Database className="h-4 w-4" /> Data & Storage</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between p-3 border rounded-lg">
                  <div><p className="text-sm font-medium">Your Data</p><p className="text-xs text-zinc-500">All data is stored locally on your machine</p></div>
                  <Badge variant="outline" className="bg-green-50 text-green-700"><Shield className="mr-1 h-3 w-3" />Private</Badge>
                </div>
                <div className="flex items-center justify-between p-3 border rounded-lg">
                  <div><p className="text-sm font-medium">Database</p><p className="text-xs text-zinc-500">SQLite — mark_imti.db in backend folder</p></div>
                </div>
                <div className="border-t pt-3">
                  <p className="text-sm font-medium mb-2">What's stored in your Library</p>
                  {!dataOverview ? (
                    <p className="text-sm text-zinc-500">Loading…</p>
                  ) : (
                    <div className="grid grid-cols-2 gap-2">
                      <Stat icon={<FileText className="h-5 w-5" />} label="Files uploaded" value={dataOverview.uploads ?? 0} />
                      <Stat icon={<ImageIcon className="h-5 w-5" />} label="Images" value={dataOverview.images ?? 0} />
                      <Stat icon={<FileText className="h-5 w-5" />} label="Documents" value={dataOverview.documents ?? 0} />
                      <Stat icon={<Video className="h-5 w-5" />} label="Videos" value={dataOverview.videos ?? 0} />
                      <Stat icon={<Music className="h-5 w-5" />} label="Audio" value={dataOverview.audio ?? 0} />
                      <Stat icon={<Database className="h-5 w-5" />} label="Spreadsheets" value={dataOverview.spreadsheets ?? 0} />
                      <Stat icon={<Globe className="h-5 w-5" />} label="Generated websites" value={dataOverview.deployed_websites ?? 0} />
                      <Stat icon={<Cpu className="h-5 w-5" />} label="Generated apps" value={dataOverview.apps ?? 0} />
                      <Stat icon={<BookOpen className="h-5 w-5" />} label="Knowledge entries" value={dataOverview.knowledge ?? 0} />
                      <Stat icon={<Brain className="h-5 w-5" />} label="Memories" value={dataOverview.memories ?? 0} />
                      <Stat icon={<Brain className="h-5 w-5" />} label="Skills installed" value={dataOverview.skills ?? 0} />
                      <Stat icon={<Shield className="h-5 w-5" />} label="Shared files" value={dataOverview.shared_files ?? 0} />
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="skills">
            <Card><CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="text-base flex items-center gap-2"><Brain className="h-4 w-4" /> Skills</CardTitle>
              <Button size="sm" variant="outline" onClick={() => window.location.href = "/skills"}><ExternalLink className="mr-1.5 h-4 w-4" /> Manage Skills</Button>
            </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-zinc-500">Installed skills — reusable capabilities Mark can load on demand. Toggle each skill on or off, or remove it entirely.</p>
                {skills.length === 0 ? (
                  <p className="text-sm text-zinc-500">No skills installed yet — pick some from the registry below.</p>
                ) : (
                  <div className="space-y-2">
                    {skills.map((s: any) => (
                      <div key={`sk-${s.id}`} className="flex items-start justify-between gap-3 p-3 border rounded-lg">
                        <div className="min-w-0">
                          <p className="text-sm font-medium">{s.display_name || s.name}</p>
                          {s.description && <p className="text-xs text-zinc-500 mt-0.5 truncate">{s.description}</p>}
                          <div className="flex flex-wrap gap-1 mt-1.5">
                            <Badge variant="outline" className="text-[10px]">v{s.version}</Badge>
                            <Badge variant="outline" className="text-[10px]">{s.source}</Badge>
                            {(s.tools || []).slice(0, 4).map((t: string) => <Badge key={t} variant="secondary" className="text-[10px]">{t}</Badge>)}
                          </div>
                        </div>
                        <div className="flex items-center gap-1.5 shrink-0">
                          <Toggle
                            checked={s.status === "ENABLED" || s.status === "INSTALLED"}
                            onChange={() => setSkillState(s.id, (s.status === "ENABLED" || s.status === "INSTALLED") ? "disable" : "enable")}
                          />
                          <Button size="icon" variant="ghost" className="h-8 w-8 text-red-500" title="Remove" onClick={() => removeSkill(s.id)}><Trash2 className="h-4 w-4" /></Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                <div className="border-t pt-3">
                  <p className="text-sm font-medium mb-2">Mark's registry ({officialSkills.length} skills)</p>
                  {officialSkills.length === 0 ? (
                    <p className="text-sm text-zinc-500">No official skills available.</p>
                  ) : (
                    <div className="space-y-2">
                      {officialSkills
                        .filter((s: any) => !skills.some((sk: any) => sk.name === s.name))
                        .map((s: any) => (
                          <div key={`off-${s.name}`} className="flex items-start justify-between gap-3 p-3 border rounded-lg">
                            <div className="min-w-0">
                              <p className="text-sm font-medium">{s.display_name || s.name}</p>
                              <p className="text-xs text-zinc-500 mt-0.5 line-clamp-1">{s.description}</p>
                              {(s.category && <Badge variant="outline" className="text-[10px] mt-1 mr-1">{s.category}</Badge>)}
                              {(s.tools || []).slice(0, 3).map((t: string) => <Badge key={t} variant="secondary" className="text-[10px]">{t}</Badge>)}
                            </div>
                            <Button size="sm" variant="outline" className="shrink-0" onClick={() => installSkill(s.name)}>
                              <Plus className="mr-1 h-3.5 w-3.5" /> Install
                            </Button>
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="connectors">
            <Card><CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="text-base flex items-center gap-2"><Plug className="h-4 w-4" /> Connectors</CardTitle>
              <Button size="sm" variant="outline" onClick={() => window.location.href = "/connectors"}><ExternalLink className="mr-1.5 h-4 w-4" /> Manage Connectors</Button>
            </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-zinc-500">Connect Mark to external services, apps, and your computer.</p>
                <SettingRow title="Connector search" desc="Let Mark-Imti automatically search connected sources for answers." control={<Toggle checked={prefs.connectorSearch !== false} onChange={(v) => updatePrefs("connectorSearch", v)} />} />
                <div className="border-t pt-3">
                  <p className="text-sm font-medium mb-2">Your connected apps & sources</p>
                  {userConnectors.length === 0 ? (
                    <p className="text-sm text-zinc-500">No connectors connected yet.</p>
                  ) : (
                    <div className="space-y-2">
                      {userConnectors.map((c: any) => (
                        <div key={c.id} className="flex items-center justify-between gap-3 p-3 border rounded-lg">
                          <div className="min-w-0">
                            <p className="text-sm font-medium">{c.connector_name}</p>
                            <p className="text-xs text-zinc-500">{c.connector_type} &bull; {c.auth_type}</p>
                            {c.last_sync_at && <p className="text-[10px] text-zinc-400 mt-0.5">Last sync {new Date(c.last_sync_at).toLocaleDateString()}</p>}
                          </div>
                          <div className="flex items-center gap-1.5 shrink-0">
                            <Badge variant="default" className="bg-green-600">{c.status}</Badge>
                            <Button size="icon" variant="ghost" className="h-8 w-8" title="Disconnect" onClick={() => removeConnector(c.id)}><Link2 className="h-4 w-4" /></Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <div className="border-t pt-3">
                  <p className="text-sm font-medium mb-2">Available connectors</p>
                  {connectors.length === 0 ? (
                    <p className="text-sm text-zinc-500">None available.</p>
                  ) : (
                    <div className="space-y-2">
                      {connectors.map((c: any) => (
                        <div key={c.id} className="flex items-center justify-between gap-3 p-3 border rounded-lg">
                          <div className="flex items-center gap-2 min-w-0">
                            <span className="text-lg shrink-0">{c.icon || "🔌"}</span>
                            <div className="min-w-0">
                              <p className="text-sm font-medium">{c.display_name}</p>
                              {c.description && <p className="text-xs text-zinc-500 truncate">{c.description}</p>}
                            </div>
                          </div>
                          {connectedNames.includes(c.name)
                            ? <Badge variant="default" className="bg-green-600 shrink-0">Connected</Badge>
                            : <Button size="sm" variant="outline" className="shrink-0" onClick={() => connectConnector(c.id)}><Link2 className="mr-1 h-3.5 w-3.5" /> Connect</Button>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-3 border-t pt-3">
                  <div className="p-3 border rounded-lg">
                    <p className="text-sm font-medium flex items-center justify-between"><span>Custom API</span><span className="text-xs text-zinc-400">{customConnectors.length}</span></p>
                    <p className="text-xs text-zinc-500 mt-1">{customConnectors.length === 0 ? "No custom APIs configured." : customConnectors.map((c: any) => c.name).join(", ")}</p>
                    <Button size="sm" variant="outline" className="mt-2" onClick={addCustomApi}><Plus className="mr-1 h-3.5 w-3.5" /> Add custom API</Button>
                  </div>
                  <div className="p-3 border rounded-lg">
                    <p className="text-sm font-medium flex items-center justify-between"><span>MCP Servers</span><span className="text-xs text-zinc-400">{mcpConnectors.length}</span></p>
                    <p className="text-xs text-zinc-500 mt-1">{mcpConnectors.length === 0 ? "No MCP servers configured." : mcpConnectors.map((c: any) => c.name).join(", ")}</p>
                    <Button size="sm" variant="outline" className="mt-2" onClick={addMcp}><Plus className="mr-1 h-3.5 w-3.5" /> Add MCP server</Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="knowledge">
            <Card><CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="text-base flex items-center gap-2"><BookOpen className="h-4 w-4" /> Knowledge</CardTitle>
              <Button size="sm" onClick={addKnowledge}><Plus className="mr-1.5 h-4 w-4" /> Add knowledge</Button>
            </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-zinc-500">Mark's knowledge base — instructions, notes, documents, and RAG sources.</p>
                <SettingRow title="Library search" desc="Allow Mark-Imti to automatically search Library files for answers." control={<Toggle checked={prefs.librarySearch !== false} onChange={(v) => updatePrefs("librarySearch", v)} />} />
                <div className="border-t pt-3">
                  <p className="text-sm font-medium mb-2">All knowledge entries ({knowledge.length})</p>
                  {knowledge.length === 0 ? (
                    <p className="text-sm text-zinc-500">No knowledge entries yet. Click "Add knowledge" to create one.</p>
                  ) : (
                    <div className="space-y-2">
                      {knowledge.map((k: any) => {
                        const tags = Array.isArray(k.tags) ? k.tags : [];
                        return (
                          <div key={k.id} className="flex items-start justify-between gap-3 p-3 border rounded-lg">
                            <div className="min-w-0">
                              <p className="text-sm font-medium">{k.name}</p>
                              {k.use_when && <p className="text-xs text-zinc-500 mt-0.5 truncate">{k.use_when}</p>}
                              {k.project_name && <p className="text-[10px] text-zinc-400 mt-0.5">Project: {k.project_name}</p>}
                              {tags.length > 0 && (
                                <div className="flex flex-wrap gap-1 mt-1.5">
                                  {tags.slice(0, 4).map((t: any) => (
                                    <Badge key={String(t)} variant="secondary" className="text-[10px]">{String(t)}</Badge>
                                  ))}
                                  {tags.length > 4 && <span className="text-[10px] text-zinc-400">+{tags.length - 4}</span>}
                                </div>
                              )}
                            </div>
                            <div className="flex items-center gap-1.5 shrink-0">
                              <Button size="icon" variant="ghost" className="h-8 w-8" title={k.enabled ? "Disable" : "Enable"} onClick={() => toggleKnowledge(k.id)}>
                                {k.enabled ? <Power className="h-4 w-4 text-green-600" /> : <Power className="h-4 w-4 text-zinc-400" />}
                              </Button>
                              <Button size="icon" variant="ghost" className="h-8 w-8 text-red-500" title="Delete" onClick={() => deleteKnowledge(k.id)}><Trash2 className="h-4 w-4" /></Button>
                              <Badge variant={k.enabled ? "default" : "secondary"}>{k.enabled ? "Enabled" : "Disabled"}</Badge>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
                <Button variant="outline" onClick={() => window.location.href = "/knowledge"}><ExternalLink className="mr-2 h-4 w-4" /> Open Knowledge</Button>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="ai-models">
            <Card><CardHeader><CardTitle className="text-base flex items-center gap-2"><Cpu className="h-4 w-4" /> AI Models & Studio</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-zinc-500">Configure cloud and local AI models. Set API keys, choose defaults, and download local models for on-device inference.</p>
                <SettingRow title="Fast Answer" desc="Mark can use general knowledge for fast answers without memory context." control={<Toggle checked={prefs.fastAnswer !== false} onChange={(v) => updatePrefs("fastAnswer", v)} />} />

                {/* Cloud Models */}
                <div className="border-t pt-4">
                  <p className="text-sm font-medium mb-3">Cloud Models</p>
                  <div className="grid grid-cols-1 gap-3">
                    {[
                      { provider: "OPENAI", name: "OpenAI", models: ["GPT-5", "GPT-5 Mini", "GPT-4o", "o3"], color: "text-green-600" },
                      { provider: "ANTHROPIC", name: "Anthropic", models: ["Claude 4 Opus", "Claude 4 Sonnet", "Claude 3.5 Haiku"], color: "text-orange-600" },
                      { provider: "GOOGLE", name: "Google", models: ["Gemini 2.5 Pro", "Gemini 2.5 Flash", "Gemini 2.0"], color: "text-blue-600" },
                      { provider: "DEEPSEEK", name: "DeepSeek", models: ["DeepSeek V4", "DeepSeek V3", "DeepSeek Coder"], color: "text-purple-600" },
                      { provider: "MISTRAL", name: "Mistral", models: ["Mistral Large", "Mistral Small", "Codestral"], color: "text-cyan-600" },
                      { provider: "XAI", name: "xAI (Grok)", models: ["Grok 4", "Grok 3"], color: "text-zinc-600" },
                      { provider: "OPENROUTER", name: "OpenRouter", models: ["All models via proxy"], color: "text-indigo-600" },
                    ].map((p) => (
                      <div key={p.provider} className="border rounded-lg p-3 space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className={cn("h-2 w-2 rounded-full", p.color.replace("text-", "bg-"))} />
                            <span className="text-sm font-medium">{p.name}</span>
                          </div>
                          <Button size="sm" variant="outline" onClick={() => {
                            const key = prompt(`Enter API key for ${p.name}:`);
                            if (key !== null) {
                              api.post("/models/providers", { provider: p.provider, api_key: key })
                                .then(() => toast.add({ title: `${p.name} configured`, type: "success" }))
                                .catch(() => toast.add({ title: `Failed to configure ${p.name}`, type: "error" }));
                            }
                          }}>Configure</Button>
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {p.models.map((m) => (
                            <Badge key={m} variant="secondary" className="text-[10px]">{m}</Badge>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Local Models (Ollama) */}
                <div className="border-t pt-4">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <p className="text-sm font-medium">Local Models (Ollama)</p>
                      <p className="text-xs text-zinc-500">Run models on your device — no API key needed, fully private.</p>
                    </div>
                    <Button size="sm" variant="outline" onClick={() => {
                      api.post("/models/providers", { provider: "OLLAMA", base_url: "http://localhost:11434" })
                        .then(() => toast.add({ title: "Ollama connected", type: "success" }))
                        .catch(() => toast.add({ title: "Ollama not running — start with `ollama serve`", type: "error" }));
                    }}>Connect Ollama</Button>
                  </div>
                  <div className="grid grid-cols-1 gap-2">
                    {[
                      { id: "qwen3.5:8b", name: "Qwen 3.5 8B", size: "5.2 GB", desc: "Best all-round local model — coding, reasoning, chat", recommended: true },
                      { id: "qwen3-coder:7b", name: "Qwen3 Coder 7B", size: "4.4 GB", desc: "Optimized for code generation and editing" },
                      { id: "gemma3:12b", name: "Gemma 3 12B", size: "7.5 GB", desc: "Google's open model — strong reasoning" },
                      { id: "llama3.3:8b", name: "Llama 3.3 8B", size: "4.9 GB", desc: "Meta's latest — fast and capable" },
                      { id: "deepseek-coder:6.7b", name: "DeepSeek Coder 6.7B", size: "4.2 GB", desc: "Specialized coding model" },
                      { id: "phi4:14b", name: "Phi-4 14B", size: "8.7 GB", desc: "Microsoft's small but powerful model" },
                      { id: "mistral:7b", name: "Mistral 7B", size: "4.1 GB", desc: "Fast European model — good for chat" },
                      { id: "codellama:13b", name: "Code Llama 13B", size: "7.4 GB", desc: "Meta's code-specialized model" },
                    ].map((model) => (
                      <div key={model.id} className="flex items-center justify-between gap-3 p-3 border rounded-lg">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-medium">{model.name}</p>
                            {model.recommended && <Badge className="text-[9px] bg-blue-600">Recommended</Badge>}
                          </div>
                          <p className="text-xs text-zinc-500 mt-0.5">{model.desc}</p>
                          <p className="text-[10px] text-zinc-400 mt-0.5">{model.size}</p>
                        </div>
                        <Button size="sm" variant="outline" className="shrink-0" onClick={async () => {
                          toast.add({ title: `Pulling ${model.name}...`, type: "info", timeout: 30000 });
                          try {
                            const res = await fetch("http://localhost:11434/api/pull", {
                              method: "POST",
                              headers: { "Content-Type": "application/json" },
                              body: JSON.stringify({ name: model.id, stream: false }),
                            });
                            if (res.ok) toast.add({ title: `${model.name} pulled successfully`, type: "success" });
                            else toast.add({ title: `Failed to pull ${model.name}`, type: "error" });
                          } catch { toast.add({ title: "Ollama not reachable. Is it running?", type: "error" }); }
                        }}>Download</Button>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Model Settings */}
                <div className="border-t pt-4">
                  <p className="text-sm font-medium mb-3">Model Behavior</p>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Default model" hint="Used when Auto routing is off.">
                      <select className="w-full px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800">
                        <option value="auto">Auto (smart routing)</option>
                        <option value="mimo-v2.5-free">MiMo V2.5 Free</option>
                        <option value="gpt-5">GPT-5</option>
                        <option value="claude-4">Claude 4</option>
                        <option value="gemini-2.5">Gemini 2.5</option>
                        <option value="deepseek-v4">DeepSeek V4</option>
                        <option value="qwen3.5:8b">Qwen 3.5 8B (Local)</option>
                      </select>
                    </Field>
                    <Field label="Routing strategy" hint="How Mark picks the best model per task.">
                      <select className="w-full px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800">
                        <option value="balanced">Balanced (quality + cost)</option>
                        <option value="quality">Quality first</option>
                        <option value="speed">Speed first</option>
                        <option value="cost">Lowest cost</option>
                        <option value="local">Prefer local models</option>
                      </select>
                    </Field>
                  </div>
                  <div className="grid grid-cols-2 gap-3 mt-3">
                    <Field label="Temperature" hint="Creativity level (0 = precise, 1 = creative).">
                      <Input type="number" min={0} max={1} step={0.1} defaultValue={0.7} className="w-32" />
                    </Field>
                    <Field label="Max output tokens" hint="Maximum response length.">
                      <Input type="number" min={256} max={128000} step={256} defaultValue={8192} className="w-32" />
                    </Field>
                  </div>
                </div>

                {/* AirLLM - Layer-by-layer 70B inference */}
                <div className="border-t pt-4">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <p className="text-sm font-medium">AirLLM (70B on 4GB GPU)</p>
                      <p className="text-xs text-zinc-500">Run massive LLMs layer-by-layer on a single 4GB GPU without quantization.</p>
                    </div>
                    <Badge variant="outline" className="text-[9px]">Advanced</Badge>
                  </div>
                  <SettingRow title="Enable AirLLM" desc="Layer-by-layer inference for 70B+ models on limited VRAM." control={<Toggle checked={catFlag("advanced", "airllm_enabled")} onChange={(v) => setCat("advanced", "airllm_enabled", v)} />} />
                  <div className="grid grid-cols-1 gap-2 mt-2">
                    {[
                      { id: "meta-llama/Meta-Llama-3.1-70B-Instruct", name: "Llama 3.1 70B Instruct", size: "~140 GB on disk", desc: "Meta's full 70B — runs layer-by-layer on 4GB GPU", recommended: true },
                      { id: "Qwen/Qwen2.5-72B-Instruct", name: "Qwen 2.5 72B Instruct", size: "~144 GB on disk", desc: "Alibaba's top open model — 72B parameters" },
                      { id: "tiiuae/falcon-180B-Chat", name: "Falcon 180B Chat", size: "~360 GB on disk", desc: "Technology Innovation Institute's massive 180B" },
                      { id: "mistralai/Mixtral-8x22B-Instruct-v0.1", name: "Mixtral 8x22B Instruct", size: "~130 GB on disk", desc: "Mistral's MoE — 141B params, 39B active" },
                      { id: "microsoft/Phi-3-medium-4k-instruct", name: "Phi-3 Medium 4K", size: "~32 GB on disk", desc: "Microsoft's 14B — strong reasoning at small size" },
                    ].map((model) => (
                      <div key={model.id} className="flex items-center justify-between gap-3 p-3 border rounded-lg">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-medium">{model.name}</p>
                            {model.recommended && <Badge className="text-[9px] bg-blue-600">Recommended</Badge>}
                          </div>
                          <p className="text-xs text-zinc-500 mt-0.5">{model.desc}</p>
                          <p className="text-[10px] text-zinc-400 mt-0.5">{model.size}</p>
                        </div>
                        <Button size="sm" variant="outline" className="shrink-0" onClick={async () => {
                          toast.add({ title: `Loading ${model.name} via AirLLM...`, type: "info", timeout: 60000 });
                          try {
                            const res = await api.post("/integrations/airllm/load", { model_id: model.id });
                            if ((res as any)?.success) toast.add({ title: `${model.name} loaded`, type: "success" });
                            else toast.add({ title: `Failed: ${(res as any)?.error || "Unknown error"}`, type: "error" });
                          } catch { toast.add({ title: "AirLLM not available. Install: pip install airllm", type: "error" }); }
                        }}>Load</Button>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Scrapling - Adaptive Web Scraping */}
                <div className="border-t pt-4">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <p className="text-sm font-medium">Scrapling (Smart Scraping)</p>
                      <p className="text-xs text-zinc-500">Adaptive web scraping with anti-bot bypass, auto-selectors, and pagination by Karim Shoair.</p>
                    </div>
                    <Badge variant="outline" className="text-[9px]">New</Badge>
                  </div>
                  <SettingRow title="Enable Scrapling" desc="Smart scraping engine with anti-bot bypass and adaptive parsing." control={<Toggle checked={catFlag("advanced", "scrapling_enabled")} onChange={(v) => setCat("advanced", "scrapling_enabled", v)} />} />
                  <div className="grid grid-cols-2 gap-2 mt-2">
                    {[
                      { name: "StealthyFetcher", desc: "Anti-bot bypass (Cloudflare, Turnstile)", icon: "🛡️" },
                      { name: "PlayWrightFetcher", desc: "Full browser automation", icon: "🌐" },
                      { name: "CrawlerFetcher", desc: "Crawlee backend with concurrency", icon: "🕷️" },
                      { name: "AutoPaginator", desc: "Automatic page traversal", icon: "📄" },
                    ].map((f) => (
                      <div key={f.name} className="p-3 border rounded-lg">
                        <div className="flex items-center gap-2">
                          <span>{f.icon}</span>
                          <p className="text-sm font-medium">{f.name}</p>
                        </div>
                        <p className="text-xs text-zinc-500 mt-1">{f.desc}</p>
                      </div>
                    ))}
                  </div>
                  <SettingRow title="Default fetcher" desc="Which backend to use for scraping tasks." control={
                    <select className="px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800">
                      <option value="stealth">StealthyFetcher (anti-bot)</option>
                      <option value="playwright">PlayWrightFetcher (browser)</option>
                      <option value="crawler">CrawlerFetcher (concurrent)</option>
                    </select>
                  } />
                </div>

                <Button onClick={() => window.location.href = "/ai"}><ExternalLink className="mr-2 h-4 w-4" /> Open AI Studio</Button>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="memory">
            <Card><CardHeader><CardTitle className="text-base flex items-center gap-2"><Brain className="h-4 w-4" /> Memory</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-zinc-500">Mark remembers context across conversations and tasks — facts, preferences, and past work.</p>
                <SettingRow title="Enable memory" desc="Let Mark-Imti personalize your experience based on your chats, files, and connected apps." control={<Toggle checked={prefs.enableMemory !== false} onChange={(v) => updatePrefs("enableMemory", v)} />} />
                <SettingRow title="Manage" desc="Mark-Imti may use Memory to personalize queries to search providers, such as Bing, especially on the web." control={<Toggle checked={prefs.memorySearch !== false} onChange={(v) => updatePrefs("memorySearch", v)} />} />
                <div className="p-3 border rounded-lg">
                  <p className="text-sm font-medium">Memory summary</p>
                  <p className="text-xs text-zinc-500 mt-0.5">View an overview of what Mark-Imti has learned about you. Use custom instructions for information you'd like it to always keep in mind. You can still manage your old saved memories.</p>
                  <Button size="sm" className="mt-2" onClick={() => window.location.href = "/memory"}><ExternalLink className="mr-1.5 h-3.5 w-3.5" /> Manage memories</Button>
                </div>
                <SettingRow title="Memory engine" desc="The vectorized memory engine that powers recall across chats and tasks." control={<Toggle checked={catFlag("advanced", "memory_engine")} onChange={(v) => setCat("advanced", "memory_engine", v)} />} />
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 border rounded-lg"><p className="text-sm font-medium">Persistence</p><Badge variant="outline" className="mt-1">SQLite local</Badge></div>
                  <div className="p-3 border rounded-lg"><p className="text-sm font-medium">Blueprints</p><Badge variant="outline" className="mt-1">{catFlag("advanced", "blueprints_enabled") ? "Enabled" : "Disabled"}</Badge></div>
                </div>
                <Button onClick={() => window.location.href = "/memory"}><ExternalLink className="mr-2 h-4 w-4" /> Open Memory</Button>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="agents">
            <Card><CardHeader><CardTitle className="text-base flex items-center gap-2"><Bot className="h-4 w-4" /> Agents</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-zinc-500">A supervisor agent coordinates specialist agents for complex tasks.</p>
                <SettingRow title="Mark companion" desc="The original Mark companion agent." control={<Toggle checked={prefs.markCompanion !== false} onChange={(v) => updatePrefs("markCompanion", v)} />} />
                <SettingRow title="Multi-agent orchestration" desc="Delegate branches of a plan to specialist agents automatically." control={<Toggle checked={catFlag("agents", "multi_agent")} onChange={(v) => setCat("agents", "multi_agent", v)} />} />
                <SettingRow title="Specialist agents" desc="Enable domain specialists (researcher, coder, analyst, designer…)." control={<Toggle checked={catFlag("agents", "specialist_agents")} onChange={(v) => setCat("agents", "specialist_agents", v)} />} />
                <SettingRow title="Auto-upgrade agents" desc="Automatically update agent blueprints as Mark improves." control={<Toggle checked={catFlag("agents", "auto_upgrade")} onChange={(v) => setCat("agents", "auto_upgrade", v)} />} />
                <SettingRow title="Self-evolution" desc="Agents learn from outcomes and refine their own workflows." control={<Toggle checked={catFlag("advanced", "self_evolution", false)} onChange={(v) => setCat("advanced", "self_evolution", v)} />} />
                <Button onClick={() => window.location.href = "/agents"}><ExternalLink className="mr-2 h-4 w-4" /> Open Agents</Button>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="admin">
            <Card><CardHeader><CardTitle className="text-base flex items-center gap-2"><ShieldCheck className="h-4 w-4" /> Admin</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-zinc-500">System administration, user management, and platform controls.</p>
                <SettingRow title="Role-Based Access" desc="ADMIN / USER roles control what each account can do." control={<Toggle checked={catFlag("security", "rbac")} onChange={(v) => setCat("security", "rbac", v)} />} />
                <SettingRow title="Rate limiting" desc="API and auth protection against brute force." control={<Toggle checked={catFlag("security", "rate_limiting")} onChange={(v) => setCat("security", "rate_limiting", v)} />} />
                <Button onClick={() => window.location.href = "/admin"}><ExternalLink className="mr-2 h-4 w-4" /> Open Admin</Button>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="about">
            <Card><CardHeader><CardTitle className="text-base">Mark-Imti</CardTitle></CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p><span className="font-medium">Version:</span> 0.1.0</p>
                <p><span className="font-medium">Type:</span> Autonomous AI Operating Platform</p>
                <p><span className="font-medium">16 Phases</span> • 21 Engines • 34 DB Tables</p>
                <p className="text-zinc-500 text-xs mt-2">Everything runs locally. No data leaves your machine unless you configure a cloud provider.</p>
              </CardContent>
            </Card>
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
