"use client";
import { useState } from "react";
import { Code2, Presentation, Globe, Image as ImageIcon, FileText, Music, Video, Wand2, ChevronDown, X } from "lucide-react";
import { cn } from "@/lib/utils";

export interface TaskType {
  id: string;
  label: string;
  icon: any;
  color: string;
  placeholder: string;
  options?: { id: string; label: string }[];
}

const defaultTaskTypes: TaskType[] = [
  { id: "chat", label: "Chat", icon: Wand2, color: "text-purple-500", placeholder: "Ask me anything..." },
  { id: "code", label: "Code", icon: Code2, color: "text-blue-500", placeholder: "Describe the code you want to build...", options: [
    { id: "website", label: "Website" },
    { id: "api", label: "API" },
    { id: "script", label: "Script" },
    { id: "app", label: "Application" },
  ]},
  { id: "slides", label: "Slides", icon: Presentation, color: "text-orange-500", placeholder: "What should the presentation be about?", options: [
    { id: "pitch", label: "Pitch Deck" },
    { id: "report", label: "Report" },
    { id: "tutorial", label: "Tutorial" },
    { id: "proposal", label: "Proposal" },
  ]},
  { id: "research", label: "Research", icon: Globe, color: "text-green-500", placeholder: "What do you want to research?" },
  { id: "image", label: "Image", icon: ImageIcon, color: "text-pink-500", placeholder: "Describe the image you want to create..." },
  { id: "document", label: "Document", icon: FileText, color: "text-yellow-500", placeholder: "What document should I create?" },
  { id: "video", label: "Video", icon: Video, color: "text-red-500", placeholder: "Describe the video content..." },
  { id: "audio", label: "Audio", icon: Music, color: "text-cyan-500", placeholder: "What audio should I generate?" },
];

export function TaskTypePills({
  selected,
  onSelect,
  placeholder,
}: {
  selected: string;
  onSelect: (id: string) => void;
  placeholder?: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const selectedType = defaultTaskTypes.find(t => t.id === selected) || defaultTaskTypes[0];

  return (
    <div className="relative">
      <button
        onClick={() => setExpanded(!expanded)}
        className={cn(
          "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border transition-all",
          "border-zinc-200 dark:border-zinc-700 hover:border-zinc-300 dark:hover:border-zinc-600",
          expanded && "border-blue-500 dark:border-blue-400"
        )}
      >
        <selectedType.icon className={cn("h-3.5 w-3.5", selectedType.color)} />
        <span>{selectedType.label}</span>
        <ChevronDown className={cn("h-3 w-3 transition-transform", expanded && "rotate-180")} />
      </button>

      {expanded && (
        <div className="absolute bottom-full left-0 mb-2 p-2 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-lg z-50 min-w-[200px]">
          <div className="grid grid-cols-2 gap-1">
            {defaultTaskTypes.map((type) => (
              <button
                key={type.id}
                onClick={() => {
                  onSelect(type.id);
                  setExpanded(false);
                }}
                className={cn(
                  "flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-colors text-left",
                  selected === type.id
                    ? "bg-blue-50 dark:bg-blue-950/30 text-blue-600 dark:text-blue-400"
                    : "hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300"
                )}
              >
                <type.icon className={cn("h-4 w-4", type.color)} />
                <span>{type.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function TaskTypeChip({
  type,
  subType,
  onRemove,
}: {
  type: string;
  subType?: string;
  onRemove: () => void;
}) {
  const taskType = defaultTaskTypes.find(t => t.id === type);
  if (!taskType) return null;
  const Icon = taskType.icon;

  return (
    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 dark:bg-blue-950/30 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800">
      <Icon className="h-3 w-3" />
      <span>{taskType.label}</span>
      {subType && (
        <>
          <span className="text-blue-300 dark:text-blue-600">/</span>
          <span className="text-blue-500 dark:text-blue-400">{subType}</span>
        </>
      )}
      <button onClick={onRemove} className="ml-0.5 hover:bg-blue-100 dark:hover:bg-blue-900 rounded-full p-0.5">
        <X className="h-2.5 w-2.5" />
      </button>
    </div>
  );
}

