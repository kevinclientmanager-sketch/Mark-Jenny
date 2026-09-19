"use client";

import { useState, useEffect, useCallback } from "react";
import { Plus, MoreHorizontal, Check, X, Loader2, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { projectsApi, ProjectSkill } from "@/lib/api/projects";
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter, SheetClose,
} from "@/components/ui/sheet";
import { toast } from "@/components/ui/toast";

export function SkillsTab({ projectId }: { projectId: number }) {
  const [projectSkills, setProjectSkills] = useState<ProjectSkill[]>([]);
  const [availableSkills, setAvailableSkills] = useState<ProjectSkill[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [addMethod, setAddMethod] = useState<"official" | "github" | "upload" | "build">("official");
  const [githubUrl, setGithubUrl] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [removeTarget, setRemoveTarget] = useState<ProjectSkill | null>(null);
  const [removing, setRemoving] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      // Get project skills
      const projectSkillsResponse = await projectsApi.listSkills(projectId);
      setProjectSkills(projectSkillsResponse);
      
      // Get available skills (for adding new ones)
      const availableSkillsResponse = await projectsApi.list({ page_size: 100 });
      const projectSkillIds = new Set(projectSkillsResponse.map(ps => ps.id));
      const available = (availableSkillsResponse.projects as unknown as ProjectSkill[]).filter(s => !projectSkillIds.has(s.id));
      setAvailableSkills(available);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

const handleAddSkill = async (skillId: number) => {
    setAdding(true);
    try {
      // await projectsApi.addSkill(projectId, skillId);
      fetchData();
      setShowAddModal(false);
      toast.add({ title: "Skill added", type: "success" });
    } catch (err) {
      toast.add({ title: "Failed to add skill", type: "error" });
      console.error(err);
    } finally {
      setAdding(false);
    }
  };

  const confirmRemove = async () => {
    if (!removeTarget) return;
    setRemoving(true);
    try {
      // await projectsApi.removeSkill(projectId, removeTarget.id);
      fetchData();
      toast.add({ title: "Skill removed from project", description: removeTarget.name, type: "success" });
    } catch (err) {
      toast.add({ title: "Failed to remove skill", type: "error" });
      console.error(err);
    } finally {
      setRemoving(false);
      setRemoveTarget(null);
    }
  };

  const handleToggleSkill = async (skill: ProjectSkill, enabled: boolean) => {
    try {
      // await projectsApi.updateSkill(projectId, skill.id, enabled);
      setProjectSkills(prev => prev.map(s => s.id === skill.id ? { ...s, enabled } : s));
    } catch (err) {
      console.error(err);
    }
  };

  const filteredSkills = projectSkills.filter(s =>
    s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredAvailable = availableSkills.filter(s =>
    s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-semibold">Project Skills</h2>
          <p className="text-zinc-500 text-sm">Manage skills available to this project</p>
        </div>
        <Button onClick={() => setShowAddModal(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Add Skill
        </Button>
      </div>

      <Tabs defaultValue="enabled" className="flex-1 flex flex-col">
        <TabsList className="grid w-full grid-cols-2 mb-4 max-w-xs">
          <TabsTrigger value="enabled">Enabled ({filteredSkills.filter(s => s.enabled).length})</TabsTrigger>
          <TabsTrigger value="available">Available ({filteredAvailable.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="enabled" className="flex-1 overflow-auto">
          {filteredSkills.filter(s => s.enabled).length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-zinc-500">
              <p className="mb-4">No enabled skills</p>
              <Button onClick={() => setShowAddModal(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Add Skill
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredSkills.filter(s => s.enabled).map((skill) => (
                <Card key={skill.id}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <h4 className="font-medium">{skill.name}</h4>
                          <Badge variant="default" className="bg-green-100 text-green-700">Enabled</Badge>
                          <Badge variant="outline" className="text-xs">{skill.source}</Badge>
                        </div>
                        <p className="text-sm text-zinc-500 mt-1">{skill.description || "No description"}</p>
                        <div className="flex items-center gap-4 text-xs text-zinc-500 mt-2">
                          <span>v{skill.version}</span>
                          <span>Updated {skill.last_updated ? new Date(skill.last_updated).toLocaleDateString() : "Unknown"}</span>
                        </div>
                      </div>
                      <DropdownMenu>
                        <DropdownMenuTrigger>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
<DropdownMenuItem onClick={() => handleToggleSkill(skill, false)}>
                            <X className="mr-2 h-4 w-4" />
                            Disable
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem className="text-red-600" onClick={() => setRemoveTarget(skill)}>
                            <Trash2 className="mr-2 h-4 w-4" />
                            Remove from Project
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="available" className="flex-1 overflow-auto">
          <div className="mb-4">
            <Input
              placeholder="Search available skills..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          {filteredAvailable.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-zinc-500">
              <p className="mb-4">No available skills found</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredAvailable.map((skill) => (
                <Card key={skill.id}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <h4 className="font-medium">{skill.name}</h4>
                          <Badge variant="secondary">Not Installed</Badge>
                          <Badge variant="outline" className="text-xs">{skill.source}</Badge>
                        </div>
                        <p className="text-sm text-zinc-500 mt-1">{skill.description || "No description"}</p>
                        <div className="flex items-center gap-4 text-xs text-zinc-500 mt-2">
                          <span>v{skill.version}</span>
                        </div>
                      </div>
                      <Button size="sm" onClick={() => handleAddSkill(skill.id)} disabled={adding}>
                        <Plus className="mr-2 h-4 w-4" />
                        Add
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
</Tabs>

      {/* Remove confirmation */}
      <Sheet open={!!removeTarget} onOpenChange={(o) => { if (!o) setRemoveTarget(null); }}>
        <SheetContent side="bottom" className="mx-auto max-w-md rounded-t-2xl">
          <SheetHeader>
            <SheetTitle>Remove this skill from the project?</SheetTitle>
            <SheetDescription>“{removeTarget?.name || "Skill"}” won't be available to this project anymore.</SheetDescription>
          </SheetHeader>
          <SheetFooter>
            <SheetClose render={<Button variant="outline" />}>Cancel</SheetClose>
            <Button variant="destructive" onClick={confirmRemove} disabled={removing}>
              {removing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Remove
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </div>
  );
}

