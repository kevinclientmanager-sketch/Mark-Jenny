import { api } from './client';

export interface InstructionVersion {
  id: number;
  project_id: number;
  content: string;
  version: number;
  created_by: number;
  created_at: string;
}

export interface InstructionResponse {
  project_id: number;
  content: string;
  updated_at: string | null;
  versions: InstructionVersion[];
}

export interface Connector {
  id: number;
  name: string;
  display_name: string;
  type: string;
  description: string | null;
  icon: string | null;
  config_schema: Record<string, unknown> | null;
  is_system: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface ConnectorCredential {
  id: number;
  connector_id: number;
  connector_name: string;
  connector_type: string;
  project_id: number | null;
  auth_type: string;
  status: string;
  expires_at: string | null;
  last_sync_at: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface ConnectConnectorData {
  connector_id: number;
  project_id?: number;
  auth_type: string;
  credentials: Record<string, unknown>;
}

export interface CustomAPIConnectorCreate {
  name: string;
  base_url: string;
  auth_type: string;
  api_key?: string;
  bearer_token?: string;
  headers: Record<string, string>;
  project_id?: number;
}

export interface CustomAPIConnector {
  id: number;
  name: string;
  base_url: string;
  auth_type: string;
  project_id: number | null;
  created_at: string;
}

export interface MCPConfigCreate {
  name: string;
  command: string;
  args: string[];
  env: Record<string, string>;
  project_id?: number;
}

export interface MCPConfig {
  id: number;
  name: string;
  command: string;
  args: string[];
  env: Record<string, string>;
  project_id: number | null;
  created_at: string;
}

export const projectWorkspaceApi = {
  // Instructions
  getInstructions: async (projectId: number): Promise<InstructionResponse> => {
    return api.get<InstructionResponse>(`/projects/${projectId}/instructions`);
  },

  updateInstructions: async (projectId: number, content: string): Promise<InstructionResponse> => {
    return api.patch<InstructionResponse>(`/projects/${projectId}/instructions`, { content });
  },

  listInstructionVersions: async (projectId: number): Promise<InstructionVersion[]> => {
    return api.get<InstructionVersion[]>(`/projects/${projectId}/instructions/versions`);
  },

  restoreInstructionVersion: async (projectId: number, versionId: number): Promise<{ message: string }> => {
    return api.post<{ message: string }>(`/projects/${projectId}/instructions/versions/${versionId}/restore`, {});
  },

  // Connectors
  listConnectors: async (): Promise<Connector[]> => {
    return api.get<Connector[]>('/connectors');
  },

  getConnector: async (id: number): Promise<Connector> => {
    return api.get<Connector>(`/connectors/${id}`);
  },

  listProjectConnectors: async (projectId: number): Promise<ConnectorCredential[]> => {
    return api.get<ConnectorCredential[]>(`/projects/${projectId}/connectors`);
  },

  listUserConnectors: async (): Promise<ConnectorCredential[]> => {
    return api.get<ConnectorCredential[]>('/connectors/user');
  },

  connectConnector: async (data: ConnectConnectorData): Promise<ConnectorCredential> => {
    return api.post<ConnectorCredential>('/connectors/connect', data);
  },

  updateConnectorCredential: async (id: number, data: {
    credentials?: Record<string, unknown>;
    auth_type?: string;
  }): Promise<ConnectorCredential> => {
    return api.patch<ConnectorCredential>(`/connectors/credentials/${id}`, data);
  },

  refreshConnector: async (id: number): Promise<{ message: string }> => {
    return api.post<{ message: string }>(`/connectors/credentials/${id}/refresh`, {});
  },

  disconnectConnector: async (id: number): Promise<{ message: string }> => {
    return api.post<{ message: string }>(`/connectors/credentials/${id}/disconnect`, {});
  },

  deleteConnectorCredential: async (id: number): Promise<{ message: string }> => {
    return api.delete<{ message: string }>(`/connectors/credentials/${id}`);
  },

  // Custom API Connectors
  createCustomAPIConnector: async (data: CustomAPIConnectorCreate): Promise<CustomAPIConnector> => {
    return api.post<CustomAPIConnector>('/connectors/custom-api', data);
  },

  listCustomAPIConnectors: async (projectId?: number): Promise<CustomAPIConnector[]> => {
    const params = projectId ? `?project_id=${projectId}` : '';
    return api.get<CustomAPIConnector[]>(`/connectors/custom-api${params}`);
  },

  // MCP Configurations
  createMCPConfig: async (data: MCPConfigCreate): Promise<MCPConfig> => {
    return api.post<MCPConfig>('/connectors/mcp', data);
  },

  listMCPConfigs: async (projectId?: number): Promise<MCPConfig[]> => {
    const params = projectId ? `?project_id=${projectId}` : '';
    return api.get<MCPConfig[]>(`/connectors/mcp${params}`);
  },
};