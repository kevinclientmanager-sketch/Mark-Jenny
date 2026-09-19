"use client";
import { useState, useEffect } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ProtectedLayout } from "@/components/layout/protected-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/toast";
import { api } from "@/lib/api/client";
import {
  Shield, Users, Database, Activity, AlertTriangle, RefreshCw, Loader2,
  Trash2, Ban, CheckCircle, XCircle, Settings
} from "lucide-react";

interface SystemStats {
  total_users: number;
  total_projects: number;
  total_tasks: number;
  total_files: number;
  active_schedules: number;
  db_size_mb: number;
}

interface User {
  id: number;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

export default function AdminPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"stats" | "users" | "blacklist">("stats");
  const [blacklistEmail, setBlacklistEmail] = useState("");
  const [blacklist, setBlacklist] = useState<string[]>([]);
  const [featureFlags, setFeatureFlags] = useState<Record<string, boolean>>({});

  const load = async () => {
    setLoading(true);
    try {
      const [s, u] = await Promise.all([
        api.get<SystemStats>("/admin/system-stats"),
        api.get<{ users: User[] }>("/admin/users?page_size=100"),
      ]);
      setStats(s);
      setUsers(u.users);
    } catch { toast.add({ title: "Failed to load admin data", type: "error" }); }
    finally { setLoading(false); }
  };

  const loadBlacklist = async () => {
    try {
      const bl = await api.get<string[]>("/admin/blacklist");
      setBlacklist(bl);
    } catch {}
  };

  const loadFeatureFlags = async () => {
    try {
      const flags = await api.get<Record<string, boolean>>("/admin/features");
      setFeatureFlags(flags);
    } catch {}
  };

  useEffect(() => { load(); loadBlacklist(); loadFeatureFlags(); }, []);

  const handleBlacklist = async () => {
    if (!blacklistEmail.trim()) return;
    try {
      await api.post("/admin/blacklist", { email: blacklistEmail });
      toast.add({ title: "Email blacklisted", type: "success" });
      setBlacklistEmail("");
      loadBlacklist();
    } catch { toast.add({ title: "Failed to blacklist", type: "error" }); }
  };

  const handleRemoveBlacklist = async (email: string) => {
    try {
      await api.delete(`/admin/blacklist/${encodeURIComponent(email)}`);
      toast.add({ title: "Removed from blacklist", type: "success" });
      loadBlacklist();
    } catch { toast.add({ title: "Failed to remove", type: "error" }); }
  };

  const handleToggleFeature = async (key: string) => {
    try {
      const newVal = !featureFlags[key];
      await api.patch("/admin/features", { key, enabled: newVal });
      setFeatureFlags(prev => ({ ...prev, [key]: newVal }));
      toast.add({ title: `${key} ${newVal ? "enabled" : "disabled"}`, type: "success" });
    } catch { toast.add({ title: "Failed to toggle feature", type: "error" }); }
  };

  const handleDeactivateUser = async (id: number) => {
    if (!confirm("Deactivate this user?")) return;
    try {
      await api.patch(`/admin/users/${id}`, { is_active: false });
      toast.add({ title: "User deactivated", type: "success" });
      load();
    } catch { toast.add({ title: "Failed to deactivate", type: "error" }); }
  };

  const tabs = [
    { id: "stats" as const, label: "System", icon: Activity },
    { id: "users" as const, label: "Users", icon: Users },
    { id: "blacklist" as const, label: "Blacklist", icon: Ban },
  ];

  return (
    <ProtectedLayout>
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex">
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <div className={`flex-1 flex flex-col min-w-0 transition-all ${sidebarOpen ? "ml-64" : "ml-16"}`}>
          <Header />
          <main className="flex-1 p-6 overflow-auto max-w-6xl mx-auto w-full">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-2xl font-semibold flex items-center gap-2"><Shield className="h-6 w-6" /> Admin Panel</h1>
                <p className="text-sm text-zinc-500 mt-1">System management and user administration.</p>
              </div>
              <Button variant="outline" onClick={load} className="gap-2">
                <RefreshCw className="h-4 w-4" /> Refresh
              </Button>
            </div>

            <div className="flex gap-1 mb-6 border-b">
              {tabs.map(t => (
                <button key={t.id} onClick={() => setActiveTab(t.id)}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === t.id ? "border-zinc-900 text-zinc-900 dark:border-zinc-100 dark:text-zinc-100" : "border-transparent text-zinc-500 hover:text-zinc-700"
                  }`}>
                  <t.icon className="h-4 w-4" /> {t.label}
                </button>
              ))}
            </div>

            {loading ? (
              <div className="flex justify-center p-12"><Loader2 className="h-6 w-6 animate-spin" /></div>
            ) : activeTab === "stats" ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {stats && [
                  { label: "Users", value: stats.total_users, icon: Users, color: "text-blue-600" },
                  { label: "Projects", value: stats.total_projects, icon: Database, color: "text-purple-600" },
                  { label: "Tasks", value: stats.total_tasks, icon: Activity, color: "text-emerald-600" },
                  { label: "Files", value: stats.total_files, icon: Database, color: "text-amber-600" },
                  { label: "Active Schedules", value: stats.active_schedules, icon: Settings, color: "text-cyan-600" },
                  { label: "DB Size", value: `${stats.db_size_mb?.toFixed(1) || 0} MB`, icon: Database, color: "text-zinc-600" },
                ].map((s, i) => (
                  <Card key={i}>
                    <CardContent className="p-4">
                      <div className="flex items-center gap-3">
                        <div className={`h-10 w-10 rounded-lg bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center`}>
                          <s.icon className={`h-5 w-5 ${s.color}`} />
                        </div>
                        <div>
                          <p className="text-2xl font-bold">{s.value}</p>
                          <p className="text-xs text-zinc-500">{s.label}</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
                <Card className="md:col-span-2 lg:col-span-3">
                  <CardHeader><CardTitle className="text-base">Feature Flags</CardTitle></CardHeader>
                  <CardContent>
                    {Object.keys(featureFlags).length === 0 ? (
                      <p className="text-sm text-zinc-500">No feature flags configured.</p>
                    ) : (
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                        {Object.entries(featureFlags).map(([key, enabled]) => (
                          <button key={key} onClick={() => handleToggleFeature(key)}
                            className={`flex items-center gap-2 p-2 rounded-lg text-sm text-left transition-colors ${
                              enabled ? "bg-green-50 text-green-700 dark:bg-green-900/20" : "bg-zinc-50 text-zinc-500 dark:bg-zinc-800"
                            }`}>
                            {enabled ? <CheckCircle className="h-4 w-4 shrink-0" /> : <XCircle className="h-4 w-4 shrink-0" />}
                            <span className="truncate">{key}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            ) : activeTab === "users" ? (
              <div className="space-y-2">
                {users.length === 0 ? (
                  <Card className="p-8 text-center text-zinc-500">No users found.</Card>
                ) : users.map(u => (
                  <Card key={u.id}>
                    <CardContent className="p-4 flex items-center justify-between">
                      <div>
                        <p className="font-medium">{u.email}</p>
                        <div className="flex items-center gap-2 text-xs text-zinc-500 mt-1">
                          <Badge variant={u.role === "ADMIN" ? "default" : "secondary"} className="text-xs">{u.role}</Badge>
                          <Badge variant={u.is_active ? "default" : "destructive"} className="text-xs">
                            {u.is_active ? "Active" : "Inactive"}
                          </Badge>
                          <span>Joined: {new Date(u.created_at).toLocaleDateString()}</span>
                          {u.last_login && <span>Last login: {new Date(u.last_login).toLocaleDateString()}</span>}
                        </div>
                      </div>
                      {u.is_active && (
                        <Button variant="ghost" size="sm" onClick={() => handleDeactivateUser(u.id)}>
                          <Ban className="h-4 w-4 text-red-500" />
                        </Button>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex gap-2">
                  <Input placeholder="Enter email to blacklist" value={blacklistEmail} onChange={e => setBlacklistEmail(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && handleBlacklist()} className="flex-1" />
                  <Button onClick={handleBlacklist} disabled={!blacklistEmail.trim()}>Blacklist</Button>
                </div>
                {blacklist.length === 0 ? (
                  <Card className="p-8 text-center text-zinc-500">No blacklisted emails.</Card>
                ) : (
                  <div className="space-y-2">
                    {blacklist.map(email => (
                      <Card key={email}>
                        <CardContent className="p-3 flex items-center justify-between">
                          <span className="text-sm">{email}</span>
                          <Button variant="ghost" size="sm" onClick={() => handleRemoveBlacklist(email)}>
                            <Trash2 className="h-4 w-4 text-red-500" />
                          </Button>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            )}
          </main>
        </div>
      </div>
    </ProtectedLayout>
  );
}
