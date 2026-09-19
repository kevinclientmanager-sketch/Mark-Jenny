"use client";

import { useState } from "react";
import { SearchIcon, Settings, Moon, Sun, PanelRightClose, PanelRight, X, Plus, Pin, PinOff, MoreHorizontal, Pencil, Trash2 } from "lucide-react";
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
  isPinned,
  onTogglePin,
  onRenameTab,
  onDeleteTab,
}: {
  tabs?: Tab[];
  onTabSelect?: (id: number) => void;
  onTabClose?: (id: number) => void;
  onTabNew?: () => void;
  rightPanelOpen?: boolean;
  onToggleRightPanel?: () => void;
  activeProjectName?: string;
  isPinned?: boolean;
  onTogglePin?: () => void;
  onRenameTab?: (id: number, title: string) => void;
  onDeleteTab?: (id: number) => void;
}) {
  const { theme, setTheme } = useTheme();
  const pathname = usePathname();
  const [hoveredTab, setHoveredTab] = useState<number | null>(null);
  const [menuTab, setMenuTab] = useState<number | null>(null);
  const [renamingTab, setRenamingTab] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState("");

  return (
    <header className="h-10 shrink-0 border-b bg-white/80 backdrop-blur-sm dark:bg-zinc-900/80 sticky top-0 z-40 flex items-center gap-0.5 px-2">
      {/* Session tabs */}
      <div className="flex items-center gap-0.5 overflow-x-auto flex-1 min-w-0 scrollbar-none">
        {tabs?.map((tab) => (
          <div
            key={tab.id}
            onClick={() => onTabSelect?.(tab.id)}
            onMouseEnter={() => setHoveredTab(tab.id)}
            onMouseLeave={() => { if (menuTab !== tab.id) setHoveredTab(null); }}
            className={cn(
              "group relative flex items-center gap-1 rounded-md px-2 py-1.5 text-xs font-medium cursor-pointer transition-colors shrink-0 max-w-[180px]",
              tab.active
                ? "bg-zinc-200 dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100"
                : "text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800/50"
            )}
            title={tab.title}
            style={{ overflow: "visible" }}
          >
            {renamingTab === tab.id ? (
              <input
                autoFocus
                value={renameValue}
                onChange={(e) => setRenameValue(e.target.value)}
                onBlur={() => { onRenameTab?.(tab.id, renameValue); setRenamingTab(null); }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") { onRenameTab?.(tab.id, renameValue); setRenamingTab(null); }
                  if (e.key === "Escape") setRenamingTab(null);
                }}
                onClick={(e) => e.stopPropagation()}
                className="w-24 bg-white dark:bg-zinc-800 border rounded px-1 py-0.5 text-xs outline-none"
              />
            ) : (
              <span className="truncate">{tab.title || "New session"}</span>
            )}

            {/* Tab actions — show on hover or when menu is open */}
            {(hoveredTab === tab.id || menuTab === tab.id) && renamingTab !== tab.id && (
              <div className="flex items-center gap-0.5 shrink-0" onClick={(e) => e.stopPropagation()}>
                <button
                  onClick={() => setMenuTab(menuTab === tab.id ? null : tab.id)}
                  className="rounded p-0.5 text-zinc-400 hover:bg-zinc-300 dark:hover:bg-zinc-600 hover:text-zinc-700"
                  title="More options"
                >
                  <MoreHorizontal className="h-3 w-3" />
                </button>
                <button
                  onClick={() => onTabClose?.(tab.id)}
                  className="rounded p-0.5 text-zinc-400 hover:bg-zinc-300 dark:hover:bg-zinc-600 hover:text-zinc-700"
                  title="Close tab"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            )}

            {/* Context dropdown menu */}
            {menuTab === tab.id && (
              <div className="absolute top-full left-0 mt-1 bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg shadow-lg py-1 z-50 min-w-[140px]">
                <button
                  onClick={(e) => { e.stopPropagation(); setRenamingTab(tab.id); setRenameValue(tab.title); setMenuTab(null); }}
                  className="flex w-full items-center gap-2 px-3 py-1.5 text-xs hover:bg-zinc-100 dark:hover:bg-zinc-700"
                >
                  <Pencil className="h-3 w-3" /> Rename
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); onTogglePin?.(); setMenuTab(null); }}
                  className="flex w-full items-center gap-2 px-3 py-1.5 text-xs hover:bg-zinc-100 dark:hover:bg-zinc-700"
                >
                  {isPinned ? <PinOff className="h-3 w-3" /> : <Pin className="h-3 w-3" />}
                  {isPinned ? "Unpin" : "Pin to top"}
                </button>
                <div className="border-t border-zinc-200 dark:border-zinc-700 my-0.5" />
                <button
                  onClick={(e) => { e.stopPropagation(); onDeleteTab?.(tab.id); setMenuTab(null); }}
                  className="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                >
                  <Trash2 className="h-3 w-3" /> Close
                </button>
              </div>
            )}
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

      {/* Center: active project name only */}
      {activeProjectName && (
        <div className="hidden md:flex items-center px-3 shrink-0">
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
        <button
          onClick={onToggleRightPanel}
          className={cn(
            "rounded-md p-1.5 transition-colors",
            rightPanelOpen
              ? "text-blue-600 bg-blue-50 dark:bg-blue-900/30"
              : "text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
          )}
          title={rightPanelOpen ? "Close agent panel" : "Open agent panel"}
        >
          {rightPanelOpen ? <PanelRightClose className="h-4 w-4" /> : <PanelRight className="h-4 w-4" />}
        </button>
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
