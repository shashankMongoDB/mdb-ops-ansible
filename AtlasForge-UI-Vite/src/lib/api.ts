import axios, { AxiosError } from 'axios';
import { config } from './config';
import type {
  Tenant,
  Deployment,
  CreateTenantRequest,
  CreateDeploymentRequest,
  ConnectionInfo,
  PrometheusConfig,
  ApiError,
} from './types';

const api = axios.create({
  baseURL: config.apiBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
});

const handleError = (error: unknown): never => {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail: string }>;
    const apiError: ApiError = {
      detail: axiosError.response?.data?.detail || axiosError.message || 'An error occurred',
      status: axiosError.response?.status,
    };
    throw apiError;
  }
  throw { detail: 'An unexpected error occurred' };
};

// Tenants API
export const tenantsApi = {
  async getAll(): Promise<Tenant[]> {
    try {
      const response = await api.get<Tenant[]>('/tenants');
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async getById(tenantId: string): Promise<Tenant> {
    try {
      const response = await api.get<Tenant>(`/tenants/${tenantId}`);
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async create(data: CreateTenantRequest): Promise<Tenant> {
    try {
      const response = await api.post<Tenant>('/tenants', data);
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async delete(tenantId: string): Promise<void> {
    try {
      await api.delete(`/tenants/${tenantId}`);
    } catch (error) {
      return handleError(error);
    }
  },
};

// Deployments API
export const deploymentsApi = {
  async getAllForTenant(tenantId: string): Promise<Deployment[]> {
    try {
      const response = await api.get<Deployment[]>(`/tenants/${tenantId}/deployments`);
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async getById(tenantId: string, deploymentId: string): Promise<Deployment> {
    try {
      const response = await api.get<Deployment>(`/tenants/${tenantId}/deployments/${deploymentId}`);
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async create(tenantId: string, data: CreateDeploymentRequest): Promise<Deployment> {
    try {
      const response = await api.post<Deployment>(`/tenants/${tenantId}/deployments`, data);
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async delete(tenantId: string, deploymentId: string): Promise<void> {
    try {
      await api.delete(`/tenants/${tenantId}/deployments/${deploymentId}`);
    } catch (error) {
      return handleError(error);
    }
  },

  async getConnectionInfo(tenantId: string, deploymentId: string): Promise<ConnectionInfo> {
    try {
      const response = await api.get<ConnectionInfo>(`/tenants/${tenantId}/deployments/${deploymentId}/connection`);
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async scale(tenantId: string, deploymentId: string, members: number): Promise<Deployment> {
    try {
      const response = await api.patch<Deployment>(`/tenants/${tenantId}/deployments/${deploymentId}/scale`, { members });
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async upgradeVersion(tenantId: string, deploymentId: string, mongoVersion: string): Promise<Deployment> {
    try {
      const response = await api.patch<Deployment>(`/tenants/${tenantId}/deployments/${deploymentId}/version`, { mongoVersion });
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async shutdown(tenantId: string, deploymentId: string): Promise<void> {
    try {
      await api.post(`/tenants/${tenantId}/deployments/${deploymentId}/actions/shutdown`);
    } catch (error) {
      return handleError(error);
    }
  },

  async start(tenantId: string, deploymentId: string): Promise<void> {
    try {
      await api.post(`/tenants/${tenantId}/deployments/${deploymentId}/actions/start`);
    } catch (error) {
      return handleError(error);
    }
  },

  async restart(tenantId: string, deploymentId: string): Promise<void> {
    try {
      await api.post(`/tenants/${tenantId}/deployments/${deploymentId}/actions/restart`);
    } catch (error) {
      return handleError(error);
    }
  },

  async getPrometheusConfig(tenantId: string, deploymentId: string): Promise<PrometheusConfig> {
    try {
      const response = await api.get<PrometheusConfig>(`/tenants/${tenantId}/deployments/${deploymentId}/monitoring/prometheus`);
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async updatePrometheus(tenantId: string, deploymentId: string, enabled: boolean): Promise<PrometheusConfig> {
    try {
      const response = await api.patch<PrometheusConfig>(`/tenants/${tenantId}/deployments/${deploymentId}/monitoring/prometheus`, { enabled });
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async getPrometheusScrapeConfig(tenantId: string, deploymentId: string): Promise<PrometheusScrapeConfig> {
    try {
      const response = await api.get<PrometheusScrapeConfig>(`/tenants/${tenantId}/deployments/${deploymentId}/monitoring/prometheus/config`);
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async revealPrometheusPassword(tenantId: string, deploymentId: string): Promise<PrometheusPasswordReveal> {
    try {
      const response = await api.post<PrometheusPasswordReveal>(`/tenants/${tenantId}/deployments/${deploymentId}/monitoring/prometheus/reveal`);
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async rotatePrometheusPassword(tenantId: string, deploymentId: string): Promise<PrometheusPasswordRotate> {
    try {
      const response = await api.post<PrometheusPasswordRotate>(`/tenants/${tenantId}/deployments/${deploymentId}/monitoring/prometheus/rotate`);
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async updateBackup(tenantId: string, deploymentId: string, enabled: boolean): Promise<void> {
    try {
      await api.patch(`/tenants/${tenantId}/deployments/${deploymentId}/backup`, { enabled });
    } catch (error) {
      return handleError(error);
    }
  },

  async getBackupStatus(tenantId: string, deploymentId: string): Promise<BackupStatus> {
    try {
      const response = await api.get<BackupStatus>(`/tenants/${tenantId}/deployments/${deploymentId}/backup/status`);
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async listBackupPolicies(tenantId: string): Promise<BackupPolicy[]> {
    try {
      const response = await api.get<BackupPolicy[]>(`/tenants/${tenantId}/backup/policies`);
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async setBackupPolicy(tenantId: string, deploymentId: string, policyId: string): Promise<void> {
    try {
      await api.post(`/tenants/${tenantId}/deployments/${deploymentId}/backup/policy`, { policyId });
    } catch (error) {
      return handleError(error);
    }
  },

  async triggerBackupSnapshot(tenantId: string, deploymentId: string): Promise<void> {
    try {
      await api.post(`/tenants/${tenantId}/deployments/${deploymentId}/backup/snapshotNow`);
    } catch (error) {
      return handleError(error);
    }
  },

  async listBackupSnapshots(tenantId: string, deploymentId: string): Promise<BackupSnapshot[]> {
    try {
      const response = await api.get<BackupSnapshot[]>(`/tenants/${tenantId}/deployments/${deploymentId}/backup/snapshots`);
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  async startBackup(tenantId: string, deploymentId: string): Promise<void> {
    try {
      await api.post(`/tenants/${tenantId}/deployments/${deploymentId}/backup/start`);
    } catch (error) {
      return handleError(error);
    }
  },

  async stopBackup(tenantId: string, deploymentId: string): Promise<void> {
    try {
      await api.post(`/tenants/${tenantId}/deployments/${deploymentId}/backup/stop`);
    } catch (error) {
      return handleError(error);
    }
  },

  async restoreBackup(tenantId: string, deploymentId: string, snapshotId: string): Promise<void> {
    try {
      await api.post(`/tenants/${tenantId}/deployments/${deploymentId}/backup/restore`, { snapshotId });
    } catch (error) {
      return handleError(error);
    }
  },
};
