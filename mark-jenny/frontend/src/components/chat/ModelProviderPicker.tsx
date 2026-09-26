"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronDown, Cpu, Check, Loader2, Search, Sparkles, Server, Zap } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { modelsApi, ProviderCatalogEntry, AIModel } from "@/lib/api/models";
import { cn } from "@/lib/utils";

/**
 * Model + provider picker that lives INSIDE the composer box.
 * Two independent drawers: one for the provider, one for the model.
 * Selection is persisted to the account so it applies to chat, tasks,
 * quick actions and generation alike.
 */
export default function ModelProviderPicker({
  mode,
  className,
}: {
  mode?: string;
  className?: string;
}) {
  const [catalog, setCatalog] = useState<ProviderCatalogEntry[]>([]);
  const [models, setModels] = useState<AIModel[]>([]);
  const [connected, setConnected] = useState<{ provider: string; has_key: boolean }[]>([]);
  const [provider, setProvider] = useState<string>("");
  const [model, setModel] = useState<string>("");
  const [openDrawer, setOpenDrawer] = useState<"provider" | "model" | null>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [cat, ms, provs] = await Promise.all([
        modelsApi.providerCatalog().catch(() => ({ providers: [] as ProviderCatalogEntry[] })),
        modelsApi.listModels().catch(() => [] as AIModel[]),
        modelsApi.listProviders().catch(() => [] as any[]),
      ]);
      setCatalog(cat.providers || []);
      setModels(ms || []);
      setConnected((provs || []).map((p: any) => ({ provider: p.provider, has_key: p.has_key })));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Restore the account's saved default.
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

  const providerModels = useMemo(
    () => models.filter((m) => !provider || m.provider === provider),
    [models, provider]
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return providerModels;
    return providerModels.filter((m) =>
      `${m.provider} ${m.model_id} ${m.display_name || ""}`.toLowerCase().includes(q)
    );
  }, [providerModels, query]);

  const hasKey = useCallback(
    (id: string) => connected.some((c) => c.provider === id && c.has_key),
    [connected]
  );

  const persist = useCallback(async (nextProvider: string, nextModel: string) => {
    setSaving(true);
    try {
      const { api } = await import("@/lib/api/client");
      // Model choice is stored on the provider config, which is what the
      // router reads when dispatching a call.
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
    } finally {
      setSaving(false);
    }
  }, [load]);

  const providerLabel =
    catalog.find((c) => c.provider === provider)?.label ||
    provider ||
    "Auto";

  const modelLabel = model || "Auto";

  const chip = (
    label: string,
    icon: React.ReactNode,
    onClick: () => void,
    active: boolean,
    title: string,
  ) => (
    <button
      type="button"
      onClick={onClick}
      title={title}
      className={cn(
        "inline-flex max-w-[190px] items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-medium transition-colors",
        "text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100",
        active && "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
      )}
    >
      {icon}
      <span className="truncate">{label}</span>
      <ChevronDown className="h-3 w-3 shrink-0 opacity-60" />
    </button>
  );

  return (
    <>
      <div className={cn("flex items-center justify-center gap-1", className)}>
        {chip(
          providerLabel,
          <Server className="h-3 w-3 shrink-0" />,
          () => { setQuery(""); setOpenDrawer("provider"); },
          !!provider,
          "Choose the AI provider (OpenAI, Anthropic, Google, OpenRouter, Groq, local Ollama…)"
        )}
        <span className="text-zinc-300 dark:text-zinc-600">|</span>
        {chip(
          modelLabel,
          <Cpu className="h-3 w-3 shrink-0" />,
          () => { setQuery(""); setOpenDrawer("model"); },
          !!model,
          "Choose the exact model used for this conversation"
        )}
        {saving && <Loader2 className="ml-1 h-3 w-3 animate-spin text-zinc-400" />}
      </div>

      {/* Provider drawer */}
      <Sheet open={openDrawer === "provider"} onOpenChange={(o) => setOpenDrawer(o ? "provider" : null)}>
        <SheetContent side="bottom" className="max-h-[70vh] overflow-auto">
          <SheetHeader>
            <SheetTitle>Provider</SheetTitle>
            <SheetDescription>
              Where Mark-Imti sends the request. Connected providers can be used immediately.
            </SheetDescription>
          </SheetHeader>
          <div className="mt-3 space-y-1.5 px-1">
            <button
              onClick={() => { setProvider(""); persist("", model); setOpenDrawer(null); }}
              className={cn(
                "flex w-full items-center justify-between rounded-lg border p-3 text-left text-sm",
                !provider && "border-blue-500 bg-blue-50 dark:bg-blue-950/30"
              )}
            >
              <span>
                <span className="font-medium">Auto (smart routing)</span>
                <span className="block text-xs text-zinc-500">Let Mark-Imti pick per task type</span>
              </span>
              {!provider && <Check className="h-4 w-4" />}
            </button>

            {catalog.map((c) => {
              const connectedNow = hasKey(c.provider);
              return (
                <button
                  key={c.provider}
                  onClick={() => { setProvider(c.provider); persist(c.provider, model); setOpenDrawer(null); }}
                  className={cn(
                    "flex w-full items-center justify-between gap-3 rounded-lg border p-3 text-left text-sm",
                    provider === c.provider && "border-blue-500 bg-blue-50 dark:bg-blue-950/30"
                  )}
                >
                  <span className="min-w-0">
                    <span className="flex items-center gap-2">
                      <span className="font-medium">{c.label}</span>
                      {c.free_tier && (
                        <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300">
                          FREE
                        </span>
                      )}
                      {connectedNow && (
                        <span className="rounded bg-green-100 px-1.5 py-0.5 text-[10px] font-semibold text-green-700 dark:bg-green-900 dark:text-green-300">
                          KEY SAVED
                        </span>
                      )}
                    </span>
                    <span className="block truncate text-xs text-zinc-500">{c.note}</span>
                  </span>
                  {provider === c.provider && <Check className="h-4 w-4 shrink-0" />}
                </button>
              );
            })}
          </div>
        </SheetContent>
      </Sheet>

      {/* Model drawer */}
      <Sheet open={openDrawer === "model"} onOpenChange={(o) => setOpenDrawer(o ? "model" : null)}>
        <SheetContent side="bottom" className="max-h-[70vh] overflow-auto">
          <SheetHeader>
            <SheetTitle>Model</SheetTitle>
            <SheetDescription>
              {provider
                ? `Models available from ${providerLabel}.`
                : "All discovered models. Pick a provider first to narrow the list."}
            </SheetDescription>
          </SheetHeader>
          <div className="mt-3 flex items-center gap-2 px-1">
            <div className="relative flex-1">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-400" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search models…"
                className="w-full rounded-lg border bg-transparent py-2 pl-8 pr-3 text-sm"
              />
            </div>
            <button
              onClick={async () => { await load(); }}
              className="inline-flex items-center gap-1 rounded-lg border px-2.5 py-2 text-xs"
              title="Re-query providers for their latest models"
            >
              {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
              Refresh
            </button>
          </div>
          <p className="mt-2 px-1 text-xs text-zinc-500">
            {models.length} models discovered. {providerModels.length} from this provider.
          </p>
          <div className="mt-2 space-y-1 px-1 pb-4">
            <button
              onClick={() => { setModel(""); persist(provider, ""); setOpenDrawer(null); }}
              className={cn(
                "flex w-full items-center justify-between rounded-lg border p-2.5 text-left text-sm",
                !model && "border-blue-500 bg-blue-50 dark:bg-blue-950/30"
              )}
            >
              <span className="font-medium">Auto (provider default)</span>
              {!model && <Check className="h-4 w-4" />}
            </button>
            {filtered.map((m) => {
              const isFree = !!(m.config as any)?.free;
              return (
                <button
                  key={`${m.provider}-${m.model_id}`}
                  onClick={() => { setModel(m.model_id); persist(m.provider, m.model_id); setProvider(m.provider); setOpenDrawer(null); }}
                  className={cn(
                    "flex w-full items-center justify-between gap-3 rounded-lg border p-2.5 text-left",
                    model === m.model_id && "border-blue-500 bg-blue-50 dark:bg-blue-950/30"
                  )}
                >
                  <span className="min-w-0">
                    <span className="flex items-center gap-2">
                      <span className="truncate text-sm font-medium">{m.display_name || m.model_id}</span>
                      {isFree && (
                        <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300">FREE</span>
                      )}
                    </span>
                    <span className="block truncate text-[11px] text-zinc-500">
                      {m.provider} · {m.model_id}
                      {m.context_window ? ` · ${Math.round(m.context_window / 1000)}k ctx` : ""}
                    </span>
                  </span>
                  {model === m.model_id && <Check className="h-4 w-4 shrink-0" />}
                </button>
              );
            })}
            {filtered.length === 0 && (
              <p className="p-4 text-center text-sm text-zinc-500">
                {models.length === 0
                  ? "No models yet. Add a provider key in AI Studio, then press Refresh."
                  : "No model matches that search."}
              </p>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}
