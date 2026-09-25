"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LayoutDashboard, Calendar, Library, FolderKanban } from "lucide-react";
import { ScheduledTab } from "./scheduled-tab";
import { LibraryTab } from "./library-tab";
import { ProjectsTab } from "./projects-tab";

export function Dashboard() {
  return (
    <div className="h-full flex flex-col">
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">Dashboard</h2>
        <p className="text-zinc-500 dark:text-zinc-400 mt-1">
          Overview of your projects, scheduled tasks, and library
        </p>
      </div>

      <Tabs defaultValue="projects" className="flex-1 flex flex-col">
        <TabsList className="grid w-full grid-cols-3 mb-4">
          <TabsTrigger value="projects">
            <FolderKanban className="mr-2 h-4 w-4" />
            Projects
          </TabsTrigger>
          <TabsTrigger value="scheduled">
            <Calendar className="mr-2 h-4 w-4" />
            Scheduled
          </TabsTrigger>
          <TabsTrigger value="library">
            <Library className="mr-2 h-4 w-4" />
            Library
          </TabsTrigger>
        </TabsList>

        <TabsContent value="projects" className="flex-1">
          <ProjectsTab />
        </TabsContent>
        <TabsContent value="scheduled" className="flex-1">
          <ScheduledTab />
        </TabsContent>
        <TabsContent value="library" className="flex-1">
          <LibraryTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

