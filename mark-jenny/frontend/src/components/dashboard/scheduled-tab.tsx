"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Plus, MoreHorizontal, Loader2, Clock, Calendar } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { schedulesApi, Schedule, ScheduleRun, UpcomingSchedule } from "@/lib/api/schedules";
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter, SheetClose,
} from "@/components/ui/sheet";
import { toast } from "@/components/ui/toast";

export function ScheduledTab() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"runs" | "scheduled">("runs");
  const [runs, setRuns] = useState<ScheduleRun[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [upcoming, setUpcoming] = useState<UpcomingSchedule[]>([]);
  const [loadingRuns, setLoadingRuns] = useState(true);
  const [loadingSchedules, setLoadingSchedules] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const [deleteTarget, setDeleteTarget] = useState<Schedule | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchRuns = useCallback(async () => {
    setLoadingRuns(true);
    try {
      // Fetch run history from the schedules API
      const allRuns: any[] = [];
      for (const schedule of schedules) {
        try {
          const runs = await schedulesApi.listRuns(schedule.id, 1, 10);
          allRuns.push(...runs.map(r => ({ ...r, schedule_title: schedule.title })));
        } catch {}
      }
      allRuns.sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime());
      setRuns(allRuns);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingRuns(false);
    }
  }, [schedules]);

  const fetchSchedules = useCallback(async () => {
    setLoadingSchedules(true);
    setError(null);
    try {
      const response = await schedulesApi.list({ page, page_size: pageSize });
      setSchedules(response.schedules);
    } catch (err) {
      setError("Failed to load schedules");
      console.error(err);
    } finally {
      setLoadingSchedules(false);
    }
  }, [page, pageSize]);

  const fetchUpcoming = useCallback(async () => {
    try {
      const data = await schedulesApi.getUpcoming(10);
      setUpcoming(data);
    } catch (err) {
      console.error(err);
    }
  }, []);

  useEffect(() => {
    fetchSchedules();
    fetchUpcoming();
  }, [fetchSchedules, fetchUpcoming]);

  useEffect(() => {
    if (activeTab === "runs") {
      fetchRuns();
    }
  }, [activeTab, fetchRuns]);

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "Never";
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return "N/A";
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (mins > 0) return `${mins}m ${secs}s`;
    return `${secs}s`;
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "COMPLETED":
      case "SUCCESS":
        return <Badge variant="default">Completed</Badge>;
      case "FAILED":
      case "ERROR":
        return <Badge variant="destructive">Failed</Badge>;
      case "RUNNING":
      case "IN_PROGRESS":
        return <Badge variant="default" className="bg-blue-100 text-blue-700">Running</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const handleCreateSchedule = () => {
    router.push("/scheduled");
  };

  const handlePause = async (id: number) => {
    try {
      await schedulesApi.pause(id);
      fetchSchedules();
      toast.add({ title: "Schedule paused", type: "success" });
    } catch (err) {
      toast.add({ title: "Couldn't pause schedule", type: "error" });
      console.error(err);
    }
  };

  const handleResume = async (id: number) => {
    try {
      await schedulesApi.resume(id);
      fetchSchedules();
      toast.add({ title: "Schedule resumed", type: "success" });
    } catch (err) {
      toast.add({ title: "Couldn't resume schedule", type: "error" });
      console.error(err);
    }
  };

  const handleDuplicate = async (id: number) => {
    try {
      await schedulesApi.duplicate(id);
      fetchSchedules();
      toast.add({ title: "Schedule duplicated", type: "success" });
    } catch (err) {
      toast.add({ title: "Duplicate failed", type: "error" });
      console.error(err);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await schedulesApi.delete(deleteTarget.id);
      fetchSchedules();
      toast.add({ title: "Schedule deleted", type: "success" });
    } catch (err) {
      toast.add({ title: "Couldn't delete schedule", type: "error" });
      console.error(err);
    } finally {
      setDeleting(false);
      setDeleteTarget(null);
    }
  };

  if (loadingSchedules && activeTab === "scheduled") {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-zinc-500">
        <p className="mb-4 text-red-600">{error}</p>
        <Button onClick={fetchSchedules}>Retry</Button>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex flex-col items-center gap-3 mb-4">
        <h3 className="text-lg font-medium">Scheduled Tasks</h3>
        <Tabs defaultValue="runs" onValueChange={setActiveTab} className="w-full flex flex-col items-center">
          <TabsList className="grid w-full grid-cols-2 mb-4 max-w-xs">
            <TabsTrigger value="runs">Runs</TabsTrigger>
            <TabsTrigger value="scheduled">Scheduled</TabsTrigger>
          </TabsList>

        <TabsContent value="runs" className="flex-1 overflow-auto">
          {loadingRuns ? (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
          ) : runs.length === 0 ? (
            <div className="flex-1 flex items-center justify-center text-zinc-500">
              No runs yet
            </div>
          ) : (
            <div className="space-y-3">
              {runs.map((run) => (
                <Card key={run.id}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h4 className="font-medium">{run.task_id ? `Task #${run.task_id}` : "Unknown Task"}</h4>
                        <div className="flex items-center gap-4 text-sm text-zinc-500 mt-1">
                          <span><Clock className="mr-1 h-3 w-3 inline" /> {formatDate(run.started_at)}</span>
                          <span>{formatDuration(run.duration_seconds)}</span>
                        </div>
                        {run.error && (
                          <p className="text-sm text-red-600 mt-1">Error: {run.error}</p>
                        )}
                      </div>
                      {getStatusBadge(run.status)}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="scheduled" className="flex-1 overflow-auto">
          {schedules.length === 0 && upcoming.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-zinc-500">
              <Calendar className="h-12 w-12 mx-auto mb-3 text-zinc-300" />
              <p className="mb-4">No scheduled tasks yet</p>
              <Button onClick={handleCreateSchedule}>
                <Plus className="mr-2 h-4 w-4" />
                New Scheduled Task
              </Button>
            </div>
          ) : (
            <>
              {upcoming.length > 0 && (
                <div className="mb-6">
                  <h4 className="font-medium text-zinc-700 dark:text-zinc-300 mb-3">Upcoming</h4>
                  <div className="space-y-2">
                    {upcoming.map((task) => (
                      <Card key={task.id}>
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <h4 className="font-medium">{task.title}</h4>
                                <Badge variant={task.status === "ACTIVE" ? "default" : "secondary"}>
                                  {task.status}
                                </Badge>
                              </div>
                              <div className="flex items-center gap-4 text-sm text-zinc-500 mt-2">
                                <span><Calendar className="mr-1 h-3 w-3 inline" /> Next: {task.next_execution ? new Date(task.next_execution).toLocaleString() : "Not scheduled"}</span>
                                <span>{task.frequency}</span>
                                {task.project && <span>{task.project}</span>}
                                {task.agent && <span>{task.agent}</span>}
                              </div>
                              <div className="flex flex-wrap gap-2 text-xs text-zinc-500 mt-1">
                                {task.connectors?.map((c) => (
                                  <Badge variant="outline" key={c}>Connector #{c}</Badge>
                                ))}
                              </div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              )}
              <div className="space-y-3">
                {schedules.map((task) => (
                  <Card key={task.id}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <h4 className="font-medium">{task.title}</h4>
                            <Badge variant={task.is_active ? "default" : "secondary"}>
                              {task.is_active ? "Active" : "Paused"}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-4 text-sm text-zinc-500 mt-2">
                            <span><Calendar className="mr-1 h-3 w-3 inline" /> Next: {formatDate(task.next_run_at)}</span>
                            <span>{task.frequency}</span>
                            {task.project_name && <span>{task.project_name}</span>}
                            {task.agent_name && <span>{task.agent_name}</span>}
                          </div>
                          <div className="flex flex-wrap gap-2 text-xs text-zinc-500 mt-1">
                            {task.connectors?.map((c) => (
                              <Badge variant="outline" key={c}>#{c}</Badge>
                            ))}
                          </div>
                        </div>
                        <DropdownMenu>
                          <DropdownMenuTrigger>
                            <Button variant="ghost" size="icon">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => router.push("/scheduled")}>Edit</DropdownMenuItem>
                            <DropdownMenuItem onClick={() => task.is_active ? handlePause(task.id) : handleResume(task.id)}>
                              {task.is_active ? "Pause" : "Resume"}
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleDuplicate(task.id)}>Duplicate</DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem className="text-red-600" onClick={() => setDeleteTarget(task)}>Delete</DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </>
          )}
        </TabsContent>
        </Tabs>
      </div>

      {/* Delete confirmation */}
      <Sheet open={!!deleteTarget} onOpenChange={(o) => { if (!o) setDeleteTarget(null); }}>
        <SheetContent side="bottom" className="mx-auto max-w-md rounded-t-2xl">
          <SheetHeader>
            <SheetTitle>Delete this schedule?</SheetTitle>
            <SheetDescription>“{deleteTarget?.title || "Schedule"}” will be permanently removed.</SheetDescription>
          </SheetHeader>
          <SheetFooter>
            <SheetClose render={<Button variant="outline" />}>Cancel</SheetClose>
            <Button variant="destructive" onClick={confirmDelete} disabled={deleting}>
              {deleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Delete
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </div>
  );
}