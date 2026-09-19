"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ProtectedLayout } from "@/components/layout/protected-layout";
import { quickActionsApi, QuickAction } from "@/lib/api/quickActions";
import { projectsApi } from "@/lib/api/projects";
import { filesApi } from "@/lib/api/files";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Camera, Image as ImageIcon, File, Laptop, Plug, Code2, Presentation, Wand2, Search, Calendar, Table, Video, Music, BookOpen, Loader2, Play } from "lucide-react";
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter, SheetClose,
} from "@/components/ui/sheet";
import { toast } from "@/components/ui/toast";

const iconMap: Record<string, any> = {
  Camera, Image: ImageIcon, File, Laptop, Plug, Code2, Presentation, Wand2, Search, Calendar, Table, Video, Music, BookOpen
};

export default function QuickActionsPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [actions, setActions] = useState<QuickAction[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAction, setSelectedAction] = useState<QuickAction | null>(null);
  const [prompt, setPrompt] = useState("");
  const [projectId, setProjectId] = useState<number | undefined>(undefined);
  const [file, setFile] = useState<File | null>(null);
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState<any>(null);
  const router = useRouter();

  useEffect(()=>{
    (async()=>{
      setLoading(true);
      try {
        const [a, p] = await Promise.all([quickActionsApi.list(), projectsApi.list({page_size:100})]);
        setActions(a);
        setProjects(p.projects);
      } catch {
        toast.add({ title: "Couldn't load quick actions", type: "error" });
      } finally { setLoading(false); }
    })();
  },[]);

  const handleExecute = async ()=>{
    if (!selectedAction) return;
    if (!prompt.trim()) { toast.add({ title: "Enter a prompt", description: "Describe what Mark should do.", type: "error" }); return; }
    setExecuting(true);
    setResult(null);
    try {
      let file_ids: number[] | undefined;
      if (file && selectedAction.needs_file) {
        const uploaded = await filesApi.uploadFile(file, { project_id: projectId });
        file_ids = [uploaded.id];
      }
      const res = await quickActionsApi.execute(selectedAction.id, { prompt, project_id: projectId, file_ids });
      setResult(res);
      toast.add({ title: "Task created", description: res.message || `Kicked off ${selectedAction.label}.`, type: "success" });
      if (res.route) {
        const route = res.route.replace("{project}", String(projectId || ""));
        setSelectedAction(null);
        router.push(route || "/chat");
      }
    } catch(e:any){ toast.add({ title: "Execution failed", description: e?.message || "Try again.", type: "error" }); } finally{ setExecuting(false); }
  };

  const handleCardClick = (a: QuickAction) => {
    setSelectedAction(a);
    setPrompt("");
    setFile(null);
    setResult(null);
    const prefixMap: Record<string,string> = {
      "build-website":"Build a website that ",
      "develop-apps":"Develop an application that ",
      "create-slides":"Create slides about ",
      "create-image":"Create an image of ",
      "edit-image":"Edit this image to ",
      "wide-research":"Wide Research: research and compare ",
      "create-spreadsheet":"Create a spreadsheet for ",
      "create-video":"Create a video about ",
      "generate-audio":"Generate audio for ",
      "playbook":"Create a playbook for ",
    };
    if (prefixMap[a.id]) setPrompt(prefixMap[a.id]);
  };

  return (
    <ProtectedLayout>
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex">
        <Sidebar isOpen={sidebarOpen} onToggle={()=>setSidebarOpen(!sidebarOpen)} />
        <div className={`flex-1 flex flex-col min-w-0 transition-all ${sidebarOpen?"ml-64":"ml-16"}`}>
          <Header />
          <main className="flex-1 p-6 overflow-auto">
            <div className="mx-auto max-w-6xl">
              <div className="mb-6">
                <h1 className="text-2xl font-semibold tracking-tight">Quick Actions</h1>
                <p className="text-sm text-zinc-500">All workflows — each creates a tracked Task or navigates to its manager. No dead buttons.</p>
              </div>
              {loading ? <div className="flex justify-center p-8"><Loader2 className="h-6 w-6 animate-spin"/></div> : actions.length === 0 ? (
                <Card className="p-8 text-center text-zinc-500">No quick actions found.</Card>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {actions.map(a=>{
                    const Icon = iconMap[a.icon] || File;
                    return (
                      <Card key={a.id} className="hover:shadow-md transition-shadow cursor-pointer group" onClick={()=>handleCardClick(a)}>
                        <CardHeader className="pb-2">
                          <div className="flex items-center gap-3">
                            <div className="h-10 w-10 rounded-lg bg-zinc-900/5 dark:bg-white/10 flex items-center justify-center"><Icon className="h-5 w-5 text-blue-600 dark:text-blue-400"/></div>
                            <CardTitle className="text-base">{a.label}</CardTitle>
                          </div>
                        </CardHeader>
                        <CardContent>
                          <p className="text-sm text-zinc-500 mb-2">{a.desc}</p>
                          <div className="flex gap-1">
                            <Badge variant="outline" className="text-xs">{a.category}</Badge>
                            {a.needs_file && <Badge variant="secondary" className="text-xs">needs file</Badge>}
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              )}
            </div>
          </main>
        </div>
      </div>

      <Sheet open={!!selectedAction} onOpenChange={(o)=>{ if(!o) setSelectedAction(null); }}>
        <SheetContent side="bottom" className="mx-auto max-w-lg rounded-t-2xl">
          {selectedAction && (
            <>
              <SheetHeader>
                <SheetTitle className="flex items-center gap-2">
                  {(() => { const Icon = iconMap[selectedAction.icon] || File; return <Icon className="h-5 w-5 text-blue-600 dark:text-blue-400"/>; })()}
                  {selectedAction.label}
                </SheetTitle>
                <SheetDescription>{selectedAction.desc}</SheetDescription>
              </SheetHeader>
              <div className="space-y-3 px-4">
                <div>
                  <label className="text-sm font-medium">Project</label>
                  <select value={projectId || ""} onChange={e=>setProjectId(e.target.value?Number(e.target.value):undefined)} className="w-full mt-1 px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800">
                    <option value="">General</option>
                    {projects.map(p=> <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </div>
                {selectedAction.needs_file && (
                  <div>
                    <label className="text-sm font-medium">File (required)</label>
                    <Input type="file" onChange={e=>setFile(e.target.files?.[0]||null)} className="mt-1" />
                    {file && <p className="text-xs text-zinc-500 mt-1">{file.name} ({Math.round(file.size/1024)}KB)</p>}
                  </div>
                )}
                <div>
                  <label className="text-sm font-medium">Prompt</label>
                  <textarea value={prompt} onChange={e=>setPrompt(e.target.value)} placeholder="Describe what MARK should do..." className="w-full mt-1 min-h-[90px] px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800" />
                </div>
                {result && !result.route && (
                  <div className="p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 text-sm">
                    <p className="font-medium text-green-800 dark:text-green-300">{result.message}</p>
                    {result.task_id && (
                      <p className="mt-1 text-xs">
                        Task #{result.task_id} ·{" "}
                        <a href="/chat" className="underline">Chat</a> · live in Dashboard
                      </p>
                    )}
                  </div>
                )}
              </div>
              <SheetFooter>
                <SheetClose render={<Button variant="outline" />}>Cancel</SheetClose>
                <Button onClick={handleExecute} disabled={executing || !prompt.trim() || (selectedAction.needs_file && !file)}>
                  {executing ? <><Loader2 className="mr-2 h-4 w-4 animate-spin"/>Creating...</> : <><Play className="mr-2 h-4 w-4"/>Execute</>}
                </Button>
              </SheetFooter>
            </>
          )}
        </SheetContent>
      </Sheet>
    </ProtectedLayout>
  );
}