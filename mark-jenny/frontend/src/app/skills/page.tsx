"use client";
import { useState, useEffect, useCallback } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ProtectedLayout } from "@/components/layout/protected-layout";
import { skillsApi, Skill } from "@/lib/api/skills";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Search, Plus, Upload, GitBranch, Wand2, Loader2, Check, X, Trash2, RotateCcw, Settings, Download, Globe } from "lucide-react";
import { toast } from "@/components/ui/toast";
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter, SheetClose,
} from "@/components/ui/sheet";

export default function SkillsPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [tab, setTab] = useState<"installed"|"official"|"builder"|"discover">("installed");
  const [installed, setInstalled] = useState<Skill[]>([]);
  const [official, setOfficial] = useState<Skill[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [builderPrompt, setBuilderPrompt] = useState("Create a skill that researches property maintenance companies and generates an Excel comparison.");
  const [building, setBuilding] = useState(false);
  const [githubUrl, setGithubUrl] = useState("");
  const [uploading, setUploading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [confirmTarget, setConfirmTarget] = useState<{ skill: Skill; action: "remove" | "rollback" } | null>(null);
  const [confirming, setConfirming] = useState(false);

  // Discover state
  const [discoverQuery, setDiscoverQuery] = useState("");
  const [discoverUrl, setDiscoverUrl] = useState("");
  const [discoveredSkills, setDiscoveredSkills] = useState<any[]>([]);
  const [discoveredRepos, setDiscoveredRepos] = useState<any[]>([]);
  const [discovering, setDiscovering] = useState(false);
  const [discoverMessage, setDiscoverMessage] = useState("");
  const [installingSkills, setInstallingSkills] = useState<Set<string>>(new Set());

  const fetchInstalled = useCallback(async()=>{
    setLoading(true);
    try {
      const res = await skillsApi.list({ search: search||undefined, page:1, page_size:50 });
      setInstalled(res.skills);
    } finally{ setLoading(false); }
  },[search]);
  const fetchOfficial = useCallback(async()=>{
    try { const res = await skillsApi.official(); setOfficial(res); } catch{}
  },[]);

  useEffect(()=>{ fetchInstalled(); },[fetchInstalled]);
  useEffect(()=>{ if(tab==="official") fetchOfficial(); },[tab, fetchOfficial]);

  const handleEnable = async (s:Skill)=>{ try { await (s.status==="ENABLED" ? skillsApi.disable(s.id) : skillsApi.enable(s.id)); fetchInstalled(); toast.add({ title: s.status==="ENABLED" ? "Skill disabled" : "Skill enabled", description: s.display_name || s.name, type: "success" }); } catch(e:any){ toast.add({ title: "Update failed", description: e?.message || "Try again.", type: "error" }); } };
  const confirmAction = async ()=>{
    if (!confirmTarget) return;
    setConfirming(true);
    try {
      if (confirmTarget.action === "remove") await skillsApi.remove(confirmTarget.skill.id);
      else await skillsApi.rollback(confirmTarget.skill.id);
      fetchInstalled();
      toast.add({ title: confirmTarget.action === "remove" ? "Skill removed" : "Skill rolled back", description: confirmTarget.skill.display_name || confirmTarget.skill.name, type: "success" });
    } catch(e:any){ toast.add({ title: confirmTarget.action === "remove" ? "Couldn't remove skill" : "Rollback failed", description: e?.message || "Try again.", type: "error" }); } finally {
      setConfirming(false);
      setConfirmTarget(null);
    }
  };
  const handleInstallOfficial = async (name:string)=>{ try { await skillsApi.installOfficial(name); fetchInstalled(); toast.add({ title: "Installed", description: name, type: "success" }); } catch(e:any){ toast.add({ title: "Install failed", description: e?.message || "Try again.", type: "error" }); } };
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>)=>{
    const f = e.target.files?.[0]; if(!f) return;
    setUploading(true);
    try { await skillsApi.upload(f); fetchInstalled(); toast.add({ title: "Uploaded", description: f.name, type: "success" }); } catch(err:any){ toast.add({ title: "Upload failed", description: err?.message || "Try again.", type: "error" }); } finally{ setUploading(false); e.target.value=""; }
  };
  const handleGithub = async()=>{
    if(!githubUrl.trim()) { toast.add({ title: "Enter GitHub raw URL", type: "error" }); return; }
    try { await skillsApi.importGithub(githubUrl); fetchInstalled(); setGithubUrl(""); toast.add({ title: "Skill imported", type: "success" }); } catch(err:any){ toast.add({ title: "Import failed", description: err?.message || "Try again.", type: "error" }); }
  };
  const handleBuild = async()=>{
    if(!builderPrompt.trim()) { toast.add({ title: "Enter a prompt", type: "error" }); return; }
    setBuilding(true);
    try {
      // Validate before install is built-in to /build (validates package)
      const skill = await skillsApi.build(builderPrompt);
      toast.add({ title: "Skill built", description: `${skill.name} v${skill.version} - validated and installed`, type: "success" });
      fetchInstalled();
      setTab("installed");
    } catch(err:any){ toast.add({ title: "Build failed", description: err?.message || "Try again.", type: "error" }); } finally{ setBuilding(false); }
  };
  const handleValidate = async()=>{
    if(!builderPrompt.trim()) return;
    setValidating(true);
    try {
      // create a draft package for validation without install
      const draft = { name: "draft-test", version:"1.0.0", manifest:{name:"draft-test"}, tools:["web_search"], permissions:[] };
      const res = await skillsApi.validate(draft);
      toast.add(res.valid ? { title: "Valid package", type: "success" } : { title: "Invalid package", description: res.errors.join(", "), type: "error" });
    } finally{ setValidating(false); }
  };

  // Self-Builder: Discover skills from GitHub
  const handleDiscover = async (mode: "search" | "url" | "all") => {
    setDiscovering(true);
    setDiscoverMessage("");
    setDiscoveredSkills([]);
    setDiscoveredRepos([]);
    try {
      const params: any = {};
      if (mode === "search" && discoverQuery.trim()) params.query = discoverQuery;
      else if (mode === "url" && discoverUrl.trim()) params.url = discoverUrl;
      const res = await skillsApi.discover(params);
      setDiscoveredSkills(res.skills || []);
      setDiscoveredRepos(res.repos || []);
      setDiscoverMessage(res.message);
      toast.add({ title: "Discovery complete", description: res.message, type: "success" });
    } catch(e:any) {
      toast.add({ title: "Discovery failed", description: e?.message || "Try again.", type: "error" });
    } finally { setDiscovering(false); }
  };

  const handleInstallDiscovered = async (skillName: string) => {
    setInstallingSkills(prev => new Set(prev).add(skillName));
    try {
      await skillsApi.autoInstall([skillName]);
      toast.add({ title: "Installed", description: skillName, type: "success" });
      fetchInstalled();
      setDiscoveredSkills(prev => prev.filter(s => s.name !== skillName));
    } catch(e:any) {
      toast.add({ title: "Install failed", description: e?.message || "Try again.", type: "error" });
    } finally {
      setInstallingSkills(prev => { const next = new Set(prev); next.delete(skillName); return next; });
    }
  };

  const handleInstallAllDiscovered = async () => {
    const names = discoveredSkills.map(s => s.name);
    if (names.length === 0) return;
    setDiscovering(true);
    try {
      const res = await skillsApi.autoInstall(names);
      toast.add({ title: "Bulk install complete", description: res.message, type: "success" });
      fetchInstalled();
      setDiscoveredSkills([]);
      setDiscoverMessage(`Installed ${res.installed} skills`);
    } catch(e:any) {
      toast.add({ title: "Bulk install failed", description: e?.message || "Try again.", type: "error" });
    } finally { setDiscovering(false); }
  };

  const handleFillGaps = async () => {
    setDiscovering(true);
    try {
      const res = await skillsApi.fillGaps();
      toast.add({ title: "Gaps filled", description: res.message, type: "success" });
      fetchInstalled();
      setDiscoverMessage(res.message);
    } catch(e:any) {
      toast.add({ title: "Fill gaps failed", description: e?.message || "Try again.", type: "error" });
    } finally { setDiscovering(false); }
  };

  return (
    <ProtectedLayout>
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex">
        <Sidebar isOpen={sidebarOpen} onToggle={()=>setSidebarOpen(!sidebarOpen)} />
        <div className={`flex-1 flex flex-col min-w-0 transition-all ${sidebarOpen?"ml-64":"ml-16"}`}>
          <Header />
          <main className="flex-1 p-6 overflow-auto">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h1 className="text-2xl font-semibold">Skills Platform</h1>
                <p className="text-sm text-zinc-500">manifest • metadata • instructions • tools • permissions • config • version • dependencies • Validate before install</p>
              </div>
              <div className="flex gap-2">
                <label className="cursor-pointer"><Button variant="outline"><Upload className="mr-2 h-4 w-4"/>Upload</Button><input type="file" accept=".json" className="hidden" onChange={handleUpload} disabled={uploading}/></label>
              </div>
            </div>

            <Tabs value={tab} onValueChange={(v)=>setTab(v as any)} className="flex-1 flex flex-col">
              <TabsList className="grid w-full grid-cols-4 mb-4 max-w-lg">
                <TabsTrigger value="installed">Installed ({installed.length})</TabsTrigger>
                <TabsTrigger value="official">Official</TabsTrigger>
                <TabsTrigger value="discover">Discover</TabsTrigger>
                <TabsTrigger value="builder">Builder</TabsTrigger>
              </TabsList>

              <div className="mb-3 flex gap-2">
                <div className="flex-1 max-w-md relative">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-zinc-400"/>
                  <Input placeholder="Search skills..." value={search} onChange={e=>setSearch(e.target.value)} className="pl-8" />
                </div>
              </div>

              <TabsContent value="installed" className="flex-1 overflow-auto">
                {loading ? <div className="flex justify-center p-8"><Loader2 className="h-6 w-6 animate-spin"/></div> :
                  installed.length===0 ? <Card className="p-8 text-center text-zinc-500">No installed skills. Install from Official or Build with Mark.</Card> :
                  <div className="space-y-3">
                    {installed.map(s=>(
                      <Card key={s.id}>
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 flex-wrap">
                                <h3 className="font-medium">{s.display_name || s.name}</h3>
                                <Badge variant="outline" className="text-xs">{s.source}</Badge>
                                <Badge variant={s.status==="ENABLED"?"default":s.status==="DISABLED"?"secondary":s.status==="ERROR"?"destructive":"outline"}>{s.status}</Badge>
                                <span className="text-xs text-zinc-500">v{s.version}</span>
                              </div>
                              <p className="text-sm text-zinc-500 mt-1">{s.description || "No description"}</p>
                              <div className="flex flex-wrap gap-1 mt-2">
                                {s.tools?.map(t=> <Badge key={t} variant="outline" className="text-xs">{t}</Badge>)}
                              </div>
                              <p className="text-xs text-zinc-400 mt-1">Updated {s.updated_at ? new Date(s.updated_at).toLocaleString() : new Date(s.created_at).toLocaleString()} {s.dependencies?.length ? `• deps: ${s.dependencies.join(", ")}` : ""}</p>
                            </div>
                            <div className="flex gap-1">
                              <Button variant="outline" size="sm" onClick={()=>handleEnable(s)}>{s.status==="ENABLED"?<><X className="mr-1 h-3 w-3"/>Disable</>:<><Check className="mr-1 h-3 w-3"/>Enable</>}</Button>
                              <Button variant="ghost" size="sm" onClick={()=>setConfirmTarget({ skill:s, action:"rollback" })}><RotateCcw className="h-3 w-3"/></Button>
                              <Button variant="ghost" size="icon" onClick={()=>setConfirmTarget({ skill:s, action:"remove" })}><Trash2 className="h-4 w-4 text-red-500"/></Button>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                }
                <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Card className="p-4">
                    <h3 className="font-medium flex items-center gap-2"><GitBranch className="h-4 w-4"/> Import from GitHub</h3>
                    <p className="text-xs text-zinc-500 mb-2">Raw JSON URL (transforms github.com/blob to raw)</p>
                    <div className="flex gap-2">
                      <Input placeholder="https://raw.githubusercontent.com/.../skill.json" value={githubUrl} onChange={e=>setGithubUrl(e.target.value)} />
                      <Button onClick={handleGithub} disabled={!githubUrl.trim()}><Download className="mr-2 h-4 w-4"/>Import</Button>
                    </div>
                  </Card>
                  <Card className="p-4">
                    <h3 className="font-medium flex items-center gap-2"><Settings className="h-4 w-4"/> Lifecycle</h3>
                    <p className="text-xs text-zinc-500">Install → Validate → Enable → Disable → Configure → Update → Rollback → Remove. Validate before install is enforced.</p>
                  </Card>
                </div>
              </TabsContent>

              <TabsContent value="official" className="flex-1 overflow-auto">
                <div className="space-y-3">
                  {official.map(s=>(
                    <Card key={s.name}>
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between">
                          <div>
                            <h3 className="font-medium">{s.display_name || s.name} <Badge variant="outline">OFFICIAL</Badge> {s.id===0 ? <Badge variant="secondary">Not Installed</Badge> : <Badge>Installed</Badge>}</h3>
                            <p className="text-sm text-zinc-500">{s.description}</p>
                            <div className="flex gap-1 mt-1">{s.tools?.map(t=> <Badge key={t} variant="outline" className="text-xs">{t}</Badge>)}</div>
                          </div>
                          {s.id===0 ? <Button size="sm" onClick={()=>handleInstallOfficial(s.name)}><Plus className="mr-1 h-3 w-3"/>Install</Button> : <Badge>Installed</Badge>}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </TabsContent>

              <TabsContent value="discover" className="flex-1 overflow-auto">
                <Card className="p-6">
                  <h2 className="text-lg font-semibold flex items-center gap-2">
                    <Globe className="h-5 w-5"/> Self-Builder — Discover Skills from GitHub
                  </h2>
                  <p className="text-sm text-zinc-500 mb-4">
                    Mark can browse GitHub, find SKILL.md files in repos, parse them, and install them automatically — just like how ECC (292 skills) and Claudex (162 skills) were discovered.
                  </p>

                  {/* Search by query */}
                  <div className="space-y-3 mb-4">
                    <div>
                      <label className="text-sm font-medium block mb-1">Search GitHub for skills</label>
                      <div className="flex gap-2">
                        <Input
                          placeholder="e.g. fastapi, react, security, tdd..."
                          value={discoverQuery}
                          onChange={e => setDiscoverQuery(e.target.value)}
                          onKeyDown={e => e.key === "Enter" && handleDiscover("search")}
                        />
                        <Button onClick={() => handleDiscover("search")} disabled={discovering || !discoverQuery.trim()}>
                          {discovering ? <Loader2 className="h-4 w-4 animate-spin"/> : <Search className="h-4 w-4"/>}
                          Search
                        </Button>
                      </div>
                    </div>

                    {/* Or paste a URL */}
                    <div>
                      <label className="text-sm font-medium block mb-1">Or paste a GitHub URL (repo, folder, or file)</label>
                      <div className="flex gap-2">
                        <Input
                          placeholder="https://github.com/user/repo/tree/main/skills"
                          value={discoverUrl}
                          onChange={e => setDiscoverUrl(e.target.value)}
                          onKeyDown={e => e.key === "Enter" && handleDiscover("url")}
                        />
                        <Button onClick={() => handleDiscover("url")} disabled={discovering || !discoverUrl.trim()} variant="outline">
                          {discovering ? <Loader2 className="h-4 w-4 animate-spin"/> : <Download className="h-4 w-4"/>}
                          Fetch
                        </Button>
                      </div>
                    </div>

                    {/* Quick actions */}
                    <div className="flex gap-2 flex-wrap">
                      <Button variant="outline" size="sm" onClick={() => handleDiscover("all")} disabled={discovering}>
                        {discovering ? <Loader2 className="mr-1 h-3 w-3 animate-spin"/> : <Globe className="mr-1 h-3 w-3"/>}
                        Scan All Known Repos
                      </Button>
                      <Button variant="outline" size="sm" onClick={handleFillGaps} disabled={discovering}>
                        {discovering ? <Loader2 className="mr-1 h-3 w-3 animate-spin"/> : <Wand2 className="mr-1 h-3 w-3"/>}
                        Auto-Fill Agent Skill Gaps
                      </Button>
                    </div>
                  </div>

                  {/* Results */}
                  {discoverMessage && (
                    <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm mb-4">
                      {discoverMessage}
                    </div>
                  )}

                  {discoveredSkills.length > 0 && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <h3 className="font-medium">Discovered Skills ({discoveredSkills.length})</h3>
                        <Button size="sm" onClick={handleInstallAllDiscovered} disabled={discovering}>
                          {discovering ? <Loader2 className="mr-1 h-3 w-3 animate-spin"/> : <Plus className="mr-1 h-3 w-3"/>}
                          Install All
                        </Button>
                      </div>
                      {discoveredSkills.map(s => (
                        <Card key={s.name}>
                          <CardContent className="p-4">
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <h4 className="font-medium">{s.display_name || s.name}</h4>
                                  <Badge variant="outline" className="text-xs">{s.origin}</Badge>
                                  <Badge variant="secondary" className="text-xs">{s.category}</Badge>
                                </div>
                                <p className="text-sm text-zinc-500 mt-1 line-clamp-2">{s.description}</p>
                                <div className="flex items-center gap-2 mt-1.5">
                                  {s.source_repo && <span className="text-xs text-zinc-400">{s.source_repo}</span>}
                                  {s.tools?.slice(0, 4).map((t: string) => <Badge key={t} variant="outline" className="text-[10px]">{t}</Badge>)}
                                </div>
                              </div>
                              <Button
                                size="sm"
                                onClick={() => handleInstallDiscovered(s.name)}
                                disabled={installingSkills.has(s.name)}
                              >
                                {installingSkills.has(s.name) ? <Loader2 className="mr-1 h-3 w-3 animate-spin"/> : <Plus className="mr-1 h-3 w-3"/>}
                                Install
                              </Button>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}

                  {discoveredRepos.length > 0 && (
                    <div className="mt-4 space-y-2">
                      <h3 className="font-medium">Relevant Repositories ({discoveredRepos.length})</h3>
                      {discoveredRepos.map(r => (
                        <div key={r.full_name} className="flex items-center justify-between p-3 border rounded-lg">
                          <div>
                            <p className="text-sm font-medium">{r.full_name}</p>
                            <p className="text-xs text-zinc-500 line-clamp-1">{r.description}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="text-xs">⭐ {r.stars}</Badge>
                            <Button size="sm" variant="outline" onClick={() => { setDiscoverUrl(r.url); handleDiscover("url"); }}>
                              Scan
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {discoveredSkills.length === 0 && discoveredRepos.length === 0 && !discoverMessage && (
                    <div className="text-center py-8 text-zinc-500">
                      <Globe className="h-12 w-12 mx-auto mb-3 text-zinc-300"/>
                      <p className="text-sm">Search GitHub or paste a URL to discover skills.</p>
                      <p className="text-xs text-zinc-400 mt-1">Mark will parse SKILL.md files and install them automatically.</p>
                    </div>
                  )}
                </Card>
              </TabsContent>

              <TabsContent value="builder" className="flex-1 overflow-auto">
                <Card className="p-6">
                  <h2 className="text-lg font-semibold flex items-center gap-2"><Wand2 className="h-5 w-5"/> Skill Builder - Build with Mark</h2>
                  <p className="text-sm text-zinc-500 mb-3">Describe in natural language: "Create a skill that researches property maintenance companies and generates an Excel comparison." MARK will generate a validated package.</p>
                  <textarea value={builderPrompt} onChange={e=>setBuilderPrompt(e.target.value)} placeholder="Describe the skill..." className="w-full min-h-[100px] px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800" />
                  <div className="flex gap-2 mt-3">
                    <Button variant="outline" onClick={handleValidate} disabled={validating}>{validating?<Loader2 className="h-4 w-4 animate-spin"/>:"Validate"}</Button>
                    <Button onClick={handleBuild} disabled={building} className="bg-blue-600 hover:bg-blue-700">
                      {building?<><Loader2 className="mr-2 h-4 w-4 animate-spin"/>Building</>:<><Wand2 className="mr-2 h-4 w-4"/>Build with Mark</>}
                    </Button>
                  </div>
                  <p className="text-xs text-zinc-400 mt-2">Generates manifest/tools/permissions/config_schema/dependencies → validates (name semver, tools list, permissions) → installs as CREATED_BY_MARK → version snapshot. No fake install.</p>
                </Card>
              </TabsContent>
            </Tabs>
          </main>
        </div>
      </div>

      <Sheet open={!!confirmTarget} onOpenChange={(o) => { if (!o) setConfirmTarget(null); }}>
        <SheetContent side="bottom" className="mx-auto max-w-md rounded-t-2xl">
          <SheetHeader>
            <SheetTitle>{confirmTarget?.action === "remove" ? "Remove this skill?" : "Rollback this skill?"}</SheetTitle>
            <SheetDescription>
              {confirmTarget?.action === "remove"
                ? `“${confirmTarget?.skill.display_name || confirmTarget?.skill.name || "Skill"}” will be removed from your skills.`
                : `“${confirmTarget?.skill.display_name || confirmTarget?.skill.name || "Skill"}” will be restored to its previous version.`}
            </SheetDescription>
          </SheetHeader>
          <SheetFooter>
            <SheetClose render={<Button variant="outline" />}>Cancel</SheetClose>
            <Button variant={confirmTarget?.action === "remove" ? "destructive" : "default"} onClick={confirmAction} disabled={confirming}>
              {confirming && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}{confirmTarget?.action === "remove" ? "Remove" : "Rollback"}
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </ProtectedLayout>
  );
}
