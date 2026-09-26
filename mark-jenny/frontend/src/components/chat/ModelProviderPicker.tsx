"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Cpu, Check, Loader2, Search, Server, KeyRound, ArrowLeft, RefreshCw } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { modelsApi, ProviderCatalogEntry, AIModel } from "@/lib/api/models";

/**
 * Model + provider selector inside the composer.
 *
 * The trigger is a single arrow so it never steals room from the text field.
 * One menu holds the scrollable provider list; picking a provider slides into
 * a sub-list of that provider's models (also scrollable). API key entry lives
 * in a small dialog so typing is never intercepted by the menu.
 */
export default function ModelProviderPicker({ mode }: { mode?: string }) {
  const [catalog, setCatalog] = useState<ProviderCatalogEntry[]>([]);
  const [models, setModels] = useState<AIModel[]>([]);
  const [connected, setConnected] = useState<{ provider: string; has_key: boolean }[]>([]);
  const [provider, setProvider] = useState<string>("");
  const [model, setModel] = useState<string>("");
  const [view, setView] = useState<"providers" | "models">("providers");
  const [active, setActive] = useState<ProviderCatalogEntry | null>(null);
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // key dialog
  const [keyFor, setKeyFor] = useState<ProviderCatalogEntry | null>(null);
  const [keyDraft, setKeyDraft] = useState("");

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const [cat, ms, provs] = await Promise.all([
        modelsApi.providerCatalog().catch(() => ({ providers: [] as ProviderCatalogEntry[] })),
        modelsApi.listModels().catch(() => [] as AIModel[]),
        modelsApi.listProviders().catch(() => [] as any[]),
      ]);
      setCatalog(cat.providers || []);
      setModels(ms || []);
      setConnected((provs || []).map((p: any) => ({ provider: p.provider, has_key: p.has_key })));
      setErr(null);
    } catch (e: any) {
      setErr(e?.message || "Could not load providers");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    (async () => {
      try {
        const { api } = await import("@/lib/api/client");
        const prefs: any = await api.get("/settings/ai");
        if (prefs?.default_model) setModel(prefs.default_model);
        if (prefs?.default_provider) setProvider(prefs.default_provider);
      } catch {}
    })();
  }, []);

  const hasKey = useCallback(
    (id: string) => connected.some((c) => c.provider === id && c.has_key),
    [connected]
  );

  const persist = useCallback(async (nextProvider: string, nextModel: string) => {
    try {
      const { api } = await import("@/lib/api/client");
      if (nextProvider) {
        await api.post("/ai/providers", {
          provider: nextProvider,
          config: nextModel ? { model: nextModel } : undefined,
          is_default: true,
        });
      }
      await api.patch("/settings/ai", {
        default_model: nextModel || null,
        default_provider: nextProvider || null,
      });
      await load();
    } catch {
      /* selection stays local if the save fails */
    }
  }, [load]);

  const saveKey = async () => {
    if (!keyFor || !keyDraft.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      const { api } = await import("@/lib/api/client");
      const test = await api.post<any>("/ai/providers/test", {
        provider: keyFor.provider, api_key: keyDraft.trim(),
      });
      if (!test?.ok) {
        setErr(test?.detail || "The provider rejected that key.");
        return;
      }
      await api.post("/ai/providers", {
        provider: keyFor.provider, api_key: keyDraft.trim(),
        config: model ? { model } : undefined, is_default: true,
      });
      setKeyDraft("");
      await load();
      setActive(keyFor);
      setView("models");
      setKeyFor(null);
    } catch (e: any) {
      setErr(e?.message || "Could not save the key");
    } finally {
      setBusy(false);
    }
  };

  const providerModels = useMemo(() => {
    if (!active) return [];
    const q = query.trim().toLowerCase();
    const list = models.filter((m) => m.provider === active.provider);
    if (!q) return list;
    return list.filter((m) =>
      `${m.model_id} ${m.display_name || ""}`.toLowerCase().includes(q)
    );
  }, [models, active, query]);

  return (
    <>
      {/* Arrow-only trigger so the text field keeps its full width. */}
      <DropdownMenu
        onOpenChange={(open: boolean) => {
          if (open) {
            setView("providers");
            setActive(null);
            setQuery("");
            setErr(null);
          }
        }}
      >
        <DropdownMenuTrigger
          aria-label="Choose model and provider"
          title={provider ? `${model || "Auto"} · ${provider}` : "Choose model and provider"}
          className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
        >
          <ChevronDown className="h-4 w-4" />
          {provider && <span className="sr-only">{model || "Auto"} / {provider}</span>}
        </DropdownMenuTrigger>

        <DropdownMenuContent align="end" className="w-72 max-h-80 overflow-hidden p-0">
          {/* ---------- providers ---------- */}
          {view === "providers" && (
            <div className="max-h-80 overflow-auto p-1">
              <div className="flex items-center justify-between px-2 py-1.5">
                <span className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
                  Provider
                </span>
                <button
                  onClick={load}
                  className="inline-flex items-center gap-1 text-[10px] text-zinc-400 hover:text-zinc-600"
                >
                  {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
                </button>
              </div>

              <DropdownMenuItem
                onClick={(e: React.MouseEvent) => {
                  e.preventDefault();
                  setProvider(""); setModel(""); persist("", "");
                }}
                className="gap-2 py-1.5"
              >
                <Cpu className="h-3.5 w-3.5 shrink-0 text-zinc-400" />
                <span className="flex-1 text-sm">Auto</span>
                {!provider && <Check className="h-3.5 w-3.5 shrink-0" />}
              </DropdownMenuItem>

              <DropdownMenuSeparator />

              {catalog.map((c) => {
                const keyed = hasKey(c.provider);
                return (
                  <div key={c.provider} className="flex items-center gap-1">
                    <DropdownMenuItem
                      onClick={(e: React.MouseEvent) => {
                        e.preventDefault();
                        setActive(c);
                        setQuery("");
                        setView("models");
                      }}
                      className="flex-1 gap-2 py-1.5"
                    >
                      {keyed
                        ? <Check className="h-3.5 w-3.5 shrink-0 text-green-600" />
                        : <Server className="h-3.5 w-3.5 shrink-0 text-zinc-400" />}
                      <div className="flex min-w-0 flex-1 flex-col">
                        <div className="flex items-center gap-1.5">
                          <span className="truncate text-sm">{c.label}</span>
                          {c.free_tier && (
                            <span className="shrink-0 rounded bg-emerald-100 px-1 py-px text-[9px] font-bold text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300">FREE</span>
                          )}
                        </div>
                        <div className="truncate text-[11px] text-zinc-500">
                          {keyed ? "Key saved" : "Key required"}
                        </div>
                      </div>
                      <ChevronRight className="h-3.5 w-3.5 shrink-0 text-zinc-400" />
                    </DropdownMenuItem>

                    {!keyed && (
                      <button
                        onClick={(e: React.MouseEvent) => {
                          e.preventDefault();
                          e.stopPropagation();
                          setKeyDraft("");
                          setErr(null);
                          setKeyFor(c);
                        }}
                        title={`Add ${c.label} API key`}
                        className="mr-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800"
                      >
                        <KeyRound className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                );
              })}

              {err && !busy && <p className="px-2 py-1.5 text-[11px] text-red-600">{err}</p>}
            </div>
          )}

          {/* ---------- models sub-list ---------- */}
          {view === "models" && active && (
            <div className="max-h-80 overflow-auto p-1">
              <div className="sticky top-0 z-10 bg-white px-1 pb-1 pt-0.5 dark:bg-zinc-950">
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => setView("providers")}
                    className="flex h-6 w-6 items-center justify-center rounded-md text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                    aria-label="Back to providers"
                  >
                    <ArrowLeft className="h-3.5 w-3.5" />
                  </button>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[11px] font-semibold">{active.label}</div>
                    <div className="truncate text-[10px] text-zinc-500">
                      {providerModels.length} model{providerModels.length === 1 ? "" : "s"}
                    </div>
                  </div>
                  {!hasKey(active.provider) && (
                    <button
                      onClick={() => { setKeyDraft(""); setErr(null); setKeyFor(active); }}
                      className="flex items-center gap-1 rounded-md border px-1.5 py-1 text-[10px] text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
                    >
                      <KeyRound className="h-3 w-3" /> Add key
                    </button>
                  )}
                  <button
                    onClick={load}
                    className="flex h-6 w-6 items-center justify-center rounded-md text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                    aria-label="Refresh models"
                  >
                    {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
                  </button>
                </div>
                <div className="relative mt-1.5">
                  <Search className="absolute left-2 top-1/2 h-3 w-3 -translate-y-1/2 text-zinc-400" />
                  <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Search models"
                    className="w-full rounded-md border border-zinc-200 bg-transparent py-1 pl-7 pr-2 text-xs outline-none dark:border-zinc-700"
                  />
                </div>
              </div>

              <DropdownMenuItem
                onClick={() => { setModel(""); setProvider(active.provider); persist(active.provider, ""); }}
                className="gap-2 py-1.5"
              >
                <Cpu className="h-3.5 w-3.5 shrink-0 text-zinc-400" />
                <span className="flex-1 text-sm">Auto (provider default)</span>
                {model === "" && <Check className="h-3.5 w-3.5 shrink-0" />}
              </DropdownMenuItem>

              <DropdownMenuSeparator />

              {providerModels.map((m) => {
                const isFree = !!(m.config as any)?.free;
                return (
                  <DropdownMenuItem
                    key={m.model_id}
                    onClick={() => {
                      setModel(m.model_id);
                      setProvider(m.provider);
                      persist(m.provider, m.model_id);
                    }}
                    className="gap-2 py-1.5"
                  >
                    <Cpu className="h-3.5 w-3.5 shrink-0 text-zinc-400" />
                    <div className="flex min-w-0 flex-1 flex-col">
                      <div className="flex items-center gap-1.5">
                        <span className="truncate text-[13px]">{m.display_name || m.model_id}</span>
                        {isFree && (
                          <span className="shrink-0 rounded bg-emerald-100 px-1 py-px text-[9px] font-bold text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300">FREE</span>
                        )}
                      </div>
                      <div className="truncate text-[10px] text-zinc-500">
                        {m.model_id}
                        {m.context_window ? ` · ${Math.round(m.context_window / 1000)}k ctx` : ""}
                      </div>
                    </div>
                    {model === m.model_id && <Check className="h-3.5 w-3.5 shrink-0" />}
                  </DropdownMenuItem>
                );
              })}

              {providerModels.length === 0 && (
                <p className="px-2 py-3 text-center text-[11px] text-zinc-500">
                  No models for this provider yet. Press refresh.
                </p>
              )}
            </div>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Small popup for API key entry */}
      <Dialog open={!!keyFor} onOpenChange={(o: boolean) => { if (!o) { setKeyFor(null); setErr(null); } }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Connect {keyFor?.label}</DialogTitle>
            <DialogDescription>{keyFor?.note}</DialogDescription>
          </DialogHeader>
          <input
            type="password"
            value={keyDraft}
            onChange={(e) => setKeyDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") saveKey(); }}
            placeholder="API key"
            autoFocus
            className="w-full rounded-md border border-zinc-200 bg-transparent px-3 py-2 text-sm outline-none dark:border-zinc-700"
          />
          {err && <p className="text-[11px] text-red-600">{err}</p>}
          <div className="flex items-center gap-2">
            <button
              onClick={saveKey}
              disabled={busy || !keyDraft.trim()}
              className="inline-flex flex-1 items-center justify-center gap-1 rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
            >
              {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
              Save &amp; verify
            </button>
            {keyFor?.signup_url && (
              <a
                href={keyFor.signup_url}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-md border px-3 py-2 text-sm text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
              >
                Get key
              </a>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
