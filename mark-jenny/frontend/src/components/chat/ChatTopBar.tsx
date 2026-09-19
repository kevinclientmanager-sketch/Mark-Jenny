"use client";

import { SearchIcon, Settings, Moon, Sun, PanelRightClose, PanelRight, X, Plus } from "lucide-react";
import { useTheme } from "next-themes";
import { usePathname } from "next/navigation";
import { setSearchOpen } from "@/lib/nav/search-store";
import { setSettingsOpen } from "@/lib/nav/settings-store";
import { cn } from "@/lib/utils";

export interface Tab {
  id: number;
  title: string;
  active: boolean;
}

export function ChatTopBar({
  tabs,
  onTabSelect,
  onTabClose,
  onTabNew,
  rightPanelOpen,
  onToggleRightPanel,
  activeProjectName,
}: {
  tabs?: Tab[];
  onTabSelect?: (id: number) => void;
  onTabClose?: (id: number) => void;
  onTabNew?: () => void;
  rightPanelOpen?: boolean;
  onToggleRightPanel?: () => void;
  activeProjectName?: string;
}) {
  const { theme, setTheme } = useTheme();
  const pathname = usePathname();

  return (
    <header className="h-10 shrink-0 border-b bg-white/80 backdrop-blur-sm dark:bg-zinc-900/80 sticky top-0 z-40 flex items-center gap-0.5 px-2">
      {/* Session tabs — take up all available space */}
      <div className="flex items-center gap-0.5 overflow-x-auto flex-1 min-w-0 scrollbar-none">
        {tabs?.map((tab) => (
          <div
            key={tab.id}
            onClick={() => onTabSelect?.(tab.id)}
            className={cn(
              "group flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium cursor-pointer transition-colors shrink-0 max-w-[180px]",
              tab.active
                ? "bg-zinc-200 dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100"
                : "text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800/50"
            )}
            title={tab.title}
          >
            <span className="truncate">{tab.title || "New session"}</span>
            <button
              onClick={(e) => { e.stopPropagation(); onTabClose?.(tab.id); }}
              className={cn(
                "shrink-0 rounded p-0.5 hover:bg-zinc-300 dark:hover:bg-zinc-600 transition-opacity",
                tab.active ? "opacity-60 hover:opacity-100" : "opacity-0 group-hover:opacity-60 hover:!opacity-100"
              )}
              title="Close tab"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        ))}
        {onTabNew && (
          <button
            onClick={onTabNew}
            className="shrink-0 rounded-md p-1.5 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800/50 transition-colors"
            title="New session (Ctrl+T)"
          >
            <Plus className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {/* Center: active project/chat name */}
      {activeProjectName && (
        <div className="hidden md:flex items-center gap-1.5 px-3 shrink-0">
          <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400 truncate max-w-[200px]">{activeProjectName}</span>
        </div>
      )}

      {/* Right-side icons */}
      <div className="flex items-center gap-0.5 shrink-0">
        <button
          onClick={() => setSearchOpen(true)}
          className={cn(
            "rounded-md p-1.5 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900 dark:hover:bg-zinc-800 dark:hover:text-zinc-100",
            pathname === "/chat" && "text-blue-600"
          )}
          title="Search (Ctrl+K)"
        >
          <SearchIcon className="h-4 w-4" />
        </button>
        <button
          onClick={() => setSettingsOpen(true)}
          className={cn(
            "rounded-md p-1.5 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900 dark:hover:bg-zinc-800 dark:hover:text-zinc-100",
            pathname === "/settings" && "text-blue-600"
          )}
          title="Settings"
        >
          <Settings className="h-4 w-4" />
        </button>
        {/* Right panel toggle — first position (swapped with theme) */}
        <button
          onClick={onToggleRightPanel}
          className={cn(
            "rounded-md p-1.5 transition-colors",
            rightPanelOpen
              ? "text-blue-600 bg-blue-50 dark:bg-blue-900/30"
              : "text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
          )}
          title={rightPanelOpen ? "Close right panel" : "Open right panel"}
        >
          {rightPanelOpen ? <PanelRightClose className="h-4 w-4" /> : <PanelRight className="h-4 w-4" />}
        </button>
        {/* Theme toggle — last position (swapped with right panel) */}
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="rounded-md p-1.5 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
          title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
        </button>
      </div>
    </header>
  );
}
