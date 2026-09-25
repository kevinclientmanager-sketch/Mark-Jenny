"use client";
import { useState, useEffect } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ProtectedLayout } from "@/components/layout/protected-layout";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Search, Library as LibraryIcon, Globe, AppWindow, Loader2,
  ExternalLink, Rocket, CheckCircle2, Clock,
} from "lucide-react";
import { generativeApi, type BuiltItem } from "@/lib/api/generative";
import { toast } from "@/components/ui/toast";

function BuildCard({ item }: { item: BuiltItem }) {
  const Icon = item.kind === "website" ? Globe : AppWindow;
  const openUrl = item.deploy_url || item.preview_url || item.repo_url;
  return (
    <Card className="overflow-hidden hover:shadow-md transition-shadow">
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className="h-10 w-10 shrink-0 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
            <Icon className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium truncate">{item.name}</p>
            {item.description && <p className="text-xs text-zinc-500 truncate mt-0.5">{item.description}</p>}
            <div className="flex flex-wrap items-center gap-1.5 mt-2">
              <Badge variant="outline" className="text-[11px]">{item.kind}</Badge>
              {item.framework && <Badge variant="outline" className="text-[11px]">{item.framework}</Badge>}
              {item.language && <Badge variant="outline" className="text-[11px]">{item.language}</Badge>}
              {item.status && (
                <Badge variant={item.status === "READY" || item.status === "DEPLOYED" || item.status === "COMPLETED" ? "default" : "secondary"} className="text-[11px]">
                  {item.status}
                </Badge>
              )}
            </div>
          </div>
        </div>
        <div className="flex gap-2 mt-3">
          {openUrl ? (
            <Button size="sm" className="flex-1" onClick={() => window.open(openUrl!, "_blank", "noopener,noreferrer")}>
              <ExternalLink className="mr-1.5 h-3.5 w-3.5" /> Open
            </Button>
          ) : (
            <Button size="sm" variant="outline" className="flex-1" disabled>No link yet</Button>
          )}
          {item.deploy_url && item.deploy_url !== openUrl && (
            <Button size="sm" variant="outline" onClick={() => window.open(item.deploy_url!, "_blank", "noopener,noreferrer")}>
              <Rocket className="mr-1.5 h-3.5 w-3.5" /> Live
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default function LibraryPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [websites, setWebsites] = useState<BuiltItem[]>([]);
  const [apps, setApps] = useState<BuiltItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const lib = await generativeApi.library();
        setWebsites(lib.websites || []);
        setApps(lib.apps || []);
      } catch {
        toast.add({ title: "Couldn't load library", type: "error" });
      } finally { setLoading(false); }
    })();
  }, []);

  const q = search.trim().toLowerCase();
  const match = (i: BuiltItem) => !q || (i.name || "").toLowerCase().includes(q) || (i.description || "").toLowerCase().includes(q);
  const sites = websites.filter(match);
  const appl = apps.filter(match);

  return (
    <ProtectedLayout>
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex">
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <div className={`flex-1 flex flex-col min-w-0 transition-all ${sidebarOpen ? "ml-64" : "ml-16"}`}>
          <Header />
          <main className="flex-1 overflow-auto p-4 lg:p-6">
            <div className="mx-auto max-w-6xl space-y-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <LibraryIcon className="h-5 w-5 text-blue-600" />
                  <h1 className="text-2xl font-semibold">Library</h1>
                  <Badge variant="outline">finished builds</Badge>
                </div>
                <div className="relative w-64">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
                  <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search builds…" className="pl-8" />
                </div>
              </div>
              <p className="text-sm text-zinc-500 -mt-3">Every app and website Mark finishes lives here — open them anytime. Working drafts stay in Projects.</p>

              {loading ? (
                <div className="flex justify-center p-12"><Loader2 className="h-6 w-6 animate-spin text-zinc-400" /></div>
              ) : sites.length === 0 && appl.length === 0 ? (
                <Card><CardContent className="p-12 text-center">
                  <CheckCircle2 className="h-12 w-12 mx-auto mb-3 text-zinc-300" />
                  <p className="font-medium">No finished builds yet</p>
                  <p className="text-sm text-zinc-500 mt-1">Ask Mark to build a website or an app — finished work appears here automatically.</p>
                </CardContent></Card>
              ) : (
                <>
                  {sites.length > 0 && (
                    <section>
                      <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 mb-3 flex items-center gap-1.5"><Globe className="h-4 w-4" /> Websites ({sites.length})</h2>
                      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                        {sites.map((w) => <BuildCard key={`w-${w.id}`} item={w} />)}
                      </div>
                    </section>
                  )}
                  {appl.length > 0 && (
                    <section>
                      <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 mb-3 flex items-center gap-1.5"><AppWindow className="h-4 w-4" /> Apps ({appl.length})</h2>
                      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                        {appl.map((a) => <BuildCard key={`a-${a.id}`} item={a} />)}
                      </div>
                    </section>
                  )}
                  {q && sites.length === 0 && appl.length === 0 && (
                    <p className="text-sm text-zinc-500 text-center py-8 flex items-center justify-center gap-2"><Clock className="h-4 w-4" /> Nothing matches “{search}”.</p>
                  )}
                </>
              )}
            </div>
          </main>
        </div>
      </div>
    </ProtectedLayout>
  );
}
