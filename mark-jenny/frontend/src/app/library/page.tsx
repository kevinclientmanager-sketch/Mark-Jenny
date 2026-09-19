"use client";
import { useState, useEffect, useRef } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ProtectedLayout } from "@/components/layout/protected-layout";
import { filesApi, FileType } from "@/lib/api/files";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Search, Library as LibraryIcon, FileText, FolderOpen, Loader2, Upload, Download, Trash2,
  Globe, AppWindow, Image as ImageIcon, Film, Music, Table, ChevronLeft, Folder, FileCode
} from "lucide-react";
import type { File as APIFile } from "@/lib/api/files";
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter, SheetClose,
} from "@/components/ui/sheet";
import { toast } from "@/components/ui/toast";

interface FolderDef {
  id: string;
  label: string;
  icon: typeof Folder;
  fileTypes: FileType[];
  subGroup?: (f: APIFile) => string;
}

const FOLDERS: FolderDef[] = [
  { id: "websites", label: "Websites", icon: Globe, fileTypes: ["WEBSITE"] },
  { id: "apps", label: "Apps", icon: AppWindow, fileTypes: ["CODE"], subGroup: (f) => f.original_name?.toLowerCase().includes("win") || f.original_name?.toLowerCase().includes(".exe") ? "windows" : "web" },
  { id: "documents", label: "Documents", icon: FileText, fileTypes: ["DOCUMENT"] },
  { id: "images", label: "Images", icon: ImageIcon, fileTypes: ["IMAGE"] },
  { id: "videos", label: "Videos", icon: Film, fileTypes: ["VIDEO"] },
  { id: "audio", label: "Audio", icon: Music, fileTypes: ["AUDIO"] },
  { id: "spreadsheets", label: "Spreadsheets", icon: Table, fileTypes: ["SPREADSHEET"] },
  { id: "code", label: "Code", icon: FileCode, fileTypes: ["CODE"] },
];

const FILE_ICONS: Record<string, typeof FileText> = {
  IMAGE: ImageIcon, DOCUMENT: FileText, VIDEO: Film, AUDIO: Music,
  SPREADSHEET: Table, CODE: FileCode, WEBSITE: Globe, ARCHIVE: FolderOpen, OTHER: FileText,
};

const APP_GROUPS = [
  { id: "web", label: "Web App", icon: Globe },
  { id: "windows", label: "Windows App", icon: AppWindow },
];

export default function LibraryPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [files, setFiles] = useState<APIFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [uploading, setUploading] = useState(false);
  const [activeFolder, setActiveFolder] = useState<string | null>(null);
  const [activeSubGroup, setActiveSubGroup] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<APIFile | null>(null);
  const [deleting, setDeleting] = useState(false);
  const uploadRef = useRef<HTMLInputElement>(null);

  const fetchFiles = async () => {
    setLoading(true);
    try {
      const res = await filesApi.listFiles({ page: 1, page_size: 200 });
      setFiles(res.files || []);
    } catch { setFiles([]); } finally { setLoading(false); }
  };

  useEffect(() => { fetchFiles(); }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try { await filesApi.uploadFile(file); fetchFiles(); toast.add({ title: "Uploaded", description: file.name, type: "success" }); }
    catch (err) { toast.add({ title: "Upload failed", type: "error" }); console.error(err); } finally { setUploading(false); e.target.value = ""; }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await filesApi.deleteFile(deleteTarget.id);
      fetchFiles();
      toast.add({ title: "File deleted", type: "success" });
    } catch {
      toast.add({ title: "Couldn't delete file", type: "error" });
    } finally {
      setDeleting(false);
      setDeleteTarget(null);
    }
  };

  const handleDownload = (file: APIFile) => {
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    window.open(`${API_BASE}/files/${file.id}/download`, "_blank");
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const searchFiltered = files.filter(f =>
    !search || f.original_name?.toLowerCase().includes(search.toLowerCase()) || f.file_type?.toLowerCase().includes(search.toLowerCase())
  );

  const counts: Record<string, number> = {};
  FOLDERS.forEach(folder => {
    counts[folder.id] = searchFiltered.filter(f => folder.fileTypes.includes(f.file_type)).length;
  });

  const activeFolderDef = FOLDERS.find(f => f.id === activeFolder) || null;

  const openFolder = (folderId: string) => { setActiveFolder(folderId); setActiveSubGroup(null); };

  const renderFileCard = (f: APIFile) => {
    const FileIcon = FILE_ICONS[f.file_type] || FileText;
    return (
      <Card key={f.id} className="hover:shadow-md transition-shadow">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg shrink-0">
              <FileIcon className="h-5 w-5 text-blue-500" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="font-medium text-sm truncate" title={f.original_name}>{f.original_name}</p>
              <div className="flex flex-wrap gap-1.5 mt-1">
                <Badge variant="outline" className="text-[10px]">{f.file_type}</Badge>
                <span className="text-[10px] text-zinc-400">{formatSize(f.size)}</span>
                <span className="text-[10px] text-zinc-400">{new Date(f.created_at).toLocaleDateString()}</span>
              </div>
              {f.project_id && <Badge variant="secondary" className="text-[10px] mt-1">Project #{f.project_id}</Badge>}
            </div>
          </div>
          <div className="flex gap-1 mt-3 justify-end">
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleDownload(f)} title="Download">
              <Download className="h-3.5 w-3.5" />
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setDeleteTarget(f)} title="Delete">
              <Trash2 className="h-3.5 w-3.5 text-red-500" />
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <ProtectedLayout>
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex">
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <div className={`flex-1 flex flex-col min-w-0 transition-all ${sidebarOpen ? "ml-64" : "ml-16"}`}>
          <Header />
          <main className="flex-1 p-6 overflow-auto">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h1 className="text-2xl font-semibold flex items-center gap-2"><LibraryIcon className="h-6 w-6" /> Library</h1>
                <p className="text-sm text-zinc-500">{files.length} files — organized into folders by type</p>
              </div>
              <Button onClick={() => uploadRef.current?.click()} disabled={uploading}>
                {uploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
                {uploading ? "Uploading..." : "Upload"}
              </Button>
              <input ref={uploadRef} type="file" className="hidden" onChange={handleUpload} />
            </div>

            <div className="mb-4 max-w-md relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-zinc-400" />
              <Input placeholder="Search files..." value={search} onChange={e => setSearch(e.target.value)} className="pl-8" />
            </div>

            {loading ? (
              <div className="flex justify-center p-8"><Loader2 className="h-6 w-6 animate-spin" /></div>
            ) : activeFolder === null ? (
              /* Folder dashboard */
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {FOLDERS.map(folder => {
                  const Icon = folder.icon;
                  const count = counts[folder.id];
                  return (
                    <Card key={folder.id} className="cursor-pointer hover:shadow-md hover:border-blue-300 dark:hover:border-blue-700 transition-all group">
                      <CardContent className="p-5 flex flex-col items-center text-center">
                        <div className="p-4 bg-blue-100/70 dark:bg-blue-900/20 rounded-xl mb-3 group-hover:scale-105 transition-transform">
                          <Icon className="h-10 w-10 text-blue-600 dark:text-blue-400" />
                        </div>
                        <p className="font-medium text-lg">{folder.label}</p>
                        <p className="text-sm text-zinc-500">{count} item{count !== 1 ? "s" : ""}</p>
                        <Button className="mt-3" size="sm" variant={count > 0 ? "default" : "outline"} onClick={() => openFolder(folder.id)}>
                          Open Folder
                        </Button>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            ) : activeFolderDef ? (
              /* Inside a folder */
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <Button variant="outline" size="sm" onClick={() => { setActiveFolder(null); setActiveSubGroup(null); }}>
                    <ChevronLeft className="h-4 w-4" /> All Folders
                  </Button>
                  <IconWrap icon={activeFolderDef.icon} />
                  <h2 className="text-xl font-semibold">{activeFolderDef.label} Folder</h2>
                </div>

                {activeFolder === "apps" ? (
                  /* Apps folder: split Web App | Windows App with sub-folders */
                  activeSubGroup === null ? (
                    <div className="grid gap-4 md:grid-cols-2">
                      {APP_GROUPS.map(g => {
                        const Icon = g.icon;
                        const groupFiles = files.filter(f => activeFolderDef!.fileTypes.includes(f.file_type) && activeFolderDef!.subGroup!(f) === g.id);
                        return (
                          <Card key={g.id} className="cursor-pointer hover:shadow-md transition-all group">
                            <CardContent className="p-6 flex flex-col items-center text-center">
                              <div className="p-4 bg-blue-100/70 dark:bg-blue-900/20 rounded-xl mb-3 group-hover:scale-105 transition-transform">
                                <Icon className="h-10 w-10 text-blue-600 dark:text-blue-400" />
                              </div>
                              <p className="font-medium text-lg">{g.label}</p>
                              <p className="text-sm text-zinc-500">{groupFiles.length} item{groupFiles.length !== 1 ? "s" : ""}</p>
                              <Button className="mt-3" size="sm" variant={groupFiles.length > 0 ? "default" : "outline"} onClick={() => setActiveSubGroup(g.id)}>
                                Open Folder
                              </Button>
                            </CardContent>
                          </Card>
                        );
                      })}
                    </div>
                  ) : (
                    <div>
                      <Button variant="ghost" size="sm" onClick={() => setActiveSubGroup(null)}><ChevronLeft className="h-4 w-4" /> {activeFolderDef.label} sub-folders</Button>
                      <h3 className="text-lg font-medium mt-2 mb-3">{activeSubGroup === "web" ? "Web App" : "Windows App"}</h3>
                      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                        {files.filter(f => activeFolderDef!.fileTypes.includes(f.file_type) && activeFolderDef!.subGroup!(f) === activeSubGroup).map(renderFileCard)}
                        {files.filter(f => activeFolderDef!.fileTypes.includes(f.file_type) && activeFolderDef!.subGroup!(f) === activeSubGroup).length === 0 && (
                          <p className="text-zinc-500 col-span-3 text-center py-8">No files in this folder yet.</p>
                        )}
                      </div>
                    </div>
                  )
                ) : (
                  /* Regular folder contents */
                  <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                    {files.filter(f => activeFolderDef.fileTypes.includes(f.file_type)).map(renderFileCard)}
                    {files.filter(f => activeFolderDef.fileTypes.includes(f.file_type)).length === 0 && (
                      <p className="text-zinc-500 col-span-3 text-center py-8">No files in this folder yet.</p>
                    )}
                  </div>
                )}
              </div>
            ) : null}
          </main>
        </div>
      </div>

      <Sheet open={!!deleteTarget} onOpenChange={(o) => { if (!o) setDeleteTarget(null); }}>
        <SheetContent side="bottom" className="mx-auto max-w-md rounded-t-2xl">
          <SheetHeader>
            <SheetTitle>Delete this file?</SheetTitle>
            <SheetDescription>“{deleteTarget?.original_name || "File"}” will be permanently removed from your library.</SheetDescription>
          </SheetHeader>
          <SheetFooter>
            <SheetClose render={<Button variant="outline" />}>Cancel</SheetClose>
            <Button variant="destructive" onClick={confirmDelete} disabled={deleting}>
              {deleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Delete
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </ProtectedLayout>
  );
}

function IconWrap({ icon: IconComponent }: { icon: any }) {
  return (
    <div className="p-1.5 bg-blue-100/70 dark:bg-blue-900/20 rounded-lg">
      <IconComponent className="h-5 w-5 text-blue-600 dark:text-blue-400" />
    </div>
  );
}
