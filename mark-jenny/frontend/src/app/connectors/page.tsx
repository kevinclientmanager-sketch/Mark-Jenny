"use client";
import { useState, useEffect, useCallback } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ProtectedLayout } from "@/components/layout/protected-layout";
import { projectWorkspaceApi, Connector, ConnectorCredential } from "@/lib/api/projectWorkspace";
import { projectsApi } from "@/lib/api/projects";
import { api } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Plug, Plus, Loader2, Globe, Key, Terminal, Check, X, RefreshCw, Unlink, Shield, Zap } from "lucide-react";
import { toast } from "@/components/ui/toast";

export default function ConnectorsPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [tab, setTab] = useState<"browse"|"my"|"custom"|"mcp">("browse");
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [myConns, setMyConns] = useState<ConnectorCredential[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showConnect, setShowConnect] = useState<Connector | null>(null);
  const [connectProject, setConnectProject] = useState("");
  const [connectAuth, setConnectAuth] = useState("API_KEY");
  const [connectCreds, setConnectCreds] = useState("");
  const [connecting, setConnecting] = useState(false);

  // MCP registry + built-in tools
  const [registry, setRegistry] = useState<any[]>([]);
  const [registryLoading, setRegistryLoading] = useState(false);
  const [tools, setTools] = useState<any[]>([]);
  const [toolsLoading, setToolsLoading] = useState(false);
  const [registryTarget, setRegistryTarget] = useState<any | null>(null);
  const [registryEnv, setRegistryEnv] = useState<Record<string, string>>({});
  const [registryBusy, setRegistryBusy] = useState(false);

  const loadRegistry = useCallback(async () => {
    setRegistryLoading(true);
    try {
      const r = await api.get<any>("/features/mcp/registry");
      setRegistry(r?.servers || []);
    } catch { setRegistry([]); } finally { setRegistryLoading(false); }
  }, []);

  const loadTools = useCallback(async () => {
    setToolsLoading(true);
    try {
      const r = await api.get<any>("/features/mcp/tools");
      setTools(r?.tools || []);
    } catch { setTools([]); } finally { setToolsLoading(false); }
  }, []);

  useEffect(() => { loadRegistry(); }, [loadRegistry]);

  const openRegistry = (r: any) => {
    setRegistryTarget(r);
    const seeded: Record<string, string> = {};
    for (const k of [...(r.required_env || []), ...(r.optional_env || [])]) seeded[k] = "";
    setRegistryEnv(seeded);
  };

  const startRegistry = async (id: string) => {
    try {
      const r = await api.post<any>(`/features/mcp/servers/${id}/start`, {});
      const n = r?.tools?.length ?? r?.result?.tools?.length ?? 0;
      toast.add({
        title: r?.success ? `${id} started` : `${id} failed to start`,
        description: r?.success ? `${n} tool(s) advertised.` : (r?.error || "unknown error"),
        type: r?.success ? "success" : "error",
      });
      loadRegistry();
    } catch (e: any) {
      toast.add({ title: "Start failed", description: e?.message || "", type: "error" });
    }
  };

  const connectRegistry = async () => {
    if (!registryTarget) return;
    const missing = (registryTarget.required_env || []).filter((k: string) => !registryEnv[k]);
    if (missing.length) {
      toast.add({ title: `Enter ${missing.join(", ")}`, type: "error" });
      return;
    }
    setRegistryBusy(true);
    try {
      const r = await api.post<any>(`/features/mcp/registry/${registryTarget.id}/connect`, {
        env: registryEnv, auto_start: true,
      });
      const ok = r?.start?.success;
      const toolsFound = r?.start?.tools?.length ?? 0;
      toast.add({
        title: ok ? `${registryTarget.label} connected` : `${registryTarget.label} added but not started`,
        description: ok
          ? `${toolsFound} tool(s) available.`
          : (r?.start?.error || "The server did not start."),
        type: ok ? "success" : "error",
      });
      setRegistryTarget(null);
      loadRegistry();
    } catch (e: any) {
      toast.add({ title: "Connect failed", description: e?.message || "", type: "error" });
    } finally { setRegistryBusy(false); }
  };

  // Custom API builder
  const [customName, setCustomName] = useState("");
  const [customBase, setCustomBase] = useState("");
  const [customAuth, setCustomAuth] = useState("API_KEY");
  const [customKey, setCustomKey] = useState("");
  const [customHeaders, setCustomHeaders] = useState("{}");
  const [customProject, setCustomProject] = useState("");

  // MCP builder
  const [mcpName, setMcpName] = useState("");
  const [mcpCmd, setMcpCmd] = useState("npx");
  const [mcpArgs, setMcpArgs] = useState("");
  const [mcpEnv, setMcpEnv] = useState("{}");
  const [mcpProject, setMcpProject] = useState("");

  const fetchAll = useCallback(async()=>{
    setLoading(true);
    try {
      const [cs, my, p] = await Promise.all([
        projectWorkspaceApi.listConnectors(),
        projectWorkspaceApi.listUserConnectors(),
        projectsApi.list({page_size:100})
      ]);
      setConnectors(cs);
      setMyConns(my);
      setProjects(p.projects);
    } finally { setLoading(false); }
  },[]);

  useEffect(()=>{ fetchAll(); },[fetchAll]);

  const getStatus = (cid:number)=> myConns.find(c=>c.connector_id===cid)?.status || "NOT_CONNECTED";
const handleConnect = async ()=>{
    if (!showConnect) return;
    setConnecting(true);
    try {
      let creds: any = {};
      if (!connectCreds.trim()) { toast.add({ title: "Credentials required", description: "Enter API key, token, or JSON credentials to connect.", type: "error" }); setConnecting(false); return; }
      try { creds = JSON.parse(connectCreds); } catch { creds = { api_key: connectCreds.trim() }; }
      await projectWorkspaceApi.connectConnector({ connector_id: showConnect.id, project_id: connectProject?Number(connectProject):undefined, auth_type: connectAuth as any, credentials: creds });
      setShowConnect(null); setConnectCreds(""); fetchAll();
      toast.add({ title: "Connected", description: showConnect.display_name, type: "success" });
    } catch(e:any){ toast.add({ title: "Connect failed", description: e?.message || "Try again.", type: "error" }); } finally{ setConnecting(false); }
  };
  const handleRefresh = async (id:number)=>{ try { await projectWorkspaceApi.refreshConnector(id); fetchAll(); toast.add({ title: "Connector refreshed", type: "success" }); } catch(e:any){ toast.add({ title: "Refresh failed", description: e?.message || "Try again.", type: "error" }); } };
  const handleDisconnect = async (id:number)=>{ try { await projectWorkspaceApi.disconnectConnector(id); fetchAll(); toast.add({ title: "Connector disconnected", type: "success" }); } catch(e:any){ toast.add({ title: "Disconnect failed", description: e?.message || "Try again.", type: "error" }); } };

  const handleCustomCreate = async()=>{
    if(!customName || !customBase) { toast.add({ title: "Name and Base URL required", type: "error" }); return; }
    try {
      let headers = {}; try{ headers = JSON.parse(customHeaders); }catch{ headers={}; }
      await projectWorkspaceApi.createCustomAPIConnector({ name: customName, base_url: customBase, auth_type: customAuth as any, api_key: customAuth==="API_KEY"?customKey:undefined, bearer_token: customAuth==="BEARER_TOKEN"?customKey:undefined, headers, project_id: customProject?Number(customProject):undefined });
      setCustomName(""); setCustomBase(""); setCustomKey("");
      toast.add({ title: "Custom API connector created", type: "success" });
      fetchAll();
    } catch(e:any){ toast.add({ title: "Create failed", description: e?.message || "Try again.", type: "error" }); }
  };
  const handleMcpCreate = async()=>{
    if(!mcpName || !mcpCmd) { toast.add({ title: "Name and Command required", type: "error" }); return; }
    try {
      let env = {}; try{ env = JSON.parse(mcpEnv); }catch{ env={}; }
      const args = mcpArgs.split(" ").filter(Boolean);
      await projectWorkspaceApi.createMCPConfig({ name: mcpName, command: mcpCmd, args, env, project_id: mcpProject?Number(mcpProject):undefined });
      setMcpName(""); setMcpCmd("npx"); setMcpArgs("");
      toast.add({ title: "MCP config created", description: "Desktop will handle local process", type: "success" });
      fetchAll();
    } catch(e:any){ toast.add({ title: "Create failed", description: e?.message || "Try again.", type: "error" }); }
  };

  const filtered = connectors.filter(c=> !search || c.name.includes(search.toLowerCase()) || c.display_name.toLowerCase().includes(search.toLowerCase()) || c.type.toLowerCase().includes(search.toLowerCase()));

  return (
    <ProtectedLayout>
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex">
        <Sidebar isOpen={sidebarOpen} onToggle={()=>setSidebarOpen(!sidebarOpen)} />
        <div className={`flex-1 flex flex-col min-w-0 transition-all ${sidebarOpen?"ml-64":"ml-16"}`}>
          <Header />
          <main className="flex-1 p-6 overflow-auto">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h1 className="text-2xl font-semibold flex items-center gap-2"><Plug className="h-6 w-6"/> Connectors & Integrations</h1>
                <p className="text-sm text-zinc-500">Framework: authenticate() · connect() · disconnect() · refresh() · getStatus() · execute() · validatePermissions() — 14 initial + extensible Custom API/MCP. Secrets never in logs, encrypted.</p>
              </div>
              <Badge variant="outline" className="hidden md:flex"><Shield className="mr-1 h-3 w-3"/> OAuth + API-key · Encrypted</Badge>
            </div>

            <Tabs value={tab} onValueChange={(v)=>setTab(v as any)} className="flex-1 flex flex-col">
              <TabsList className="grid w-full grid-cols-4 mb-4 max-w-xl">
                <TabsTrigger value="browse"><Globe className="mr-1 h-3 w-3"/>Browse ({connectors.length})</TabsTrigger>
                <TabsTrigger value="my">My ({myConns.length})</TabsTrigger>
                <TabsTrigger value="custom"><Key className="mr-1 h-3 w-3"/>Custom API</TabsTrigger>
                <TabsTrigger value="mcp"><Terminal className="mr-1 h-3 w-3"/>MCP</TabsTrigger>
              </TabsList>

              <div className="mb-3 flex gap-2">
                <div className="flex-1 max-w-md relative">
                  <Input placeholder="Search connectors..." value={search} onChange={e=>setSearch(e.target.value)} className="pl-3" />
                </div>
              </div>

              <TabsContent value="browse" className="flex-1 overflow-auto">
                {loading ? <div className="flex justify-center p-8"><Loader2 className="h-6 w-6 animate-spin"/></div> :
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filtered.map(c=>{
                      const status = getStatus(c.id);
                      const isConnected = status==="CONNECTED";
                      return (
                        <Card key={c.id} className="hover:shadow-md transition-shadow">
                          <CardHeader className="pb-2">
                            <div className="flex items-center gap-3">
                              <div className="h-10 w-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-xl">{c.icon || "🔌"}</div>
                              <div className="flex-1 min-w-0">
                                <CardTitle className="text-base truncate">{c.display_name}</CardTitle>
                                <p className="text-xs text-zinc-500">{c.type}</p>
                              </div>
                              <Badge variant={isConnected?"default":status==="CONNECTING"?"secondary":"outline"} className={isConnected?"bg-green-100 text-green-700":""}>{status}</Badge>
                            </div>
                          </CardHeader>
                          <CardContent>
                            <p className="text-sm text-zinc-500 mb-3 line-clamp-2">{c.description}</p>
                            <div className="flex gap-2">
                              {isConnected ? (
                                <>
                                  <Button variant="outline" size="sm" className="flex-1" onClick={()=>{ const cred=myConns.find(x=>x.connector_id===c.id); if(cred) handleRefresh(cred.id); }}><RefreshCw className="mr-1 h-3 w-3"/>Refresh</Button>
                                  <Button variant="ghost" size="sm" className="flex-1" onClick={()=>{ const cred=myConns.find(x=>x.connector_id===c.id); if(cred) handleDisconnect(cred.id); }}><X className="mr-1 h-3 w-3"/>Disconnect</Button>
                                </>
                              ) : (
                                <Button size="sm" className="w-full bg-blue-600 hover:bg-blue-700" onClick={()=>setShowConnect(c)}><Plus className="mr-1 h-3 w-3"/>Connect</Button>
                              )}
                            </div>
                          </CardContent>
                        </Card>
                      );
                    })}
                  </div>
                }
                <Card className="mt-6 p-4 bg-amber-50 dark:bg-amber-900/20 border-amber-200">
                  <p className="text-sm"><strong>Extensible framework:</strong> Add any new connector via <em>Custom API</em> (Name/Base URL/Auth/Headers/Endpoints) or <em>MCP</em> (command/args/env) without code changes. Connector interface is uniform across 14 initial + infinite custom.</p>
                </Card>
              </TabsContent>

              <TabsContent value="my" className="flex-1 overflow-auto">
                {myConns.length===0 ? <Card className="p-8 text-center text-zinc-500">No connections yet. Browse and Connect.</Card> :
                  <div className="space-y-3">
                    {myConns.map(cred=>{
                      const con = connectors.find(x=>x.id===cred.connector_id);
                      return (
                        <Card key={cred.id}>
                          <CardContent className="p-4">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <div className="h-10 w-10 rounded-lg bg-green-100 flex items-center justify-center">{con?.icon || "🔌"}</div>
                                <div>
                                  <p className="font-medium">{con?.display_name || cred.connector_name} <Badge variant="outline" className="ml-1">{cred.connector_type}</Badge></p>
                                  <p className="text-xs text-zinc-500">{cred.auth_type} • {cred.project_id?`Project #${cred.project_id}`:"Global"} • Last sync {cred.last_sync_at ? new Date(cred.last_sync_at).toLocaleString() : "never"}</p>
                                </div>
                              </div>
                              <div className="flex items-center gap-2">
                                <Badge className={cred.status==="CONNECTED"?"bg-green-100 text-green-700":""}>{cred.status}</Badge>
                                <Button variant="outline" size="sm" onClick={()=>handleRefresh(cred.id)}><RefreshCw className="h-3 w-3"/></Button>
                                <Button variant="ghost" size="sm" onClick={()=>handleDisconnect(cred.id)}><Unlink className="h-3 w-3"/></Button>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      );
                    })}
                  </div>
                }
              </TabsContent>

              <TabsContent value="custom" className="flex-1 overflow-auto">
                <Card className="p-6">
                  <h3 className="font-semibold mb-2 flex items-center gap-2"><Key className="h-4 w-4"/> Custom API Connector Builder</h3>
                  <p className="text-sm text-zinc-500 mb-4">Define any REST API: Name/Base URL/Auth (API key/Bearer/Headers) → encrypted → available as connector. Never exposed in logs.</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div><label className="text-sm font-medium">Name *</label><Input value={customName} onChange={e=>setCustomName(e.target.value)} placeholder="My CRM API" /></div>
                    <div><label className="text-sm font-medium">Base URL *</label><Input value={customBase} onChange={e=>setCustomBase(e.target.value)} placeholder="https://api.example.com" /></div>
                    <div><label className="text-sm font-medium">Auth Type</label><select value={customAuth} onChange={e=>setCustomAuth(e.target.value)} className="w-full mt-1 px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800"><option value="API_KEY">API Key</option><option value="BEARER_TOKEN">Bearer</option><option value="NONE">None</option></select></div>
                    <div><label className="text-sm font-medium">Key/Token</label><Input value={customKey} onChange={e=>setCustomKey(e.target.value)} placeholder="sk-... (encrypted)" type="password" /></div>
                    <div><label className="text-sm font-medium">Project (optional)</label><select value={customProject} onChange={e=>setCustomProject(e.target.value)} className="w-full mt-1 px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800"><option value="">Global</option>{projects.map(p=> <option key={p.id} value={p.id}>{p.name}</option>)}</select></div>
                    <div><label className="text-sm font-medium">Headers JSON</label><Input value={customHeaders} onChange={e=>setCustomHeaders(e.target.value)} placeholder='{"X-Custom":"1"}' /></div>
                  </div>
                  <Button className="mt-4 bg-blue-600 hover:bg-blue-700" onClick={handleCustomCreate}><Plus className="mr-2 h-4 w-4"/>Create Custom API Connector</Button>
                </Card>
              </TabsContent>

              <TabsContent value="mcp" className="flex-1 overflow-auto">
                <Card className="p-6 mb-4">
                  <h3 className="font-semibold mb-1 flex items-center gap-2"><Zap className="h-4 w-4"/> Featured MCP Servers</h3>
                  <p className="text-sm text-zinc-500 mb-3">One-click install with the correct launch configuration already filled in.</p>
                  {registryLoading ? <div className="flex justify-center p-6"><Loader2 className="h-5 w-5 animate-spin"/></div> : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {registry.map(r => (
                        <Card key={r.id} className="p-3">
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <p className="font-medium text-sm">{r.label}</p>
                              <p className="text-[11px] text-zinc-500">{r.category}</p>
                            </div>
                            <div className="flex gap-1 shrink-0">
                              {r.connected && <Badge className="bg-green-600 text-[10px]">Connected</Badge>}
                              {!r.runtime_available && <Badge variant="outline" className="text-[10px]">No runtime</Badge>}
                            </div>
                          </div>
                          <p className="text-xs text-zinc-500 mt-1.5">{r.description}</p>
                          <p className="text-[10px] text-zinc-400 mt-1 break-all">{r.command} {r.args.join(" ")}</p>
                          {!r.runtime_available && (
                            <p className="text-[10px] text-amber-600 mt-1">
                              `{r.command}` is not installed on this host. {r.note || "Install it on the server/desktop that runs Mark-Imti."}
                            </p>
                          )}
                          <div className="flex gap-2 mt-2">
                            {!r.connected ? (
                              <Button size="sm" onClick={() => openRegistry(r)}>
                                <Plug className="mr-1 h-3 w-3"/>Connect
                              </Button>
                            ) : (
                              <Button size="sm" variant="outline" onClick={() => startRegistry(r.id)}>
                                <RefreshCw className="mr-1 h-3 w-3"/>Start
                              </Button>
                            )}
                            {r.docs_url && (
                              <a href={r.docs_url} target="_blank" rel="noopener noreferrer">
                                <Button size="sm" variant="ghost">Docs</Button>
                              </a>
                            )}
                          </div>
                        </Card>
                      ))}
                    </div>
                  )}
                </Card>

                <Card className="p-6 mb-4">
                  <h3 className="font-semibold mb-2 flex items-center gap-2"><Terminal className="h-4 w-4"/> Mark-Imti Built-in Tools</h3>
                  <p className="text-sm text-zinc-500 mb-2">Your own skills, memory, knowledge, sandbox, files and model are callable through the same tool interface.</p>
                  <Button size="sm" variant="outline" onClick={loadTools} disabled={toolsLoading}>
                    {toolsLoading ? <Loader2 className="mr-1 h-3 w-3 animate-spin"/> : <Terminal className="mr-1 h-3 w-3"/>}
                    List callable tools ({tools.length})
                  </Button>
                  {tools.length > 0 && (
                    <div className="mt-3 space-y-1.5">
                      {tools.map(t => (
                        <div key={`${t.server}-${t.name}`} className="border rounded-lg p-2">
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-medium">{t.name}</p>
                            <Badge variant="outline" className="text-[10px]">{t.server}</Badge>
                          </div>
                          <p className="text-[11px] text-zinc-500">{t.description}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>

                <Card className="p-6">
                  <h3 className="font-semibold mb-2 flex items-center gap-2"><Terminal className="h-4 w-4"/> Custom MCP Configuration</h3>
                  <p className="text-sm text-zinc-500 mb-1">Desktop: runs local MCP process. Web: shows <em>Local MCP requires desktop</em> if unsupported - never pretends.</p>
                  <Badge variant="outline" className="mb-3">{typeof window !== "undefined" && (window as any).electron ? "Desktop: MCP supported" : "Web: MCP limited - use desktop for local processes"}</Badge>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div><label className="text-sm font-medium">Name *</label><Input value={mcpName} onChange={e=>setMcpName(e.target.value)} placeholder="my-mcp-server" /></div>
                    <div><label className="text-sm font-medium">Command *</label><Input value={mcpCmd} onChange={e=>setMcpCmd(e.target.value)} placeholder="npx" /></div>
                    <div><label className="text-sm font-medium">Args (space separated)</label><Input value={mcpArgs} onChange={e=>setMcpArgs(e.target.value)} placeholder="-y @modelcontextprotocol/server-filesystem /tmp" /></div>
                    <div><label className="text-sm font-medium">Project</label><select value={mcpProject} onChange={e=>setMcpProject(e.target.value)} className="w-full mt-1 px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800"><option value="">Global</option>{projects.map(p=> <option key={p.id} value={p.id}>{p.name}</option>)}</select></div>
                    <div className="md:col-span-2"><label className="text-sm font-medium">Env JSON</label><Input value={mcpEnv} onChange={e=>setMcpEnv(e.target.value)} placeholder='{"API_KEY":"..."}' /></div>
                  </div>
                  <Button className="mt-4" onClick={handleMcpCreate}><Plus className="mr-2 h-4 w-4"/>Create MCP Config</Button>
                </Card>
              </TabsContent>
            </Tabs>

            {registryTarget && (
              <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50" onClick={()=>setRegistryTarget(null)}>
                <Card className="w-full max-w-md" onClick={e=>e.stopPropagation()}>
                  <CardContent className="p-6 space-y-3">
                    <h3 className="font-semibold">Connect {registryTarget.label}</h3>
                    <p className="text-sm text-zinc-500">{registryTarget.description}</p>
                    {Object.keys(registryEnv).map(k => (
                      <div key={k}>
                        <label className="text-sm font-medium">
                          {k} {(registryTarget.required_env || []).includes(k) ? "*" : "(optional)"}
                        </label>
                        <Input
                          type="password"
                          value={registryEnv[k]}
                          onChange={e => setRegistryEnv(prev => ({ ...prev, [k]: e.target.value }))}
                          placeholder={k}
                        />
                      </div>
                    ))}
                    {Object.keys(registryEnv).length === 0 && (
                      <p className="text-xs text-zinc-500">This server needs no secrets.</p>
                    )}
                    <div className="flex gap-2 justify-end">
                      <Button variant="outline" onClick={()=>setRegistryTarget(null)}>Cancel</Button>
                      <Button onClick={connectRegistry} disabled={registryBusy} className="bg-blue-600 hover:bg-blue-700">
                        {registryBusy ? <><Loader2 className="mr-2 h-4 w-4 animate-spin"/>Starting</> : <><Check className="mr-2 h-4 w-4"/>Connect &amp; start</>}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {showConnect && (
              <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50" onClick={()=>setShowConnect(null)}>
                <Card className="w-full max-w-md" onClick={e=>e.stopPropagation()}>
                  <CardContent className="p-6 space-y-3">
                    <h3 className="font-semibold">Connect {showConnect.display_name}</h3>
                    <p className="text-sm text-zinc-500">{showConnect.description}</p>
                    <div><label className="text-sm font-medium">Project (optional)</label><select value={connectProject} onChange={e=>setConnectProject(e.target.value)} className="w-full mt-1 px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800"><option value="">Global</option>{projects.map(p=> <option key={p.id} value={p.id}>{p.name}</option>)}</select></div>
                    <div><label className="text-sm font-medium">Auth Type</label><select value={connectAuth} onChange={e=>setConnectAuth(e.target.value)} className="w-full mt-1 px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800"><option value="API_KEY">API Key</option><option value="OAUTH2">OAuth2</option><option value="BEARER_TOKEN">Bearer</option></select></div>
                    <div><label className="text-sm font-medium">Credentials JSON (encrypted)</label><Input value={connectCreds} onChange={e=>setConnectCreds(e.target.value)} placeholder='{"api_key":"..."}' /></div>
                    <div className="flex gap-2 justify-end">
                      <Button variant="outline" onClick={()=>setShowConnect(null)}>Cancel</Button>
                      <Button onClick={handleConnect} disabled={connecting} className="bg-blue-600 hover:bg-blue-700">{connecting?<><Loader2 className="mr-2 h-4 w-4 animate-spin"/>Connecting</>:<><Check className="mr-2 h-4 w-4"/>Connect</>}</Button>
                    </div>
                    <p className="text-xs text-zinc-400">Framework: authenticate()→connect()→getStatus()→execute()→refresh() - encrypted, never logged.</p>
                  </CardContent>
                </Card>
              </div>
            )}
          </main>
        </div>
      </div>
    </ProtectedLayout>
  );
}



