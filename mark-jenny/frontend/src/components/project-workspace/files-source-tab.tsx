"use client";

import { useState, useEffect, useCallback } from "react";
import { Upload, Download, Search, Grid, List, MoreHorizontal, Eye, Globe, Trash2, Loader2, Image, Video, Music, FileText, Table, File as LucideFile } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { filesApi, File as ApiFile, FileType } from "@/lib/api/files";
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter, SheetClose,
} from "@/components/ui/sheet";
import { toast } from "@/components/ui/toast";

const categories: { value: string; label: string }[] = [
  { value: "All", label: "All" },
  { value: "Images", label: "Images" },
  { value: "Documents", label: "Documents" },
  { value: "Videos", label: "Videos" },
  { value: "Audios", label: "Audios" },
  { value: "Spreadsheets", label: "Spreadsheets" },
  { value: "Code", label: "Code" },
  { value: "Archive", label: "Archive" },
  { value: "Others", label: "Others" },
];

const getIcon = (type: string) => {
  switch (type) {
    case "Documents": return FileText;
    case "Images": return Image;
    case "Videos": return Video;
    case "Audios": return Music;
    case "Spreadsheets": return Table;
    case "Code": return FileText;
    case "Archive": return LucideFile;
    default: return LucideFile;
  }
};

const FileIcon = ({ type }: { type: string }) => {
  const Icon = getIcon(type);
  return <Icon className="h-12 w-12 text-zinc-400" />;
};

const FileIconSmall = ({ type }: { type: string }) => {
  const Icon = getIcon(type);
  return <Icon className="h-8 w-8 text-zinc-400" />;
};

const formatSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} GB`;
};

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString();
};

export function FilesSourceTab({ projectId }: { projectId: number }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState("All");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [files, setFiles] = useState<ApiFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 50;
const [categoriesData, setCategoriesData] = useState<{ value: string; label: string }[]>(categories);
  const [uploading, setUploading] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ApiFile | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchFiles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const fileType = activeCategory === "All" ? undefined : activeCategory as FileType;
      const response = await filesApi.listFiles({
        page,
        page_size: pageSize,
        search: searchQuery || undefined,
        file_type: fileType,
        project_id: projectId,
        sort_by: "created_at",
        sort_order: "desc",
      });
      setFiles(response.files);
      setTotal(response.total);
    } catch (err) {
      setError("Failed to load files");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, searchQuery, activeCategory, projectId]);

  const fetchCategories = useCallback(async () => {
    try {
      const data = await filesApi.getCategories();
      setCategoriesData(data);
    } catch (err) {
      console.error(err);
    }
  }, []);

  useEffect(() => {
    fetchFiles();
    fetchCategories();
  }, [fetchFiles, fetchCategories]);

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    setPage(1);
  };

  const handleCategoryChange = (value: string) => {
    setActiveCategory(value);
    setPage(1);
  };

const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setUploading(true);
    try {
      await filesApi.uploadFile(file, { project_id: projectId });
      fetchFiles();
      e.target.value = "";
      toast.add({ title: "Uploaded", description: file.name, type: "success" });
    } catch (err) {
      toast.add({ title: "Upload failed", type: "error" });
      console.error(err);
    } finally {
      setUploading(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await filesApi.deleteFile(deleteTarget.id);
      fetchFiles();
      toast.add({ title: "File deleted", type: "success" });
    } catch (err) {
      toast.add({ title: "Couldn't delete file", type: "error" });
      console.error(err);
    } finally {
      setDeleting(false);
      setDeleteTarget(null);
    }
  };

  const handleDownload = async (file: ApiFile) => {
    try {
      const blob = await filesApi.downloadFile(file.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.original_name;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.add({ title: "Downloaded", description: file.original_name, type: "success" });
    } catch (err) {
      toast.add({ title: "Download failed", type: "error" });
      console.error(err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-zinc-500">
        <p className="mb-4 text-red-600">{error}</p>
        <Button onClick={fetchFiles}>Retry</Button>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-4 gap-4">
        <div className="flex-1 max-w-md">
          <Input
            placeholder="Search files..."
            value={searchQuery}
            onChange={handleSearch}
          />
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor="file-upload" className="cursor-pointer">
            <Button variant="outline" size="sm" disabled={uploading}>
              <Upload className="mr-2 h-4 w-4" />
              {uploading ? "Uploading..." : "Upload"}
            </Button>
            <input
              id="file-upload"
              type="file"
              className="hidden"
              onChange={handleUpload}
              multiple
              disabled={uploading}
            />
          </label>
          <select
            value={activeCategory}
            onChange={(e) => handleCategoryChange(e.target.value)}
            className="px-3 py-1.5 text-sm border border-zinc-300 rounded-lg dark:border-zinc-600 dark:bg-zinc-800"
          >
            {categoriesData.map((cat) => <option key={cat.value} value={cat.value}>{cat.label}</option>)}
          </select>
          <Button variant="outline" size="sm" onClick={() => setViewMode("grid")}>
            <Grid className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={() => setViewMode("list")}>
            <List className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <Tabs defaultValue="project" className="flex-1 flex flex-col">
        <TabsList className="grid w-full grid-cols-2 mb-4 max-w-xs">
          <TabsTrigger value="project">Project Files</TabsTrigger>
          <TabsTrigger value="web">Web Resources</TabsTrigger>
        </TabsList>

        <TabsContent value="project" className="flex-1 flex flex-col">
          <div className="flex-1 overflow-auto">
            {viewMode === "grid" ? (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                {files.map((file) => (
                  <Card key={file.id} className="group">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-center h-24 mb-3">
                        <FileIcon type={file.file_type} />
                      </div>
                      <h4 className="font-medium text-sm truncate mb-1" title={file.original_name}>
                        {file.original_name}
                      </h4>
                      <div className="flex items-center justify-between text-xs text-zinc-500 mb-2">
                        <span>{formatSize(file.size)}</span>
                        <span>{formatDate(file.created_at)}</span>
                      </div>
                      <Badge variant="outline" className="text-xs">{file.file_type}</Badge>
<DropdownMenu className="mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
                        <DropdownMenuTrigger>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleDownload(file)}><Eye className="mr-2 h-4 w-4" />Preview</DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleDownload(file)}><Download className="mr-2 h-4 w-4" />Download</DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem className="text-red-600" onClick={() => setDeleteTarget(file)}><Trash2 className="mr-2 h-4 w-4" />Delete</DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="space-y-2">
                {files.map((file) => (
                  <Card key={file.id}>
                    <CardContent className="p-3">
                      <div className="flex items-center gap-4">
                        <FileIconSmall type={file.file_type} />
                        <div className="flex-1 min-w-0">
                          <h4 className="font-medium truncate">{file.original_name}</h4>
                          <p className="text-sm text-zinc-500">{formatSize(file.size)} • {formatDate(file.created_at)}</p>
                        </div>
                        <Badge variant="outline">{file.file_type}</Badge>
                        <DropdownMenu>
                          <DropdownMenuTrigger>
                            <Button variant="ghost" size="icon">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
<DropdownMenuItem onClick={() => handleDownload(file)}><Eye className="mr-2 h-4 w-4" />Preview</DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleDownload(file)}><Download className="mr-2 h-4 w-4" />Download</DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem className="text-red-600" onClick={() => setDeleteTarget(file)}><Trash2 className="mr-2 h-4 w-4" />Delete</DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
            {files.length === 0 && (
              <div className="flex-1 flex flex-col items-center justify-center text-zinc-500">
                <p className="mb-4">No files in this project</p>
                <label htmlFor="file-upload-empty" className="cursor-pointer">
                  <Button>
                    <Upload className="mr-2 h-4 w-4" />
                    Upload Files
                  </Button>
                  <input
                    id="file-upload-empty"
                    type="file"
                    className="hidden"
                    onChange={handleUpload}
                    multiple
                    disabled={uploading}
                  />
                </label>
              </div>
            )}
            {total > pageSize && (
              <div className="flex items-center justify-center gap-2 mt-4">
                <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}>
                  Previous
                </Button>
                <span className="text-sm text-zinc-500">Page {page} of {Math.ceil(total / pageSize)}</span>
                <Button variant="outline" size="sm" onClick={() => setPage(p => Math.min(Math.ceil(total / pageSize), p + 1))} disabled={page >= Math.ceil(total / pageSize)}>
                  Next
                </Button>
              </div>
            )}
          </div>
        </TabsContent>

<TabsContent value="web" className="flex-1 flex flex-col">
          <Card className="flex-1">
            <CardContent className="flex-1 p-6">
              <div className="text-center text-zinc-500">
                <Globe className="h-12 w-12 mx-auto mb-4 text-zinc-300" />
                <h3 className="text-lg font-medium mb-2">Web Resources</h3>
                <p className="mb-4">Add URLs, web pages, and online resources to this project</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Delete confirmation */}
      <Sheet open={!!deleteTarget} onOpenChange={(o) => { if (!o) setDeleteTarget(null); }}>
        <SheetContent side="bottom" className="mx-auto max-w-md rounded-t-2xl">
          <SheetHeader>
            <SheetTitle>Delete this file?</SheetTitle>
            <SheetDescription>“{deleteTarget?.original_name || "File"}” will be permanently removed from this project.</SheetDescription>
          </SheetHeader>
          <SheetFooter>
            <SheetClose render={<Button variant="outline" />}>Cancel</SheetClose>
            <Button variant="destructive" onClick={confirmDelete} disabled={deleting}>
              {deleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Delete
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </div>
  );
}
