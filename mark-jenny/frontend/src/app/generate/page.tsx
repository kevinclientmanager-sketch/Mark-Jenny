"use client";
import { useState, useEffect } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ProtectedLayout } from "@/components/layout/protected-layout";
import { generativeApi, GenerateResult } from "@/lib/api/generative";
import { projectsApi } from "@/lib/api/projects";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Globe, Code2, Presentation, Image as ImageIcon, Wand2, Search, Table, Video, Music, FileText, Code, Loader2, Download, Play } from "lucide-react";
import { toast } from "@/components/ui/toast";

const TYPE_ICON: Record<string, any> = {
  website: Globe, app: Code2, slides: Presentation, image: ImageIcon, "image-edit": Wand2,
  research: Search, spreadsheet: Table, video: Video, audio: Music, document: FileText, code: Code
};

export default function GeneratePage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [types, setTypes] = useState<any[]>([]);
  const [active, setActive] = useState("website");
  const [projects, setProjects] = useState<any[]>([]);
  const [projectId, setProjectId] = useState<string>("");
  const [prompt, setPrompt] = useState("");
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(()=>{
    (async()=>{
      try {
        const [t, p] = await Promise.all([generativeApi.types(), projectsApi.list({page_size:100})]);
        setTypes(t);
        setProjects(p.projects);
        if(t.length) setActive(t[0].id);
      } catch {}
    })();
  },[]);

  const handleGenerate = async()=>{
    if(!prompt.trim()) { toast.add({ title: "Enter a prompt", description: "Describe what Mark should generate.", type: "error" }); return; }
    setLoading(true); setResult(null);
    try {
      const r = await generativeApi.generate(active, { prompt: prompt.trim(), project_id: projectId?Number(projectId):undefined });
      setResult(r);
      toast.add({ title: "Generated", description: `${r.type} task started - task #${r.task_id}`, type: "success" });
    } catch(e:any){ toast.add({ title: "Generation failed", description: e?.message || "Try again.", type: "error" }); } finally{ setLoading(false); }
  };

  const currentType = types.find(t=>t.id===active);
  const Icon = TYPE_ICON[active] || FileText;

  return (
    <ProtectedLayout>
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex">
        <Sidebar isOpen={sidebarOpen} onToggle={()=>setSidebarOpen(!sidebarOpen)} />
        <div className={`flex-1 flex flex-col min-w-0 transition-all ${sidebarOpen?"ml-64":"ml-16"}`}>
          <Header />
          <main className="flex-1 p-6 overflow-auto">
            <h1 className="text-2xl font-semibold">Generative Workflows</h1>
            <p className="text-sm text-zinc-500 mb-4">Website • App • Slides • Image • Edit • Research • Spreadsheet • Video • Audio • Document • Code — each creates real files saved to project, tracked as Task, previewable.</p>

            <Tabs value={active} onValueChange={setActive} className="flex-1 flex flex-col">
              <TabsList className="grid w-full grid-cols-4 lg:grid-cols-6 mb-4 gap-1 h-auto">
                {types.map(t=>{
                  const I = TYPE_ICON[t.id] || FileText;
                  return <TabsTrigger key={t.id} value={t.id} className="flex flex-col py-2 h-auto"><I className="h-4 w-4 mb-1"/><span className="text-xs">{t.label}</span></TabsTrigger>;
                })}
              </TabsList>

              {types.map(t=>(
                <TabsContent key={t.id} value={t.id} className="flex-1">
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="flex items-center gap-2 text-base">
                        {(() => { const I = TYPE_ICON[t.id] || FileText; return <I className="h-5 w-5"/>; })()}
                        {t.label} <Badge variant="outline">{t.id}</Badge>
                      </CardTitle>
                      <p className="text-sm text-zinc-500">{t.desc} — {active===t.id && currentType?.desc}</p>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <div className="md:col-span-2">
                          <label className="text-sm font-medium">Prompt *</label>
                          <textarea value={prompt} onChange={e=>setPrompt(e.target.value)} placeholder={
                            t.id==="website"?"Build a landing page for a property maintenance CRM with hero, features, pricing":
                            t.id==="spreadsheet"?"Create an Excel comparison of 5 property CRMs with pricing and features":
                            t.id==="research"?"Research the best property maintenance CRM and write a report":
                            `Describe the ${t.label.toLowerCase()} to generate...`
                          } className="w-full mt-1 min-h-[90px] px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800" />
                        </div>
                        <div className="space-y-2">
                          <div>
                            <label className="text-sm font-medium">Project</label>
                            <select value={projectId} onChange={e=>setProjectId(e.target.value)} className="w-full mt-1 px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800">
                              <option value="">General</option>
                              {projects.map((p:any)=> <option key={p.id} value={p.id}>{p.name}</option>)}
                            </select>
                          </div>
                          <Button onClick={handleGenerate} disabled={loading || !prompt.trim()} className="w-full bg-blue-600 hover:bg-blue-700">
                            {loading ? <><Loader2 className="mr-2 h-4 w-4 animate-spin"/>Generating</> : <><Play className="mr-2 h-4 w-4"/>Generate {t.label}</>}
                          </Button>
                          <p className="text-xs text-zinc-400">Creates Task + File(s) in `uploads/generated/{active}/` + File DB entry</p>
                        </div>
                      </div>

                      {result && result.type===t.id && (
                        <Card className="bg-green-50 dark:bg-green-900/20 border-green-200">
                          <CardContent className="p-3">
                            <p className="text-sm font-medium text-green-800 dark:text-green-300">{result.message}</p>
                            <p className="text-xs text-zinc-600">Task #{result.task_id} • {result.files.length} file(s)</p>
                            <div className="flex flex-wrap gap-2 mt-2">
                              {result.files.map((f:any)=>(
                                <a key={f.id} href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/files/${f.id}/download`} target="_blank" className="inline-flex items-center gap-1 text-xs px-2 py-1 bg-white dark:bg-zinc-800 border rounded hover:bg-zinc-50">
                                  <Download className="h-3 w-3"/>{f.name} ({Math.round(f.size/1024)}KB)
                                </a>
                              ))}
                              {result.preview_url && <Badge variant="outline">Preview: {result.preview_url}</Badge>}
                            </div>
                          </CardContent>
                        </Card>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>
              ))}
            </Tabs>
          </main>
        </div>
      </div>
    </ProtectedLayout>
  );
}


