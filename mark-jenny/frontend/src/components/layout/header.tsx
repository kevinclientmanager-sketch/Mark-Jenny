"use client";

import { Moon, Sun, SearchIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTheme } from "next-themes";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { cn } from "@/lib/utils";
import { setSearchOpen } from "@/lib/nav/search-store";

const TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/projects": "Projects",
  "/chat": "Chat",
  "/quick-actions": "Quick Actions",
  "/library": "Library",
  "/ai": "AI Studio",
  "/skills": "Skills",
  "/connectors": "Connectors",
  "/knowledge": "Knowledge",
  "/generate": "Generate",
  "/agents": "Agents",
  "/scheduled": "Scheduled",
  "/memory": "Memory",
  "/admin": "Admin",
  "/advanced": "Advanced",
  "/settings": "Settings",
};

function titleFromPath(pathname: string): string {
  if (pathname.startsWith("/projects")) return "Project";
  const exact = TITLES[pathname];
  if (exact) return exact;
  if (pathname.startsWith("/auth")) return "Account";
  return "mark imti";
}

export function Header() {
  const { theme, setTheme } = useTheme();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();
  const modeTabs = [
    { label: "Chat", href: "/chat" },
    { label: "Work", href: "/projects" },
    { label: "Browse", href: "/chat?mode=browse" },
  ];

  return (
    <header className="h-16 shrink-0 border-b bg-white/80 backdrop-blur-sm dark:bg-zinc-900/80 sticky top-0 z-40">
      <div className="flex h-full items-center justify-between px-4">
        <h1 className="text-lg font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
          {titleFromPath(pathname)}
        </h1>

        <nav aria-label="Workspace mode" className="hidden items-center gap-1 rounded-lg border bg-muted/40 p-1 md:flex">
          {modeTabs.map((tab) => {
            const active = tab.href === "/chat"
              ? pathname === "/chat" && searchParams.get("mode") !== "browse"
              : tab.href === "/projects"
                ? pathname.startsWith("/projects")
                : pathname === "/chat" && searchParams.get("mode") === "browse";
            return (
              <button
                key={tab.label}
                type="button"
                onClick={() => {
                  if (tab.label === "Browse") {
                    window.localStorage.setItem("mark.sidebarMode", "browse");
                    window.location.href = tab.href;
                  } else if (tab.label === "Chat") {
                    window.localStorage.setItem("mark.sidebarMode", "chat");
                    window.location.href = tab.href;
                  } else {
                    router.push(tab.href);
                  }
                }}
                className={cn("rounded-md px-3 py-1.5 text-xs font-medium transition-colors", active ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground")}
                aria-current={active ? "page" : undefined}
              >
                {tab.label}
              </button>
            );
          })}
        </nav>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setSearchOpen(true)}
            className="hidden h-9 w-64 items-center gap-2 rounded-lg border bg-muted/40 px-3 text-sm text-muted-foreground transition-colors hover:bg-muted sm:flex"
          >
            <SearchIcon className="h-4 w-4 shrink-0" />
            <span className="truncate">Search…</span>
            <kbd className="ml-auto shrink-0 rounded border bg-background px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
              ⌘K
            </kbd>
          </button>
          <Button
            variant="ghost"
            size="icon"
            className="sm:hidden"
            onClick={() => setSearchOpen(true)}
            title="Search (Ctrl+K)"
          >
            <SearchIcon className="h-5 w-5" />
          </Button>

          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          >
            <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Moon className="h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          </Button>
        </div>
      </div>
    </header>
  );
}
