"use client";
import { useState, useEffect, useCallback } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ProtectedLayout } from "@/components/layout/protected-layout";
import { knowledgeApi, Knowledge } from "@/lib/api/knowledge";
import { projectsApi } from "@/lib/api/projects";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Plus, Search, Edit, Trash2, Power, Loader2, BookOpen } from "lucide-react";
import { toast } from "@/components/ui/toast";
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter, SheetClose,
} from "@/components/ui/sheet";

export default function KnowledgePage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [items, setItems] = useState<Knowledge[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [enabledFilter, setEnabledFilter] = useState<"all"|"enabled"|"disabled">("all");
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Knowledge | null>(null);
  const [form, setForm] = useState({ name:"", use_when:"", content:"", enabled:true, project_id:"", tags:"", confidence:100, importance:50 });
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Knowledge | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetch = useCallback(async()=>{
    setLoading(true);
    try {
      const res = await knowledgeApi.list({ search: search||undefined, enabled: enabledFilter==="all"?undefined:enabledFilter==="enabled", page:1, page_size:50 });
      setItems(res.knowledge);
    } finally { setLoading(false); }
  },[search, enabledFilter]);

  const fetchProjects = useCallback(async()=>{ try{ const r=await projectsApi.list({page_size:100}); setProjects(r.projects);}catch{} },[]);

  useEffect(()=>{ fetch(); fetchProjects(); },[fetch, fetchProjects]);

  const openCreate = ()=>{ setEditing(null); setForm({ name:"", use_when:"", content:"", enabled:true, project_id:"", tags:"", confidence:100, importance:50 }); setShowForm(true); };
  const openEdit = (k:Knowledge)=>{ setEditing(k); setForm({ name:k.name, use_when:k.use_when||"", content:k.content, enabled:k.enabled, project_id: k.project_id?String(k.project_id):"", tags:(k.tags||[]).join(", "), confidence:k.confidence||100, importance:k.importance||50 }); setShowForm(true); };

  const handleSave = async()=>{
    if (!form.name.trim() || !form.content.trim()) { toast.add({ title: "Name and Content required", type: "error" }); return; }
    setSaving(true);
    try {
      const data:any = {
        name: form.name.trim(),
        use_when: form.use_when.trim()||undefined,
        content: form.content.trim(),
        enabled: form.enabled,
        project_id: form.project_id?Number(form.project_id):undefined,
        tags: form.tags ? form.tags.split(",").map(s=>s.trim()).filter(Boolean) : undefined,
        confidence: Number(form.confidence),
        importance: Number(form.importance),
      };
      if (editing) await knowledgeApi.update(editing.id, data);
      else await knowledgeApi.create(data);
      setShowForm(false); fetch();
      toast.add({ title: editing ? "Knowledge updated" : "Knowledge created", type: "success" });
    } catch(e:any){ toast.add({ title: "Save failed", description: e?.message || "Try again.", type: "error" }); } finally{ setSaving(false); }
  };

  const handleToggle = async(k:Knowledge)=>{ try { await knowledgeApi.toggle(k.id); fetch(); } catch(e:any){ toast.add({ title: "Toggle failed", description: e?.message || "Try again.", type: "error" }); } };
  const confirmDelete = async()=>{
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await knowledgeApi.delete(deleteTarget.id); fetch();
      toast.add({ title: "Knowledge deleted", type: "success" });
    } catch(e:any){ toast.add({ title: "Couldn't delete knowledge", description: e?.message || "Try again.", type: "error" }); } finally{ setDeleting(false); setDeleteTarget(null); }
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
                <h1 className="text-2xl font-semibold flex items-center gap-2"><BookOpen className="h-6 w-6"/> Knowledge</h1>
                <p className="text-sm text-zinc-500">Entries: Name • Use When • Content • Enabled • Project • Confidence/Importance • Tags</p>
              </div>
              <Button onClick={openCreate}><Plus className="mr-2 h-4 w-4"/>New Knowledge</Button>
            </div>
            <div className="flex gap-2 mb-4">
              <div className="flex-1 max-w-md relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-zinc-400"/>
                <Input placeholder="Search name, content, use_when..." value={search} onChange={e=>setSearch(e.target.value)} className="pl-8" />
              </div>
              <select value={enabledFilter} onChange={e=>setEnabledFilter(e.target.value as any)} className="px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800">
                <option value="all">All</option>
                <option value="enabled">Enabled</option>
                <option value="disabled">Disabled</option>
              </select>
            </div>
            {loading ? <div className="flex justify-center p-8"><Loader2 className="h-6 w-6 animate-spin"/></div> :
              items.length===0 ? <Card className="p-8 text-center text-zinc-500">No knowledge entries. Create one.</Card> :
              <div className="space-y-3">
                {items.map(k=>(
                  <Card key={k.id}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <h3 className="font-medium">{k.name}</h3>
                            <Badge variant={k.enabled?"default":"secondary"}>{k.enabled?"Enabled":"Disabled"}</Badge>
                            {k.project_name && <Badge variant="outline">{k.project_name}</Badge>}
                          </div>
                          {k.use_when && <p className="text-xs text-blue-600 mt-1">Use when: {k.use_when}</p>}
                          <p className="text-sm text-zinc-600 mt-1 line-clamp-3 whitespace-pre-wrap">{k.content}</p>
                          <div className="flex gap-2 mt-2 flex-wrap text-xs text-zinc-500">
                            {k.tags?.map(t=> <Badge key={t} variant="outline" className="text-xs">{t}</Badge>)}
                            <span>Conf: {k.confidence}</span><span>Imp: {k.importance}</span><span>{new Date(k.updated_at || k.created_at).toLocaleString()}</span>
                          </div>
                        </div>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="icon" onClick={()=>handleToggle(k)} title={k.enabled?"Disable":"Enable"}><Power className={`h-4 w-4 ${k.enabled?"text-green-600":"text-zinc-400"}`}/></Button>
                          <Button variant="ghost" size="icon" onClick={()=>openEdit(k)}><Edit className="h-4 w-4"/></Button>
                          <Button variant="ghost" size="icon" onClick={()=>setDeleteTarget(k)}><Trash2 className="h-4 w-4 text-red-500"/></Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            }
            {showForm && (
              <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50 overflow-auto" onClick={()=>setShowForm(false)}>
                <Card className="w-full max-w-lg max-h-[90vh] overflow-auto" onClick={e=>e.stopPropagation()}>
                  <CardContent className="p-6 space-y-3">
                    <h2 className="text-lg font-semibold">{editing?"Edit Knowledge":"New Knowledge"}</h2>
                    <div><label className="text-sm font-medium">Name *</label><Input value={form.name} onChange={e=>setForm({...form, name:e.target.value})} placeholder="e.g., Property CRM Preference" /></div>
                    <div><label className="text-sm font-medium">Use When</label><Input value={form.use_when} onChange={e=>setForm({...form, use_when:e.target.value})} placeholder="e.g., When user asks about CRM..." /></div>
                    <div><label className="text-sm font-medium">Content *</label><textarea value={form.content} onChange={e=>setForm({...form, content:e.target.value})} placeholder="Knowledge content..." className="w-full min-h-[100px] px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800" /></div>
                    <div className="grid grid-cols-2 gap-3">
                      <div><label className="text-sm">Project</label><select value={form.project_id} onChange={e=>setForm({...form, project_id:e.target.value})} className="w-full mt-1 px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800"><option value="">Global</option>{projects.map(p=> <option key={p.id} value={p.id}>{p.name}</option>)}</select></div>
                      <div className="flex items-center gap-2 mt-6"><input type="checkbox" checked={form.enabled} onChange={e=>setForm({...form, enabled:e.target.checked})} id="k-enabled"/><label htmlFor="k-enabled" className="text-sm">Enabled</label></div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div><label className="text-sm">Confidence (0-100)</label><Input type="number" min={0} max={100} value={form.confidence} onChange={e=>setForm({...form, confidence: Number(e.target.value)})} /></div>
                      <div><label className="text-sm">Importance (0-100)</label><Input type="number" min={0} max={100} value={form.importance} onChange={e=>setForm({...form, importance: Number(e.target.value)})} /></div>
                    </div>
                    <div><label className="text-sm">Tags (comma separated)</label><Input value={form.tags} onChange={e=>setForm({...form, tags:e.target.value})} placeholder="crm, preference, operations" /></div>
                    <div className="flex gap-2 justify-end">
                      <Button variant="outline" onClick={()=>setShowForm(false)}>Cancel</Button>
                      <Button onClick={handleSave} disabled={saving}>{saving?<><Loader2 className="mr-2 h-4 w-4 animate-spin"/>Saving</>:editing?"Update":"Create"}</Button>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </main>
        </div>
      </div>

      <Sheet open={!!deleteTarget} onOpenChange={(o) => { if (!o) setDeleteTarget(null); }}>
        <SheetContent side="bottom" className="mx-auto max-w-md rounded-t-2xl">
          <SheetHeader>
            <SheetTitle>Delete this knowledge entry?</SheetTitle>
            <SheetDescription>“{deleteTarget?.name || "Knowledge"}” will be permanently removed.</SheetDescription>
          </SheetHeader>
          <SheetFooter>
            <SheetClose render={<Button variant="outline" />}>Cancel</SheetClose>
            <Button variant="destructive" onClick={confirmDelete} disabled={deleting}>
              {deleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Delete
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </ProtectedLayout>
  );
}
