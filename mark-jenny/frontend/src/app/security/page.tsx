"use client";
import { useState, useEffect } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ProtectedLayout } from "@/components/layout/protected-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/toast";
import { api } from "@/lib/api/client";
import {
  ShieldCheck, AlertTriangle, Lock, Eye, RefreshCw, Loader2, CheckCircle,
  XCircle, Clock, Zap, Activity
} from "lucide-react";

interface SecurityScan {
  id: string;
  status: string;
  issues: { severity: string; message: string; file: string }[];
  scanned_at: string;
}

interface RateLimitInfo {
  limit: number;
  remaining: number;
  reset_at: string;
}

export default function SecurityPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [scans, setScans] = useState<SecurityScan[]>([]);
  const [rateLimit, setRateLimit] = useState<RateLimitInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [activeTab, setActiveTab] = useState<"overview" | "scans" | "approvals">("overview");
  const [approvals, setApprovals] = useState<any[]>([]);

  const load = async () => {
    setLoading(true);
    try {
      const [rl, ap] = await Promise.all([
        api.get<RateLimitInfo>("/advanced/security/rate-limit").catch(() => null),
        api.get<any[]>("/advanced/approvals/pending").catch(() => []),
      ]);
      setRateLimit(rl);
      setApprovals(ap);
    } catch {}
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleScan = async () => {
    setScanning(true);
    try {
      const result = await api.post<SecurityScan>("/cybersecurity-agent/scan", {});
      setScans(prev => [result, ...prev]);
      toast.add({ title: "Security scan complete", description: `${result.issues?.length || 0} issues found.`, type: result.issues?.length ? "warning" : "success" });
    } catch { toast.add({ title: "Scan failed", type: "error" }); }
    finally { setScanning(false); }
  };

  const handleApprove = async (id: number) => {
    try {
      await api.post(`/advanced/approvals/${id}/approve`, { reason: "Approved from security panel" });
      toast.add({ title: "Approved", type: "success" });
      load();
    } catch { toast.add({ title: "Approval failed", type: "error" }); }
  };

  const handleReject = async (id: number) => {
    try {
      await api.post(`/advanced/approvals/${id}/reject`, { reason: "Rejected from security panel" });
      toast.add({ title: "Rejected", type: "success" });
      load();
    } catch { toast.add({ title: "Rejection failed", type: "error" }); }
  };

  const tabs = [
    { id: "overview" as const, label: "Overview", icon: ShieldCheck },
    { id: "scans" as const, label: "Scans", icon: Eye },
    { id: "approvals" as const, label: `Approvals (${approvals.length})`, icon: CheckCircle },
  ];

  const severityColor: Record<string, string> = {
    critical: "bg-red-100 text-red-700", high: "bg-orange-100 text-orange-700",
    medium: "bg-amber-100 text-amber-700", low: "bg-zinc-100 text-zinc-700",
  };

  return (
    <ProtectedLayout>
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex">
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <div className={`flex-1 flex flex-col min-w-0 transition-all ${sidebarOpen ? "ml-64" : "ml-16"}`}>
          <Header />
          <main className="flex-1 p-6 overflow-auto max-w-6xl mx-auto w-full">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-2xl font-semibold flex items-center gap-2"><ShieldCheck className="h-6 w-6" /> Security</h1>
                <p className="text-sm text-zinc-500 mt-1">Monitor system security and manage pending approvals.</p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={load} className="gap-2"><RefreshCw className="h-4 w-4" /> Refresh</Button>
                <Button onClick={handleScan} disabled={scanning} className="gap-2">
                  {scanning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Eye className="h-4 w-4" />} Run Scan
                </Button>
              </div>
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
            ) : activeTab === "overview" ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-lg bg-green-100 flex items-center justify-center">
                        <Lock className="h-5 w-5 text-green-600" />
                      </div>
                      <div>
                        <p className="text-2xl font-bold">{rateLimit?.remaining ?? "—"}</p>
                        <p className="text-xs text-zinc-500">API requests remaining</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-lg bg-amber-100 flex items-center justify-center">
                        <AlertTriangle className="h-5 w-5 text-amber-600" />
                      </div>
                      <div>
                        <p className="text-2xl font-bold">{approvals.length}</p>
                        <p className="text-xs text-zinc-500">Pending approvals</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-lg bg-blue-100 flex items-center justify-center">
                        <Activity className="h-5 w-5 text-blue-600" />
                      </div>
                      <div>
                        <p className="text-2xl font-bold">{scans.length}</p>
                        <p className="text-xs text-zinc-500">Scans performed</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card className="md:col-span-3">
                  <CardHeader><CardTitle className="text-base">Quick Security Actions</CardTitle></CardHeader>
                  <CardContent className="flex flex-wrap gap-2">
                    <Button variant="outline" size="sm" onClick={handleScan} disabled={scanning}>
                      {scanning ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Eye className="h-4 w-4 mr-2" />} Full Security Scan
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => setActiveTab("approvals")}>
                      <CheckCircle className="h-4 w-4 mr-2" /> Review Approvals ({approvals.length})
                    </Button>
                  </CardContent>
                </Card>
              </div>
            ) : activeTab === "scans" ? (
              scans.length === 0 ? (
                <Card className="p-12 text-center text-zinc-500">
                  <Eye className="h-12 w-12 mx-auto mb-3 text-zinc-300" />
                  <p className="text-lg font-medium">No scans yet</p>
                  <p className="text-sm mt-1">Run a security scan to check for vulnerabilities.</p>
                </Card>
              ) : (
                <div className="space-y-3">
                  {scans.map(scan => (
                    <Card key={scan.id}>
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between mb-2">
                          <Badge variant={scan.issues?.length ? "destructive" : "default"}>
                            {scan.issues?.length || 0} issues
                          </Badge>
                          <span className="text-xs text-zinc-500">{new Date(scan.scanned_at).toLocaleString()}</span>
                        </div>
                        {scan.issues?.length > 0 && (
                          <div className="space-y-1 mt-2">
                            {scan.issues.map((issue, i) => (
                              <div key={i} className="flex items-center gap-2 text-sm">
                                <Badge className={`text-xs ${severityColor[issue.severity] || ""}`}>{issue.severity}</Badge>
                                <span className="text-zinc-700">{issue.message}</span>
                                <span className="text-zinc-400 text-xs">({issue.file})</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )
            ) : (
              approvals.length === 0 ? (
                <Card className="p-12 text-center text-zinc-500">
                  <CheckCircle className="h-12 w-12 mx-auto mb-3 text-zinc-300" />
                  <p className="text-lg font-medium">No pending approvals</p>
                  <p className="text-sm mt-1">All caught up!</p>
                </Card>
              ) : (
                <div className="space-y-3">
                  {approvals.map((a: any) => (
                    <Card key={a.id}>
                      <CardContent className="p-4 flex items-center justify-between">
                        <div>
                          <p className="font-medium">{a.title || a.type || "Approval"}</p>
                          <p className="text-sm text-zinc-500">{a.description || a.reason || "No description"}</p>
                          <span className="text-xs text-zinc-400">{new Date(a.created_at).toLocaleString()}</span>
                        </div>
                        <div className="flex gap-2">
                          <Button size="sm" onClick={() => handleApprove(a.id)} className="bg-green-600 hover:bg-green-700">
                            <CheckCircle className="h-4 w-4 mr-1" /> Approve
                          </Button>
                          <Button size="sm" variant="destructive" onClick={() => handleReject(a.id)}>
                            <XCircle className="h-4 w-4 mr-1" /> Reject
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )
            )}
          </main>
        </div>
      </div>
    </ProtectedLayout>
  );
}


