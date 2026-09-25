"use client";
import { useState } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ProtectedLayout } from "@/components/layout/protected-layout";
import { Settings } from "lucide-react";
import { SettingsContent } from "@/components/settings/settings-content";

export default function SettingsPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <ProtectedLayout>
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex">
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <div className={`flex-1 flex flex-col min-w-0 transition-all ${sidebarOpen ? "ml-64" : "ml-16"}`}>
          <Header />
          <main className="flex-1 p-6 overflow-auto max-w-5xl mx-auto">
            <h1 className="text-2xl font-semibold flex items-center gap-2 mb-6"><Settings className="h-6 w-6" /> Settings</h1>
            <SettingsContent />
          </main>
        </div>
      </div>
    </ProtectedLayout>
  );
}


