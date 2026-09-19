"use client";

import { useState, useEffect, useCallback } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FileText, FolderKanban, Brain, Plug, Loader2 } from "lucide-react";
import { InstructionsTab } from "./instructions-tab";
import { FilesSourceTab } from "./files-source-tab";
import { SkillsTab } from "./skills-tab";
import { ConnectorsTab } from "./connectors-tab";
import { projectsApi, Project } from "@/lib/api/projects";

interface ProjectWorkspaceProps {
  projectId: number;
}

export function ProjectWorkspace({ projectId }: ProjectWorkspaceProps) {
  const [activeTab, setActiveTab] = useState<"instructions" | "files" | "skills" | "connectors">("instructions");
  const [loading, setLoading] = useState(false);
  const [project, setProject] = useState<Project | null>(null);

  const fetchProject = useCallback(async () => {
    try {
      const p = await projectsApi.get(projectId);
      setProject(p);
    } catch {}
  }, [projectId]);

  useEffect(() => { fetchProject(); }, [fetchProject]);

  const TABS_CONFIG = [
    { value: "instructions" as const, label: "Instructions", icon: FileText, count: undefined },
    { value: "files" as const, label: "Files & Source", icon: FolderKanban, count: project?.file_count },
    { value: "skills" as const, label: "Skills", icon: Brain, count: project?.skill_count },
    { value: "connectors" as const, label: "Connectors", icon: Plug, count: undefined },
  ];

  return (
    <div className="h-full flex flex-col">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
        <div className="shrink-0 border-b bg-white dark:bg-zinc-900 px-4">
          <TabsList className="h-9 bg-transparent p-0 gap-0">
            {TABS_CONFIG.map((tab) => (
              <TabsTrigger
                key={tab.value}
                value={tab.value}
                className="flex items-center gap-1.5 rounded-none border-b-2 border-transparent px-3 py-2 text-xs font-medium text-zinc-500 data-[state=active]:border-blue-600 data-[state=active]:text-zinc-900 dark:data-[state=active]:text-zinc-100 hover:text-zinc-800 dark:hover:text-zinc-200 transition-colors"
              >
                <tab.icon className="h-3.5 w-3.5" />
                {tab.label}
                {tab.count !== undefined && (
                  <span className="ml-1 text-[10px] text-zinc-400 font-normal">{tab.count}</span>
                )}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>

        {loading && (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
          </div>
        )}

        <div className="flex-1 overflow-auto">
          <TabsContent value="instructions" className="h-full m-0">
            <InstructionsTab projectId={projectId} />
          </TabsContent>
          <TabsContent value="files" className="h-full m-0">
            <FilesSourceTab projectId={projectId} />
          </TabsContent>
          <TabsContent value="skills" className="h-full m-0">
            <SkillsTab projectId={projectId} />
          </TabsContent>
          <TabsContent value="connectors" className="h-full m-0">
            <ConnectorsTab projectId={projectId} />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
