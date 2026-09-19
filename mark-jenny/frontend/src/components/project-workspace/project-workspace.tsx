"use client";

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FileText, FolderKanban, Brain, Plug, Loader2 } from "lucide-react";
import { InstructionsTab } from "./instructions-tab";
import { FilesSourceTab } from "./files-source-tab";
import { SkillsTab } from "./skills-tab";
import { ConnectorsTab } from "./connectors-tab";

interface ProjectWorkspaceProps {
  projectId: number;
}

export function ProjectWorkspace({ projectId }: ProjectWorkspaceProps) {
  const [activeTab, setActiveTab] = useState<"instructions" | "files" | "skills" | "connectors">("instructions");
  const [loading, setLoading] = useState(false);

  return (
    <div className="h-full flex flex-col">
      <div className="mb-4">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="instructions">
              <FileText className="mr-2 h-4 w-4" />
              Instructions
            </TabsTrigger>
            <TabsTrigger value="files">
              <FolderKanban className="mr-2 h-4 w-4" />
              Files & Source
            </TabsTrigger>
            <TabsTrigger value="skills">
              <Brain className="mr-2 h-4 w-4" />
              Skills
            </TabsTrigger>
            <TabsTrigger value="connectors">
              <Plug className="mr-2 h-4 w-4" />
              Connectors
            </TabsTrigger>
          </TabsList>

          {loading && (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
          )}

          <TabsContent value="instructions" className="mt-4 flex-1">
            <InstructionsTab projectId={projectId} />
          </TabsContent>
          <TabsContent value="files" className="mt-4 flex-1">
            <FilesSourceTab projectId={projectId} />
          </TabsContent>
          <TabsContent value="skills" className="mt-4 flex-1">
            <SkillsTab projectId={projectId} />
          </TabsContent>
          <TabsContent value="connectors" className="mt-4 flex-1">
            <ConnectorsTab projectId={projectId} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}