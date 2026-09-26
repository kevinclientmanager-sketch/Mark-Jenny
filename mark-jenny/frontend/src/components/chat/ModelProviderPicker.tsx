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
import { modelsApi, ProviderCatalogEntry, AIModel } from "@/lib/api/models";
import { cn } from "@/lib/utils";

/**
 * One compact model/provider selector that lives inside the composer.
 *
 * A single trigger opens a scrollable provider list. Choosing a provider
 * slides into a sub-list of that provider's models, also scrollable. If the
 * provider has no key yet, a small inline form collects it without leaving
 * the panel. Nothing here is a full-screen sheet.
 */
export default function ModelProviderPicker({ mode }: { mode?: string }) {
  const [catalog, setCatalog] = useState<ProviderCatalogEntry[]>([]);
  const [models, setModels] = useState<AIModel[]>([]);
  const [connected, setConnected] = useState<{ provider: string; has_key: boolean }[]>([]);
  const [provider, setProvider] = useState<string>("");
  const [model, setModel] = useState<string>("");
  const [view, setView] = useState<"providers" | "models" | "key">("providers");
  const [active, setActive] = useState<ProviderCatalogEntry | null>(null);
  const [query, setQuery] = useState("");
  const [keyDraft, setKeyDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [loadErr, setLoadErr] = useState<string | null>(null);

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
      setLoadErr(null);
    } catch (e: any) {
      setLoadErr(e?.message || "Could not load providers");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Restore the account's saved choice.
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
      /* keep the local selection even if the save fails */
    }
  }, [load]);

  const saveKey = async () => {
    if (!active || !keyDraft.trim()) return;
    setBusy(true);
    try {
      const { api } = await import("@/lib/api/client");
      const test = await api.post<any>("/ai/providers/test", {
        provider: active.provider, api_key: keyDraft.trim(),
      });
      if (!test?.ok) {
        // Surface the provider's own error rather than pretending it worked.
        setLoadErr(test?.detail || "The provider rejected that key.");
        return;
      }
      await api.post("/ai/providers", {
        provider: active.provider, api_key: keyDraft.trim(),
        config: model ? { model } : undefined, is_default: true,
      });
      setKeyDraft("");
      setLoadErr(null);
      await load();
      setView("models");
    } catch (e: any) {
      setLoadErr(e?.message || "Could not save the key");
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

  const providerLabel =
    catalog.find((c) => c.provider === provider)?.label || provider || "Auto";
  const modelLabel = model || "Auto";

  return (
    <DropdownMenu
      onOpenChange={(open: boolean) => {
        if (open) {
          setView("providers");
          setActive(null);
          setQuery("");
          setLoadErr(null);
        }
      }}
    >
      <DropdownMenuTrigger
        type="button"
        aria-label="Choose AI model and provider"
        title="Choose model and provider"
        className="inline-flex h-8 max-w-[220px] items-center gap-1.5 rounded-full border border-zinc-200 bg-white px-2.5 text-xs font-medium text-zinc-600 transition-colors hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800"
      >
        <Cpu className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate">{modelLabel}</span>
        <span className="text-zinc-300 dark:text-zinc-600">/</span>
        <Server className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate">{providerLabel}</span>
        <ChevronDown className="h-3 w-3 shrink-0 opacity-60" />
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-72 max-h-80 overflow-hidden p-0">
        {/* ---------- provider list ---------- */}
        {view === "providers" && (
          <div className="max-h-80 overflow-auto p-1">
            <div className="flex items-center justify-between px-2 py-1.5">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
                Provider
              </span>
              {busy ? <Loader2 className="h-3 w-3 animate-spin text-zinc-400" /> : (
                <button
                  onClick={load}
                  className="text-[10px] text-zinc-400 hover:text-zinc-600"
                  title="Reload providers"
                >
                  refresh
                </button>
              )}
            </div>

            <DropdownMenuItem
              onSelect={(e) => { e.preventDefault(); setProvider(""); setModel(""); persist("", ""); }}
              className="gap-2 py-1.5"
            >
              <Cpu className="h-3.5 w-3.5 shrink-0 text-zinc-400" />
              <div className="flex min-w-0 flex-1 items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="truncate text-sm">Auto</div>
                  <div className="truncate text-[11px] text-zinc-500">Smart routing per task</div>
                </div>
                {!provider && <Check className="h-3.5 w-3.5 shrink-0" />}
              </div>
            </DropdownMenuItem>

            <DropdownMenuSeparator />

            {catalog.map((c) => (
              <DropdownMenuItem
                key={c.provider}
                onSelect={(e) => {
                  e.preventDefault();
                  setActive(c);
                  setQuery("");
                  setLoadErr(null);
                  setView(hasKey(c.provider) ? "models" : "key");
                }}
                className="gap-2 py-1.5"
              >
                {hasKey(c.provider)
                  ? <Check className="h-3.5 w-3.5 shrink-0 text-green-600" />
                  : <KeyRound className="h-3.5 w-3.5 shrink-0 text-zinc-400" />}
                <div className="flex min-w-0 flex-1 flex-col">
                  <div className="flex items-center gap-1.5">
                    <span className="truncate text-sm">{c.label}</span>
                    {c.free_tier && (
                      <span className="shrink-0 rounded bg-emerald-100 px-1 py-px text-[9px] font-bold text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300">
                        FREE
                      </span>
                    )}
                  </div>
                  <div className="truncate text-[11px] text-zinc-500">
                    {hasKey(c.provider) ? "Key saved" : "Key required"}
                  </div>
                </div>
                <ChevronRight className="h-3.5 w-3.5 shrink-0 text-zinc-400" />
              </DropdownMenuItem>
            ))}

            {loadErr && !busy && (
              <p className="px-2 py-1.5 text-[11px] text-red-600">{loadErr}</p>
            )}
          </div>
        )}

        {/* ---------- model sub-list ---------- */}
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
                  className="w-full rounded-md border border-zinc-200 bg-transparent py-1 pl-7 pr-2 text-xs dark:border-zinc-700"
                />
              </div>
            </div>

            <DropdownMenuItem
              onSelect={(e) => {
                e.preventDefault();
                setModel("");
                setProvider(active.provider);
                persist(active.provider, "");
              }}
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
                  onSelect={(e) => {
                    e.preventDefault();
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
                        <span className="shrink-0 rounded bg-emerald-100 px-1 py-px text-[9px] font-bold text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300">
                          FREE
                        </span>
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

            <DropdownMenuSeparator />
            <DropdownMenuItem
              onSelect={(e) => { e.preventDefault(); setKeyDraft(""); setView("key"); }}
              className="gap-2 py-1.5"
            >
              <KeyRound className="h-3.5 w-3.5 shrink-0" />
              <span className="text-[12px]">Replace API key</span>
            </DropdownMenuItem>
          </div>
        )}

        {/* ---------- inline key setup ---------- */}
        {view === "key" && active && (
          <div className="max-h-80 overflow-auto p-2">
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setView("providers")}
                className="flex h-6 w-6 items-center justify-center rounded-md text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                aria-label="Back to providers"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
              </button>
              <div className="min-w-0 flex-1">
                <div className="truncate text-[11px] font-semibold">Connect {active.label}</div>
                <div className="truncate text-[10px] text-zinc-500">{active.note}</div>
              </div>
            </div>

            <input
              type="password"
              value={keyDraft}
              onChange={(e) => setKeyDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") saveKey(); }}
              placeholder="API key"
              autoFocus
              className="mt-2 w-full rounded-md border border-zinc-200 bg-transparent px-2 py-1.5 text-xs dark:border-zinc-700"
            />
            {loadErr && <p className="mt-1 text-[10px] text-red-600">{loadErr}</p>}

            <div className="mt-2 flex items-center gap-1.5">
              <button
                onClick={saveKey}
                disabled={busy || !keyDraft.trim()}
                className="inline-flex flex-1 items-center justify-center gap-1 rounded-md bg-zinc-900 px-2 py-1.5 text-[11px] font-medium text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
              >
                {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
                Save &amp; verify
              </button>
              {active.signup_url && (
                <a
                  href={active.signup_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-md border px-2 py-1.5 text-[11px] text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
                >
                  Get key
                </a>
              )}
            </div>
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
