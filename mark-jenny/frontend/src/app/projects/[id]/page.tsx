"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ProtectedLayout } from "@/components/layout/protected-layout";
import { ProjectWorkspace } from "@/components/project-workspace/project-workspace";
import { projectsApi, Project } from "@/lib/api/projects";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, FolderKanban, Copy, Trash2, ArrowLeft } from "lucide-react";
import { toast } from "@/components/ui/toast";

export default function ProjectDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const id = Number(params?.id);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchProject = useCallback(async () => {
    if (!id || Number.isNaN(id)) { setLoading(false); return; }
    setLoading(true);
    try {
      setProject(await projectsApi.get(id));
    } catch {
      setProject(null);
    } finally { setLoading(false); }
  }, [id]);

  useEffect(() => { fetchProject(); }, [fetchProject]);

  const handleDuplicate = async () => {
    try {
      const dup = await projectsApi.duplicate(id);
      toast.add({ title: "Project duplicated", description: dup.name, type: "success" });
      fetchProject();
    } catch { toast.add({ title: "Duplicate failed", type: "error" }); }
  };

  const handleDelete = async () => {
    try {
      await projectsApi.delete(id);
      toast.add({ title: "Project deleted", type: "success" });
      router.push("/projects");
    } catch { toast.add({ title: "Couldn't delete project", type: "error" }); }
  };

  return (
    <ProtectedLayout>
      <div className="h-screen bg-zinc-50 dark:bg-zinc-950 flex overflow-hidden">
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <div className={`flex-1 flex flex-col min-w-0 transition-all ${sidebarOpen ? "ml-64" : "ml-16"}`}>
          <Header />
          {/* Compact project header bar */}
          <div className="shrink-0 border-b bg-white dark:bg-zinc-900 px-4 py-2">
            {loading ? (
              <div className="flex items-center gap-2 h-8">
                <Loader2 className="h-4 w-4 animate-spin text-zinc-400" />
                <span className="text-xs text-zinc-400">Loading project...</span>
              </div>
            ) : project ? (
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <button onClick={() => router.push("/projects")} className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 shrink-0" title="Back to projects">
                    <ArrowLeft className="h-4 w-4" />
                  </button>
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-blue-600">
                    <FolderKanban className="h-3.5 w-3.5 text-white" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <h1 className="truncate text-sm font-semibold">{project.name}</h1>
                      <Badge variant={project.status === "active" ? "default" : "secondary"} className="text-[10px] px-1.5 py-0">{project.status}</Badge>
                    </div>
                  </div>
                  <div className="hidden sm:flex items-center gap-3 text-[11px] text-zinc-400 shrink-0">
                    <span>{project.task_count} tasks</span>
                    <span>{project.file_count} files</span>
                    <span>{project.skill_count} skills</span>
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleDuplicate} title="Duplicate">
                    <Copy className="h-3.5 w-3.5" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500 hover:text-red-600" onClick={handleDelete} title="Delete">
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2 h-8">
                <FolderKanban className="h-4 w-4 text-zinc-300" />
                <span className="text-sm text-zinc-500">Project not found</span>
                <Button variant="outline" size="sm" className="ml-2 h-6 text-xs" onClick={() => router.push("/projects")}>
                  Back
                </Button>
              </div>
            )}
          </div>
          {/* Project workspace — fills remaining space */}
          <main className="flex-1 overflow-auto">
            {project && <ProjectWorkspace projectId={id} />}
          </main>
        </div>
      </div>
    </ProtectedLayout>
  );
}
