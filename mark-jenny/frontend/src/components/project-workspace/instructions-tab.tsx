"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Save, RotateCcw, Clock, Loader2, AlertCircle, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { projectWorkspaceApi } from "@/lib/api/projectWorkspace";
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter, SheetClose,
} from "@/components/ui/sheet";
import { toast } from "@/components/ui/toast";

interface Version {
  id: number;
  project_id: number;
  content: string;
  version: number;
  created_by: number;
  created_at: string;
}

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString();
};

export function InstructionsTab({ projectId }: { projectId: number }) {
  const [content, setContent] = useState("");
  const [savedContent, setSavedContent] = useState("");
  const [versions, setVersions] = useState<Version[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [restoreTarget, setRestoreTarget] = useState<Version | null>(null);
  const [restoring, setRestoring] = useState(false);
  const autosaveTimerRef = useRef<NodeJS.Timeout | null>(null);
  const lastSavedRef = useRef<string>("");

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await projectWorkspaceApi.getInstructions(projectId);
      setContent(data.content);
      setSavedContent(data.content);
      lastSavedRef.current = data.content;
      if (data.versions) {
        setVersions(data.versions);
      }
    } catch (err) {
      console.error(err);
      toast.add({ title: "Failed to load instructions", type: "error" });
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSave = async () => {
    if (saving) return;
    setSaving(true);
    try {
      await projectWorkspaceApi.updateInstructions(projectId, content);
      setSavedContent(content);
      lastSavedRef.current = content;
      toast.add({ title: "Instructions saved", type: "success" });
    } catch (err) {
      console.error(err);
      toast.add({ title: "Failed to save instructions", type: "error" });
    } finally {
      setSaving(false);
    }
  };

  const handleRestore = async (version: Version) => {
    setRestoreTarget(version);
  };

  const confirmRestore = async () => {
    if (!restoreTarget) return;
    setRestoring(true);
    try {
      await projectWorkspaceApi.restoreInstructionVersion(projectId, restoreTarget.id);
      setContent(restoreTarget.content);
      setSavedContent(restoreTarget.content);
      lastSavedRef.current = restoreTarget.content;
      toast.add({ title: `Restored version ${restoreTarget.version}`, type: "success" });
      fetchData();
    } catch (err) {
      console.error(err);
      toast.add({ title: "Failed to restore version", type: "error" });
    } finally {
      setRestoring(false);
      setRestoreTarget(null);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setContent(e.target.value);
    
    if (autosaveTimerRef.current) {
      clearTimeout(autosaveTimerRef.current);
    }
    autosaveTimerRef.current = setTimeout(() => {
      if (content !== lastSavedRef.current) {
        handleSave();
      }
    }, 2000);
  };

  const hasUnsavedChanges = content !== savedContent;

  useEffect(() => {
    return () => {
      if (autosaveTimerRef.current) {
        clearTimeout(autosaveTimerRef.current);
      }
    };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-4 shrink-0">
        <div>
          <h2 className="text-xl font-semibold">Project Instructions</h2>
          <p className="text-zinc-500 text-sm">Guidelines and context for this project</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={hasUnsavedChanges ? "default" : "secondary"} className={hasUnsavedChanges ? "bg-yellow-100 text-yellow-700" : ""}>
            {hasUnsavedChanges ? <><AlertCircle className="mr-1 h-3 w-3 inline" /> Unsaved changes</> : <><CheckCircle className="mr-1 h-3 w-3 inline" /> Saved</>}
          </Badge>
          <Button variant="outline" onClick={() => setShowHistory(!showHistory)}>
            <Clock className="mr-2 h-4 w-4" />
            History
          </Button>
          <Button onClick={handleSave} disabled={saving || !hasUnsavedChanges}>
            <Save className="mr-2 h-4 w-4" />
            {saving ? "Saving..." : "Save"}
          </Button>
        </div>
      </div>

      <Card className="flex-1 flex flex-col min-h-0">
        <CardHeader className="border-b shrink-0 py-3">
          <CardTitle className="text-sm">Instructions Editor</CardTitle>
        </CardHeader>
        <CardContent className="flex-1 p-0 min-h-0">
          <textarea
            value={content}
            onChange={handleChange}
            placeholder="Enter project instructions, guidelines, context, and requirements... Supports Markdown."
            className="w-full h-full min-h-[300px] resize-none border-0 focus:ring-0 bg-transparent p-4 font-mono text-sm leading-relaxed"
            spellCheck={false}
          />
        </CardContent>
      </Card>

      {showHistory && versions.length > 0 && (
        <Card className="mt-4 shrink-0">
          <CardHeader className="py-3">
            <h3 className="text-lg font-medium">Version History</h3>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-64 overflow-auto">
              {versions.map((version) => (
                <div key={version.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div>
                    <p className="font-medium">Version {version.version}</p>
                    <p className="text-sm text-zinc-500">Updated {formatDate(version.created_at)}</p>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => handleRestore(version)}>
                    <RotateCcw className="mr-2 h-4 w-4" />
                    Restore
                  </Button>
                </div>
              ))}
            </div>
            {versions.length === 0 && (
              <p className="text-zinc-500 text-center py-4">No version history yet</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Restore confirmation */}
      <Sheet open={!!restoreTarget} onOpenChange={(o) => { if (!o) setRestoreTarget(null); }}>
        <SheetContent side="bottom" className="mx-auto max-w-md rounded-t-2xl">
          <SheetHeader>
            <SheetTitle>Restore version {restoreTarget?.version}?</SheetTitle>
            <SheetDescription>This will replace the current content with an older version.</SheetDescription>
          </SheetHeader>
          <SheetFooter>
            <SheetClose render={<Button variant="outline" />}>Cancel</SheetClose>
            <Button onClick={confirmRestore} disabled={restoring}>
              {restoring && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Restore
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </div>
  );
}
