"use client";

import { useState, useEffect, useCallback } from "react";
import { Plus, MoreHorizontal, RefreshCw, Unlink2, Loader2, Globe, Key, Terminal, Shield, CheckCircle, AlertCircle, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { projectWorkspaceApi, Connector, ConnectorCredential, CustomAPIConnector, MCPConfig } from "@/lib/api/projectWorkspace";
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter, SheetClose,
} from "@/components/ui/sheet";
import { toast } from "@/components/ui/toast";

export function ConnectorsTab({ projectId }: { projectId: number }) {
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [projectConnectors, setProjectConnectors] = useState<ConnectorCredential[]>([]);
  const [userConnectors, setUserConnectors] = useState<ConnectorCredential[]>([]);
  const [customApis, setCustomApis] = useState<CustomAPIConnector[]>([]);
  const [mcpConfigs, setMcpConfigs] = useState<MCPConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"browse" | "project" | "custom" | "mcp">("browse");
  const [showConnectModal, setShowConnectModal] = useState<{ connector?: Connector; projectId?: number } | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [confirmTarget, setConfirmTarget] = useState<{ id: number; action: "disconnect" | "delete" } | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [showCustomForm, setShowCustomForm] = useState(false);
  const [customForm, setCustomForm] = useState({ name: "", base_url: "", api_key: "" });
  const [showMcpForm, setShowMcpForm] = useState(false);
  const [mcpForm, setMcpForm] = useState({ name: "", command: "npx", args: "" });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [connectorsData, projectConnectorsData, userConnectorsData, customApisData, mcpConfigsData] = await Promise.all([
        projectWorkspaceApi.listConnectors(),
        projectWorkspaceApi.listProjectConnectors(projectId),
        projectWorkspaceApi.listUserConnectors(),
        projectWorkspaceApi.listCustomAPIConnectors(projectId),
        projectWorkspaceApi.listMCPConfigs(projectId),
      ]);
      setConnectors(connectorsData);
      setProjectConnectors(projectConnectorsData);
      setUserConnectors(userConnectorsData);
      setCustomApis(customApisData);
      setMcpConfigs(mcpConfigsData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleConnect = async (connector: Connector, projectId?: number) => {
    if (!connector.config_schema) {
      setShowConnectModal({ connector, projectId });
      return;
    }
    // For connectors that need credentials, show modal
    setShowConnectModal({ connector, projectId });
  };

  const handleConnectSubmit = async (credentials: Record<string, unknown>) => {
    if (!showConnectModal?.connector) return;
    setConnecting(true);
    try {
      await projectWorkspaceApi.connectConnector({
        connector_id: showConnectModal.connector.id,
        project_id: showConnectModal.projectId,
        auth_type: "API_KEY",
        credentials,
      });
      setShowConnectModal(null);
      fetchData();
      toast.add({ title: "Connected", description: showConnectModal.connector.display_name || showConnectModal.connector.name, type: "success" });
    } catch (err) {
      toast.add({ title: "Failed to connect", type: "error" });
      console.error(err);
    } finally {
      setConnecting(false);
    }
  };

  const handleRefresh = async (credentialId: number) => {
    try {
      await projectWorkspaceApi.refreshConnector(credentialId);
      fetchData();
      toast.add({ title: "Connector refreshed", type: "success" });
    } catch (err) {
      toast.add({ title: "Failed to refresh", type: "error" });
      console.error(err);
    }
  };

  const handleDisconnect = async (credentialId: number) => {
    setConfirmTarget({ id: credentialId, action: "disconnect" });
  };

  const handleDelete = async (credentialId: number) => {
    setConfirmTarget({ id: credentialId, action: "delete" });
  };

  const confirmAction = async () => {
    if (!confirmTarget) return;
    setConfirming(true);
    try {
      if (confirmTarget.action === "disconnect") await projectWorkspaceApi.disconnectConnector(confirmTarget.id);
      else await projectWorkspaceApi.deleteConnectorCredential(confirmTarget.id);
      fetchData();
      toast.add({ title: confirmTarget.action === "disconnect" ? "Connector disconnected" : "Credential deleted", type: "success" });
    } catch (err) {
      toast.add({ title: confirmTarget.action === "disconnect" ? "Failed to disconnect" : "Failed to delete credential", type: "error" });
      console.error(err);
    } finally {
      setConfirming(false);
      setConfirmTarget(null);
    }
  };

  const handleCreateCustomApi = async (data: { name: string; base_url: string; auth_type: string; api_key?: string; bearer_token?: string; headers: Record<string, string> }) => {
    try {
      await projectWorkspaceApi.createCustomAPIConnector({ ...data, project_id: projectId });
      fetchData();
      toast.add({ title: "Custom API connector created", description: data.name, type: "success" });
    } catch (err) {
      toast.add({ title: "Failed to create custom API connector", type: "error" });
      console.error(err);
    }
  };

  const handleCreateMcp = async (data: { name: string; command: string; args: string[]; env: Record<string, string> }) => {
    try {
      await projectWorkspaceApi.createMCPConfig({ ...data, project_id: projectId });
      fetchData();
      toast.add({ title: "MCP config created", description: data.name, type: "success" });
    } catch (err) {
      toast.add({ title: "Failed to create MCP config", type: "error" });
      console.error(err);
    }
  };

  const submitCustomForm = async () => {
    if (!customForm.name.trim() || !customForm.base_url.trim()) {
      toast.add({ title: "Name and Base URL required", type: "error" });
      return;
    }
    await handleCreateCustomApi({
      name: customForm.name.trim(),
      base_url: customForm.base_url.trim(),
      auth_type: "API_KEY",
      api_key: customForm.api_key.trim() || undefined,
      headers: {},
    });
    setShowCustomForm(false);
    setCustomForm({ name: "", base_url: "", api_key: "" });
  };

  const submitMcpForm = async () => {
    if (!mcpForm.name.trim() || !mcpForm.command.trim()) {
      toast.add({ title: "Name and Command required", type: "error" });
      return;
    }
    await handleCreateMcp({
      name: mcpForm.name.trim(),
      command: mcpForm.command.trim(),
      args: mcpForm.args.split(" ").filter(Boolean),
      env: {},
    });
    setShowMcpForm(false);
    setMcpForm({ name: "", command: "npx", args: "" });
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "CONNECTED": return <Badge variant="default" className="bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"><CheckCircle className="mr-1 h-3 w-3 inline" /> Connected</Badge>;
      case "CONNECTING": return <Badge variant="default" className="bg-yellow-100 text-yellow-700"><Loader2 className="mr-1 h-3 w-3 animate-spin inline" /> Connecting</Badge>;
      case "EXPIRED": return <Badge variant="destructive"><AlertCircle className="mr-1 h-3 w-3 inline" /> Expired</Badge>;
      case "ERROR": return <Badge variant="destructive"><AlertCircle className="mr-1 h-3 w-3 inline" /> Error</Badge>;
      default: return <Badge variant="secondary"><Unlink2 className="mr-1 h-3 w-3 inline" /> Not Connected</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-semibold">Connectors & Integrations</h2>
          <p className="text-zinc-500 text-sm">Manage external services and API connections</p>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
        <TabsList className="grid w-full grid-cols-4 mb-4">
          <TabsTrigger value="browse">
            <Globe className="mr-2 h-4 w-4" />
            Browse
          </TabsTrigger>
          <TabsTrigger value="project">
            <Shield className="mr-2 h-4 w-4" />
            Project
          </TabsTrigger>
          <TabsTrigger value="custom">
            <Key className="mr-2 h-4 w-4" />
            Custom API
          </TabsTrigger>
          <TabsTrigger value="mcp">
            <Terminal className="mr-2 h-4 w-4" />
            MCP
          </TabsTrigger>
        </TabsList>

        <TabsContent value="browse" className="flex-1 overflow-auto">
          <div className="space-y-4">
            {connectors.map((connector) => {
              const projectCred = projectConnectors.find(c => c.connector_id === connector.id);
              const userCred = userConnectors.find(c => c.connector_id === connector.id);
              const cred = projectCred || userCred;
              const isConnected = cred?.status === "CONNECTED";
              
              return (
                <Card key={connector.id}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900/30">
                          {connector.icon ? (
                            <span className="text-2xl">{connector.icon}</span>
                          ) : (
                            <Globe className="h-6 w-6 text-blue-600" />
                          )}
                        </div>
                        <div>
                          <h4 className="font-medium">{connector.display_name || connector.name}</h4>
                          <p className="text-sm text-zinc-500">{connector.description || "No description"}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {getStatusBadge(cred?.status || "NOT_CONNECTED")}
                        {cred ? (
                          <>
                            <Button variant="outline" size="sm" onClick={() => handleRefresh(cred.id)}>
                              <RefreshCw className="mr-2 h-4 w-4" />
                              Refresh
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleDisconnect(cred.id)}>
                              <Unlink2 className="mr-2 h-4 w-4" />
                              Disconnect
                            </Button>
                          </>
                        ) : (
                          <Button size="sm" onClick={() => handleConnect(connector, projectId)}>
                            <Plus className="mr-2 h-4 w-4" />
                            Connect
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>

        <TabsContent value="project" className="flex-1 overflow-auto">
          {projectConnectors.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-zinc-500">
              <p className="mb-4">No connectors configured for this project</p>
              <Button onClick={() => setActiveTab("browse")}>
                <Plus className="mr-2 h-4 w-4" />
                Browse Connectors
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {projectConnectors.map((cred) => {
                const connector = connectors.find(c => c.id === cred.connector_id);
                return (
                  <Card key={cred.id}>
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900/30">
                            {connector?.icon ? (
                              <span className="text-xl">{connector.icon}</span>
                            ) : (
                              <Globe className="h-5 w-5 text-blue-600" />
                            )}
                          </div>
                          <div>
                            <h4 className="font-medium">{connector?.display_name || connector?.name || "Unknown"}</h4>
                            <p className="text-sm text-zinc-500">Project-level connection</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {getStatusBadge(cred.status)}
                          <Button variant="outline" size="sm" onClick={() => handleRefresh(cred.id)}>
                            <RefreshCw className="mr-2 h-4 w-4" />
                            Refresh
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleDisconnect(cred.id)}>
                            <Unlink2 className="mr-2 h-4 w-4" />
                            Disconnect
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </TabsContent>

        <TabsContent value="custom" className="flex-1 overflow-auto">
          <div className="mb-4 flex justify-between items-center">
            <h3 className="text-lg font-medium">Custom API Connectors</h3>
            <Button onClick={() => setShowCustomForm(true)}>
              <Plus className="mr-2 h-4 w-4" />
              New Custom API
            </Button>
          </div>
          {customApis.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-zinc-500">
              <Key className="h-12 w-12 mb-4 text-zinc-300" />
              <p className="mb-4">No custom API connectors configured</p>
              <Button variant="outline" onClick={() => setShowCustomForm(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Create Custom API Connector
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {customApis.map((api) => (
                <Card key={api.id}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-900/30">
                          <Key className="h-5 w-5 text-purple-600" />
                        </div>
                        <div>
                          <h4 className="font-medium">{api.name}</h4>
                          <p className="text-sm text-zinc-500">{api.base_url}</p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="mcp" className="flex-1 overflow-auto">
          <div className="mb-4 flex justify-between items-center">
            <h3 className="text-lg font-medium">MCP Configurations</h3>
            <Button onClick={() => setShowMcpForm(true)}>
              <Plus className="mr-2 h-4 w-4" />
              New MCP Config
            </Button>
          </div>
          {mcpConfigs.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-zinc-500">
              <Terminal className="h-12 w-12 mb-4 text-zinc-300" />
              <p className="mb-4">No MCP configurations</p>
              <Button variant="outline" onClick={() => setShowMcpForm(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Create MCP Configuration
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {mcpConfigs.map((config) => (
                <Card key={config.id}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100 dark:bg-green-900/30">
                          <Terminal className="h-5 w-5 text-green-600" />
                        </div>
                        <div>
                          <h4 className="font-medium">{config.name}</h4>
                          <p className="text-sm text-zinc-500 font-mono text-xs">{config.command} {config.args.join(" ")}</p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Disconnect / delete confirmation */}
      <Sheet open={!!confirmTarget} onOpenChange={(o) => { if (!o) setConfirmTarget(null); }}>
        <SheetContent side="bottom" className="mx-auto max-w-md rounded-t-2xl">
          <SheetHeader>
            <SheetTitle>{confirmTarget?.action === "disconnect" ? "Disconnect this connector?" : "Delete this credential?"}</SheetTitle>
            <SheetDescription>
              {confirmTarget?.action === "disconnect"
                ? "This connector will be disconnected from the project."
                : "This connector credential will be permanently deleted."}
            </SheetDescription>
          </SheetHeader>
          <SheetFooter>
            <SheetClose render={<Button variant="outline" />}>Cancel</SheetClose>
            <Button variant="destructive" onClick={confirmAction} disabled={confirming}>
              {confirming && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}{confirmTarget?.action === "disconnect" ? "Disconnect" : "Delete"}
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      {/* New custom API connector */}
      <Sheet open={showCustomForm} onOpenChange={(o) => { if (!o) setShowCustomForm(false); }}>
        <SheetContent side="bottom" className="mx-auto max-w-md rounded-t-2xl">
          <SheetHeader>
            <SheetTitle>New Custom API Connector</SheetTitle>
            <SheetDescription>Define any REST API and connect it to this project.</SheetDescription>
          </SheetHeader>
          <div className="space-y-3 px-4">
            <div>
              <label className="text-sm font-medium">Name *</label>
              <Input value={customForm.name} onChange={e => setCustomForm({ ...customForm, name: e.target.value })} placeholder="My CRM API" autoFocus />
            </div>
            <div>
              <label className="text-sm font-medium">Base URL *</label>
              <Input value={customForm.base_url} onChange={e => setCustomForm({ ...customForm, base_url: e.target.value })} placeholder="https://api.example.com" />
            </div>
            <div>
              <label className="text-sm font-medium">API Key (encrypted)</label>
              <Input value={customForm.api_key} onChange={e => setCustomForm({ ...customForm, api_key: e.target.value })} placeholder="sk-..." type="password" />
            </div>
          </div>
          <SheetFooter>
            <SheetClose render={<Button variant="outline" />}>Cancel</SheetClose>
            <Button onClick={submitCustomForm} disabled={!customForm.name.trim() || !customForm.base_url.trim()}>
              Create
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      {/* New MCP config */}
      <Sheet open={showMcpForm} onOpenChange={(o) => { if (!o) setShowMcpForm(false); }}>
        <SheetContent side="bottom" className="mx-auto max-w-md rounded-t-2xl">
          <SheetHeader>
            <SheetTitle>New MCP Config</SheetTitle>
            <SheetDescription>Configure a local MCP server process for this project.</SheetDescription>
          </SheetHeader>
          <div className="space-y-3 px-4">
            <div>
              <label className="text-sm font-medium">Name *</label>
              <Input value={mcpForm.name} onChange={e => setMcpForm({ ...mcpForm, name: e.target.value })} placeholder="my-mcp-server" autoFocus />
            </div>
            <div>
              <label className="text-sm font-medium">Command *</label>
              <Input value={mcpForm.command} onChange={e => setMcpForm({ ...mcpForm, command: e.target.value })} placeholder="npx" />
            </div>
            <div>
              <label className="text-sm font-medium">Args (space separated)</label>
              <Input value={mcpForm.args} onChange={e => setMcpForm({ ...mcpForm, args: e.target.value })} placeholder="-y @modelcontextprotocol/server-filesystem /tmp" />
            </div>
          </div>
          <SheetFooter>
            <SheetClose render={<Button variant="outline" />}>Cancel</SheetClose>
            <Button onClick={submitMcpForm} disabled={!mcpForm.name.trim() || !mcpForm.command.trim()}>
              Create
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </div>
  );
}