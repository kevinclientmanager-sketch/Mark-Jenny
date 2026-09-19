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
import { Loader2, ArrowLeft, FolderKanban, Copy, Trash2, ExternalLink, Calendar } from "lucide-react";
import Link from "next/link";
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
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex">
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <div className={`flex-1 flex flex-col min-w-0 transition-all ${sidebarOpen ? "ml-64" : "ml-16"}`}>
          <Header />
          <main className="flex-1 overflow-auto">
            <div className="mx-auto max-w-4xl p-6">
              {loading ? (
                <div className="flex justify-center p-12"><Loader2 className="h-6 w-6 animate-spin" /></div>
              ) : !project ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <FolderKanban className="h-12 w-12 mb-3 text-zinc-300 dark:text-zinc-700" />
                  <p className="text-lg font-medium">Project not found</p>
                  <p className="text-sm text-zinc-500">It may have been deleted, or you don&apos;t have access.</p>
                  <Button className="mt-4" variant="outline" onClick={() => router.push("/projects")}>
                    <ArrowLeft className="mr-2 h-4 w-4" /> Back to projects
                  </Button>
                </div>
              ) : (
                <>
                  <div className="mb-6">
                    <Link href="/projects" className="text-sm text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 flex items-center gap-1">
                      <ArrowLeft className="h-3.5 w-3.5" /> Projects
                    </Link>
                    <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-600">
                          <FolderKanban className="h-5 w-5 text-white" />
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <h1 className="truncate text-xl font-semibold tracking-tight">{project.name}</h1>
                            <Badge variant={project.status === "active" ? "default" : "secondary"}>{project.status}</Badge>
                          </div>
                          <div className="mt-0.5 flex items-center gap-3 text-xs text-zinc-500">
                            <span>{project.task_count} tasks · {project.file_count} files · {project.skill_count} skills</span>
                            {project.last_modified && (
                              <span className="flex items-center gap-1"><Calendar className="h-3 w-3" /> {new Date(project.last_modified).toLocaleDateString()}</span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Link href={`/chat`}>
                          <Button variant="outline" size="sm">
                            <ExternalLink className="mr-1.5 h-3.5 w-3.5" /> Open in Chat
                          </Button>
                        </Link>
                        <Button variant="ghost" size="icon" onClick={handleDuplicate} title="Duplicate">
                          <Copy className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={handleDelete} title="Delete" className="text-red-500 hover:text-red-600">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                    {project.description && <p className="mt-2 max-w-2xl text-sm text-zinc-500">{project.description}</p>}
                  </div>
                  <ProjectWorkspace projectId={id} />
                </>
              )}
            </div>
          </main>
        </div>
      </div>
    </ProtectedLayout>
  );
}