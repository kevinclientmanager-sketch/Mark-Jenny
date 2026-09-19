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
import { browserApi, BrowserCapability } from "@/lib/api/browser";
import {
  Globe, Loader2, Plus, Trash2, ExternalLink, RefreshCw, Search, Monitor
} from "lucide-react";

export default function BrowserPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [capability, setCapability] = useState<BrowserCapability | null>(null);
  const [sessions, setSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [navigating, setNavigating] = useState(false);
  const [url, setUrl] = useState("https://");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any>(null);
  const [pageContent, setPageContent] = useState<string | null>(null);
  const [activeSession, setActiveSession] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const [cap, sess] = await Promise.all([
        browserApi.capability().catch(() => null),
        browserApi.listSessions().catch(() => []),
      ]);
      setCapability(cap);
      setSessions(Array.isArray(sess) ? sess : []);
      if (!activeSession && Array.isArray(sess) && sess.length > 0) {
        setActiveSession(sess[0].session_id);
      }
    } catch {}
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleCreateSession = async () => {
    try {
      const res = await browserApi.createSession(true);
      toast.add({ title: "Session created", type: "success" });
      setActiveSession(res.session_id);
      load();
    } catch { toast.add({ title: "Failed to create session", type: "error" }); }
  };

  const handleNavigate = async () => {
    if (!url.trim()) return;
    setNavigating(true);
    try {
      await browserApi.navigate({ url, session_id: activeSession || undefined, persistent: true });
      toast.add({ title: "Navigated", type: "success" });
      if (activeSession) {
        const content = await browserApi.read(activeSession);
        setPageContent(typeof content === "string" ? content : JSON.stringify(content, null, 2));
      }
    } catch { toast.add({ title: "Navigation failed", type: "error" }); }
    finally { setNavigating(false); }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setNavigating(true);
    try {
      const res = await browserApi.search({ query: searchQuery, session_id: activeSession || undefined });
      setSearchResults(res);
      toast.add({ title: "Search complete", type: "success" });
    } catch { toast.add({ title: "Search failed", type: "error" }); }
    finally { setNavigating(false); }
  };

  const handleCloseSession = async (id: string) => {
    try {
      await browserApi.closeSession(id);
      toast.add({ title: "Session closed", type: "success" });
      if (activeSession === id) setActiveSession(null);
      load();
    } catch { toast.add({ title: "Failed to close session", type: "error" }); }
  };

  const handleReadPage = async () => {
    if (!activeSession) return;
    try {
      const content = await browserApi.read(activeSession);
      setPageContent(typeof content === "string" ? content : JSON.stringify(content, null, 2));
    } catch { toast.add({ title: "Failed to read page", type: "error" }); }
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
                <h1 className="text-2xl font-semibold flex items-center gap-2"><Globe className="h-6 w-6" /> Browser</h1>
                <p className="text-sm text-zinc-500 mt-1">Manage persistent browser sessions for agent web access.</p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={load}><RefreshCw className="h-4 w-4" /></Button>
                <Button onClick={handleCreateSession} className="gap-2">
                  <Plus className="h-4 w-4" /> New Session
                </Button>
              </div>
            </div>

            {capability && (
              <Card className="mb-4">
                <CardContent className="p-3 flex items-center gap-4 text-sm">
                  <Badge variant={capability.playwright_installed ? "default" : "destructive"}>
                    {capability.playwright_installed ? "Playwright Installed" : "Playwright Missing"}
                  </Badge>
                  <span className="text-zinc-500">Status: {capability.capability?.status || "unknown"}</span>
                  <span className="text-zinc-500">Sessions: {capability.sessions_active}</span>
                </CardContent>
              </Card>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-2 space-y-4">
                <Card>
                  <CardContent className="p-4">
                    <div className="flex gap-2 mb-3">
                      <Input placeholder="Enter URL" value={url} onChange={e => setUrl(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && handleNavigate()} className="flex-1" />
                      <Button onClick={handleNavigate} disabled={navigating || !url.trim()}>
                        {navigating ? <Loader2 className="h-4 w-4 animate-spin" /> : <ExternalLink className="h-4 w-4" />}
                      </Button>
                      <Button variant="outline" onClick={handleReadPage} disabled={!activeSession}>
                        <Monitor className="h-4 w-4" />
                      </Button>
                    </div>
                    <div className="flex gap-2">
                      <Input placeholder="Search the web..." value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && handleSearch()} className="flex-1" />
                      <Button variant="outline" onClick={handleSearch} disabled={navigating || !searchQuery.trim()}>
                        <Search className="h-4 w-4" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>

                {pageContent && (
                  <Card>
                    <CardHeader><CardTitle className="text-base">Page Content</CardTitle></CardHeader>
                    <CardContent>
                      <pre className="text-xs whitespace-pre-wrap max-h-96 overflow-auto bg-zinc-50 dark:bg-zinc-800 p-3 rounded-lg">
                        {pageContent}
                      </pre>
                    </CardContent>
                  </Card>
                )}

                {searchResults && (
                  <Card>
                    <CardHeader><CardTitle className="text-base">Search Results</CardTitle></CardHeader>
                    <CardContent>
                      <pre className="text-xs whitespace-pre-wrap max-h-96 overflow-auto bg-zinc-50 dark:bg-zinc-800 p-3 rounded-lg">
                        {JSON.stringify(searchResults, null, 2)}
                      </pre>
                    </CardContent>
                  </Card>
                )}
              </div>

              <div>
                <Card>
                  <CardHeader><CardTitle className="text-base">Sessions</CardTitle></CardHeader>
                  <CardContent>
                    {loading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : sessions.length === 0 ? (
                      <p className="text-sm text-zinc-500">No active sessions.</p>
                    ) : (
                      <div className="space-y-2">
                        {sessions.map((s: any) => (
                          <div key={s.session_id} className={`p-2 rounded-lg text-sm cursor-pointer transition-colors ${
                            activeSession === s.session_id ? "bg-blue-50 dark:bg-blue-900/20 border border-blue-200" : "bg-zinc-50 dark:bg-zinc-800 hover:bg-zinc-100"
                          }`} onClick={() => setActiveSession(s.session_id)}>
                            <div className="flex items-center justify-between">
                              <span className="font-mono text-xs truncate">{s.session_id}</span>
                              <Button variant="ghost" size="sm" onClick={e => { e.stopPropagation(); handleCloseSession(s.session_id); }}>
                                <Trash2 className="h-3 w-3 text-red-500" />
                              </Button>
                            </div>
                            <div className="flex items-center gap-2 mt-1 text-xs text-zinc-400">
                              <Badge variant={s.persistent ? "default" : "secondary"} className="text-xs">
                                {s.persistent ? "Persistent" : "Temporary"}
                              </Badge>
                              {s.created_at && <span>{new Date(s.created_at).toLocaleTimeString()}</span>}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
          </main>
        </div>
      </div>
    </ProtectedLayout>
  );
}
