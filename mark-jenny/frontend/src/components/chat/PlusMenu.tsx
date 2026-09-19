"use client";
import { Camera, Image as ImageIcon, File, Plug, Sparkles, Code2, Presentation, Wand2, Search, Calendar, Table, Video, Music, BookOpen, Laptop, FileText, Code, Bot, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";

export type PlusAction = 
  | "camera" | "picture" | "file" | "connect-computer" | "add-skills"
  | "build-website" | "develop-apps" | "create-slides" | "create-image" | "edit-image"
  | "wide-research" | "scheduled-tasks" | "create-spreadsheet" | "create-video" | "generate-audio" | "playbook"
  | "create-document" | "create-code" | "assign-agent" | "open-browser";

const actions: {id: PlusAction; label: string; icon: any; desc: string}[] = [
  {id:"camera", label:"Camera", icon: Camera, desc:"Take photo"},
  {id:"picture", label:"Picture", icon: ImageIcon, desc:"Upload image"},
  {id:"file", label:"File", icon: File, desc:"Attach file"},
  {id:"connect-computer", label:"Connect My Computer", icon: Laptop, desc:"Pair device (permission)"},
  {id:"add-skills", label:"Add Skills", icon: Plug, desc:"Browse skills"},
  {id:"build-website", label:"Build website", icon: Code2, desc:"Generate site"},
  {id:"develop-apps", label:"Develop apps", icon: Code2, desc:"Build app"},
  {id:"create-slides", label:"Create slides", icon: Presentation, desc:"Deck"},
  {id:"create-image", label:"Create image", icon: Wand2, desc:"Image gen"},
  {id:"edit-image", label:"Edit image", icon: Wand2, desc:"Edit"},
  {id:"wide-research", label:"Wide Research", icon: Search, desc:"Deep research"},
  {id:"scheduled-tasks", label:"Scheduled tasks", icon: Calendar, desc:"Schedule"},
  {id:"create-spreadsheet", label:"Create spreadsheet", icon: Table, desc:"Excel/Sheets"},
  {id:"create-video", label:"Create video", icon: Video, desc:"Video"},
  {id:"generate-audio", label:"Generate audio", icon: Music, desc:"Audio"},
  {id:"create-document", label:"Create document", icon: FileText, desc:"Report / doc"},
  {id:"create-code", label:"Create code", icon: Code, desc:"Script / snippet"},
  {id:"assign-agent", label:"Assign to agent", icon: Bot, desc:"Delegate task"},
  {id:"open-browser", label:"Open browser", icon: Globe, desc:"Browse the web"},
  {id:"playbook", label:"Playbook", icon: BookOpen, desc:"Blueprint"},
];

export function PlusMenu({ onSelect, onFilePick }: { onSelect: (id: PlusAction)=>void; onFilePick?: (f: File)=>void }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="inline-flex items-center justify-center h-9 w-9 rounded-full border bg-white dark:bg-zinc-900 hover:bg-zinc-100 text-xl">
        +
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-64 max-h-80 overflow-auto p-1">
        {actions.map(a => (
          <DropdownMenuItem key={a.id} onClick={() => {
            if (a.id==="file" || a.id==="picture") {
              const input = document.createElement('input');
              input.type='file';
              input.accept = a.id==="picture" ? 'image/*' : '*/*';
              input.onchange = (e:any)=>{ const f=e.target.files?.[0]; if(f && onFilePick) onFilePick(f); onSelect(a.id); };
              input.click();
            } else if (a.id==="camera") {
              const input = document.createElement('input');
              input.type='file'; input.accept='image/*'; (input as any).capture='environment';
              input.onchange = (e:any)=>{ const f=e.target.files?.[0]; if(f && onFilePick) onFilePick(f); onSelect(a.id); };
              input.click();
            } else onSelect(a.id);
          }} className="gap-2 py-2">
            <a.icon className="h-4 w-4" /> <div className="flex flex-col"><span className="text-sm">{a.label}</span><span className="text-xs text-zinc-500">{a.desc}</span></div>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export const plusPromptTemplates: Record<PlusAction,string> = {
  "camera":"[Camera] Analyze this photo and ",
  "picture":"[Image] Describe and use this image to ",
  "file":"[File attached] Use this file to ",
  "connect-computer":"Connect my computer with permission and ",
  "add-skills":"Browse and add a skill that can ",
  "build-website":"Build a website that ",
  "develop-apps":"Develop an application that ",
  "create-slides":"Create slides about ",
  "create-image":"Create an image of ",
  "edit-image":"Edit this image to ",
  "wide-research":"Wide Research: research and compare ",
  "scheduled-tasks":"Create a scheduled task: ",
  "create-spreadsheet":"Create a spreadsheet for ",
  "create-video":"Create a video about ",
  "generate-audio":"Generate audio for ",
  "create-document":"Create a document that ",
  "create-code":"Write code that ",
  "assign-agent":"Assign to an agent to ",
  "open-browser":"Open the browser and ",
  "playbook":"Create a playbook for ",
};
