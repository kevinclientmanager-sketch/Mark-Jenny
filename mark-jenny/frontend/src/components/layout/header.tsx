"use client";

import { Moon, Sun, SearchIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTheme } from "next-themes";
import { usePathname } from "next/navigation";
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
  "/settings": "Settings",
};

function titleFromPath(pathname: string): string {
  if (pathname.startsWith("/projects")) return "Project";
  const exact = TITLES[pathname];
  if (exact) return exact;
  if (pathname.startsWith("/auth")) return "Account";
  return "Mark-Imti";
}

export function Header() {
  const { theme, setTheme } = useTheme();
  const pathname = usePathname();

  return (
    <header className="h-16 shrink-0 border-b bg-white/80 backdrop-blur-sm dark:bg-zinc-900/80 sticky top-0 z-40">
      <div className="flex h-full items-center justify-between px-4">
        <h1 className="text-lg font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
          {titleFromPath(pathname)}
        </h1>

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