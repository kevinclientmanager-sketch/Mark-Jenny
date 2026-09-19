"use client";
import { useState, useEffect } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ProtectedLayout } from "@/components/layout/protected-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/toast";
import { advancedFeaturesApi } from "@/lib/api/advancedFeatures";
import { Layers, Loader2, Eye, GitBranch } from "lucide-react";

export default function BlueprintsPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [blueprints, setBlueprints] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<any>(null);

  const load = async () => {
    setLoading(true);
    try {
      const bp = await advancedFeaturesApi.listBlueprints();
      setBlueprints(Array.isArray(bp) ? bp : []);
    } catch { toast.add({ title: "Failed to load blueprints", type: "error" }); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  return (
    <ProtectedLayout>
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex">
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <div className={`flex-1 flex flex-col min-w-0 transition-all ${sidebarOpen ? "ml-64" : "ml-16"}`}>
          <Header />
          <main className="flex-1 p-6 overflow-auto max-w-6xl mx-auto w-full">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-2xl font-semibold flex items-center gap-2"><Layers className="h-6 w-6" /> Blueprints</h1>
                <p className="text-sm text-zinc-500 mt-1">Reusable task templates auto-generated from completed work.</p>
              </div>
              <Button variant="outline" onClick={load}>Refresh</Button>
            </div>

            {loading ? (
              <div className="flex justify-center p-12"><Loader2 className="h-6 w-6 animate-spin" /></div>
            ) : blueprints.length === 0 ? (
              <Card className="p-12 text-center text-zinc-500">
                <Layers className="h-12 w-12 mx-auto mb-3 text-zinc-300" />
                <p className="text-lg font-medium">No blueprints yet</p>
                <p className="text-sm mt-1">Complete tasks to auto-generate reusable blueprints.</p>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {blueprints.map((bp: any, i: number) => (
                  <Card key={i} className="hover:shadow-md transition-shadow cursor-pointer"
                    onClick={() => setSelected(selected?.id === bp.id ? null : bp)}>
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-base">{bp.name || `Blueprint ${bp.id || i + 1}`}</CardTitle>
                        <Badge variant="secondary">{bp.status || "saved"}</Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-zinc-500 mb-2">{bp.description || bp.task_summary || "Auto-generated from completed task."}</p>
                      {bp.steps && (
                        <div className="text-xs text-zinc-400">{Array.isArray(bp.steps) ? bp.steps.length : "?"} steps</div>
                      )}
                      {bp.tags && (
                        <div className="flex gap-1 mt-2">
                          {(Array.isArray(bp.tags) ? bp.tags : []).slice(0, 3).map((t: string, j: number) => (
                            <Badge key={j} variant="outline" className="text-xs">{t}</Badge>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}

            {selected && (
              <Card className="mt-6">
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Eye className="h-4 w-4" /> {selected.name || "Blueprint Details"}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <pre className="text-sm whitespace-pre-wrap text-zinc-700 dark:text-zinc-300">
                    {JSON.stringify(selected, null, 2)}
                  </pre>
                </CardContent>
              </Card>
            )}
          </main>
        </div>
      </div>
    </ProtectedLayout>
  );
}
