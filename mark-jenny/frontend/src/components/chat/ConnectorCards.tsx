"use client";
import { Globe, Mail, Calendar, FileText, Code2, Database, Cloud, Lock, Image as ImageIcon, Music } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ConnectorCard {
  id: string;
  label: string;
  description: string;
  icon: any;
  color: string;
  connected: boolean;
}

const defaultConnectors: ConnectorCard[] = [
  { id: "gmail", label: "Gmail", description: "Read, send, and manage emails", icon: Mail, color: "text-red-500", connected: false },
  { id: "calendar", label: "Calendar", description: "Manage events and schedules", icon: Calendar, color: "text-blue-500", connected: false },
  { id: "drive", label: "Google Drive", description: "Access and manage files", icon: Cloud, color: "text-green-500", connected: false },
  { id: "github", label: "GitHub", description: "Repos, issues, and pull requests", icon: Code2, color: "text-zinc-700 dark:text-zinc-300", connected: false },
  { id: "database", label: "Database", description: "Query and manage data", icon: Database, color: "text-purple-500", connected: false },
  { id: "browser", label: "Browser", description: "Browse and interact with websites", icon: Globe, color: "text-cyan-500", connected: false },
  { id: "files", label: "Local Files", description: "Access local file system", icon: FileText, color: "text-yellow-500", connected: false },
  { id: "images", label: "Image Gen", description: "Generate and edit images", icon: ImageIcon, color: "text-pink-500", connected: false },
];

export function ConnectorCards({ onSelect }: { onSelect?: (id: string) => void }) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
      {defaultConnectors.map((conn) => (
        <button
          key={conn.id}
          onClick={() => onSelect?.(conn.id)}
          className={cn(
            "flex items-center gap-3 px-4 py-3 rounded-xl border transition-all shrink-0 min-w-[180px]",
            "border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700",
            "hover:shadow-md bg-white dark:bg-zinc-900"
          )}
        >
          <div className={cn("h-10 w-10 rounded-lg flex items-center justify-center bg-zinc-100 dark:bg-zinc-800", conn.color)}>
            <conn.icon className="h-5 w-5" />
          </div>
          <div className="text-left">
            <p className="text-sm font-medium">{conn.label}</p>
            <p className="text-[10px] text-zinc-500">{conn.description}</p>
          </div>
          {conn.connected && (
            <span className="h-2 w-2 rounded-full bg-green-500 ml-auto" />
          )}
        </button>
      ))}
    </div>
  );
}

