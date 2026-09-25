"use client";

import { X, Plus } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SessionTab {
  id: number;
  title: string;
  active: boolean;
}

export function SessionTabs({
  tabs,
  onSelect,
  onClose,
  onNew,
}: {
  tabs: SessionTab[];
  onSelect: (id: number) => void;
  onClose: (id: number) => void;
  onNew: () => void;
}) {
  return (
    <div className="flex items-center gap-0.5 border-b bg-zinc-50 dark:bg-zinc-900/50 px-2 py-1 overflow-x-auto scrollbar-none">
      {tabs.map((tab) => (
        <div
          key={tab.id}
          onClick={() => onSelect(tab.id)}
          className={cn(
            "group flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium cursor-pointer transition-colors shrink-0 max-w-[180px]",
            tab.active
              ? "bg-white dark:bg-zinc-800 shadow-sm text-zinc-900 dark:text-zinc-100 border border-zinc-200 dark:border-zinc-700"
              : "text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800/50"
          )}
          title={tab.title}
        >
          <span className="truncate">{tab.title || "New session"}</span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onClose(tab.id);
            }}
            className={cn(
              "shrink-0 rounded p-0.5 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-opacity",
              tab.active ? "opacity-60 hover:opacity-100" : "opacity-0 group-hover:opacity-60 hover:!opacity-100"
            )}
            title="Close tab"
          >
            <X className="h-3 w-3" />
          </button>
        </div>
      ))}
      <button
        onClick={onNew}
        className="shrink-0 rounded-md p-1.5 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800/50 transition-colors"
        title="New session (Ctrl+T)"
      >
        <Plus className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

