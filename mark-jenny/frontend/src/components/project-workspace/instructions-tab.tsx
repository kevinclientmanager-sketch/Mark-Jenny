"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Save, RotateCcw, Clock, Loader2, AlertCircle, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
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

  useEffect(() => { fetchData(); }, [fetchData]);

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
        <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b bg-white dark:bg-zinc-900 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-zinc-500">Instructions Editor</span>
          <Badge variant={hasUnsavedChanges ? "default" : "secondary"} className={`text-[10px] px-1.5 py-0 ${hasUnsavedChanges ? "bg-yellow-100 text-yellow-700" : ""}`}>
            {hasUnsavedChanges ? <><AlertCircle className="mr-1 h-2.5 w-2.5 inline" /> Unsaved</> : <><CheckCircle className="mr-1 h-2.5 w-2.5 inline" /> Saved</>}
          </Badge>
        </div>
        <div className="flex items-center gap-1.5">
          <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => setShowHistory(!showHistory)}>
            <Clock className="mr-1 h-3 w-3" />
            History
          </Button>
          <Button size="sm" className="h-7 text-xs" onClick={handleSave} disabled={saving || !hasUnsavedChanges}>
            <Save className="mr-1 h-3 w-3" />
            {saving ? "Saving..." : "Save"}
          </Button>
        </div>
      </div>

      {/* Editor — fills remaining space */}
      <div className="flex-1 min-h-0">
        <textarea
          value={content}
          onChange={handleChange}
          placeholder="Enter project instructions, guidelines, context, and requirements... Supports Markdown."
          className="w-full h-full resize-none border-0 focus:ring-0 bg-white dark:bg-zinc-900 p-4 font-mono text-sm leading-relaxed"
          spellCheck={false}
        />
      </div>

      {/* History panel — slides in from bottom */}
      {showHistory && versions.length > 0 && (
        <div className="shrink-0 border-t bg-white dark:bg-zinc-900 max-h-48 overflow-auto">
          <div className="px-4 py-2">
            <p className="text-xs font-medium text-zinc-500 mb-2">Version History</p>
            <div className="space-y-1">
              {versions.map((version) => (
                <div key={version.id} className="flex items-center justify-between p-2 rounded-lg border text-xs">
                  <div>
                    <span className="font-medium">v{version.version}</span>
                    <span className="text-zinc-400 ml-2">{formatDate(version.created_at)}</span>
                  </div>
                  <Button variant="ghost" size="sm" className="h-6 text-[10px]" onClick={() => handleRestore(version)}>
                    <RotateCcw className="mr-1 h-2.5 w-2.5" /> Restore
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </div>
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
