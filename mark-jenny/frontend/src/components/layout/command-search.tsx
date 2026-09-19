"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  SearchIcon,
  LayoutDashboard,
  FolderKanban,
  Bot,
  Sparkles,
  Flame,
  FolderOpen,
  Settings,
  Cpu,
  Plug,
  BookOpen,
  Wand2,
  Users,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react"
import { useSearchOpen, setSearchOpen } from "@/lib/nav/search-store";
import { projectsApi } from "@/lib/api";

const PAGES: { label: string; href: string; icon: LucideIcon; hint: string; keywords: string }[] = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard, hint: "Quick access", keywords: "home" },
  { label: "Projects", href: "/projects", icon: FolderKanban, hint: "Quick access", keywords: "project folder workspace" },
  { label: "Chat", href: "/chat", icon: Bot, hint: "Quick access", keywords: "talk messages agent" },
  { label: "Quick Actions", href: "/quick-actions", icon: Sparkles, hint: "Quick access", keywords: "shortcuts workflows tasks" },
  { label: "Library", href: "/library", icon: FolderOpen, hint: "Quick access", keywords: "files assets" },
  { label: "AI Studio", href: "/ai", icon: Cpu, hint: "Quick access", keywords: "models agent" },
  { label: "Skills", href: "/skills", icon: Wand2, hint: "Quick access", keywords: "capabilities" },
  { label: "Connectors", href: "/connectors", icon: Plug, hint: "Quick access", keywords: "integrations apis" },
  { label: "Knowledge", href: "/knowledge", icon: BookOpen, hint: "Quick access", keywords: "docs memory" },
  { label: "Generate", href: "/generate", icon: Flame, hint: "Quick access", keywords: "images creative" },
  { label: "Agents", href: "/agents", icon: Users, hint: "Quick access", keywords: "autonomous crew" },
  { label: "Settings", href: "/settings", icon: Settings, hint: "Quick access", keywords: "preferences config" },
];

type SearchItem = { label: string; hint: string; href: string; icon: React.ReactNode };

export function CommandSearch() {
  const open = useSearchOpen();
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [projects, setProjects] = useState<SearchItem[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setActiveIndex(0);
    const timeout = setTimeout(() => inputRef.current?.focus(), 20);
    return () => clearTimeout(timeout);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    projectsApi
      .list({ page_size: 100 })
      .then((res) => {
        if (cancelled) return;
        setProjects(
          res.projects.map((p) => ({
            label: p.name,
            hint: `Project · ${p.task_count ?? 0} tasks`,
            href: `/projects/${p.id}`,
            icon: <FolderKanban className="h-4 w-4 shrink-0 text-muted-foreground" />,
          }))
        );
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [open]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen(!open);
      }
      if (e.key === "Escape" && open) {
        setSearchOpen(false);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    const groups: { title: string; items: SearchItem[] }[] = [];
    const toItems = (pages: typeof PAGES): SearchItem[] =>
      pages.map((p) => ({
        label: p.label,
        href: p.href,
        hint: p.hint,
        icon: <p.icon className="h-4 w-4 shrink-0 text-muted-foreground" />,
      }));
    if (!q) {
      groups.push({ title: "Pages", items: toItems(PAGES) });
      if (projects.length) groups.push({ title: "Projects", items: projects.slice(0, 8) });
      return groups;
    }
    const pages = PAGES.filter((p) => (p.label + " " + p.keywords).toLowerCase().includes(q));
    if (pages.length) groups.push({ title: "Pages", items: toItems(pages) });
    const projs = projects.filter((p) => p.label.toLowerCase().includes(q)).slice(0, 8);
    if (projs.length) groups.push({ title: "Projects", items: projs });
    return groups;
  }, [query, projects]);

  const flat = useMemo(() => results.flatMap((g) => g.items), [results]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  if (!open) return null;

  function go(item: SearchItem) {
    setSearchOpen(false);
    router.push(item.href);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, flat.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const item = flat[activeIndex];
      if (item) go(item);
    }
  }

  let runningIndex = 0;

  return (
    <div className="fixed inset-0 z-[90] flex items-start justify-center pt-[15vh] px-4">
      <div
        className="fixed inset-0 bg-black/40 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=open]:fade-in-0"
        onClick={() => setSearchOpen(false)}
      />
      <div className="relative w-full max-w-lg overflow-hidden rounded-xl border bg-popover text-popover-foreground shadow-2xl data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95">
        <div className="flex items-center gap-2 border-b px-3">
          <SearchIcon className="h-4 w-4 shrink-0 text-muted-foreground" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Search pages, projects…"
            className="h-12 w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
          <kbd className="shrink-0 rounded-md border bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
            ESC
          </kbd>
        </div>

        <div className="max-h-[46vh] overflow-y-auto p-2">
          {flat.length === 0 && (
            <p className="px-2 py-8 text-center text-sm text-muted-foreground">
              No results for “{query}”
            </p>
          )}
          {results.map((group) => (
            <div key={group.title} className="mb-1">
              <p className="px-2 py-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                {group.title}
              </p>
              {group.items.map((item) => {
                const idx = runningIndex++;
                const active = idx === activeIndex;
                return (
                  <button
                    key={`${group.title}-${item.href}`}
                    onMouseEnter={() => setActiveIndex(idx)}
                    onClick={() => go(item)}
                    className={cn(
                      "flex w-full items-center gap-2.5 rounded-md px-2 py-2 text-left text-sm outline-none",
                      active ? "bg-accent text-accent-foreground" : "text-foreground"
                    )}
                  >
                    {item.icon}
                    <span className="min-w-0 flex-1 truncate">{item.label}</span>
                    <span className="shrink-0 text-xs text-muted-foreground">{item.hint}</span>
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}