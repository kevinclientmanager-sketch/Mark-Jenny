"use client";

import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { useSettingsOpen, setSettingsOpen } from "@/lib/nav/settings-store";
import { Settings as SettingsIcon } from "lucide-react";
import { SettingsContent } from "@/components/settings/settings-content";

export function SettingsDialog() {
  const open = useSettingsOpen();

  return (
    <Sheet open={open} onOpenChange={setSettingsOpen}>
      <SheetContent
        className="w-full h-full gap-0"
        style={{ width: "45vw", maxWidth: "45vw", minWidth: "360px" }}
        overlayClassName="bg-black/15 backdrop-blur-[2px]"
      >
        <SheetHeader className="px-4 pt-9 pb-2">
          <SheetTitle className="flex items-center gap-2 text-xl">
            <SettingsIcon className="h-5 w-5" /> Settings
          </SheetTitle>
        </SheetHeader>
        <div className="flex-1 min-h-0 overflow-hidden pl-1.5 pr-4 pb-2">
          <SettingsContent key={open ? "open" : "closed"} />
        </div>
      </SheetContent>
    </Sheet>
  );
}

