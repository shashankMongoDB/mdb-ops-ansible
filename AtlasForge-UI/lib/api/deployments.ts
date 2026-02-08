import { apiClient } from '../api-client';
import {
  Deployment,
  CreateDeploymentRequest,
  ConnectionInfo,
  ScaleDeploymentRequest,
  UpgradeVersionRequest,
  PrometheusConfig,
  PrometheusRequest,
  BackupRequest,
  MonitoringRequest,
} from '../types';

export const deploymentsApi = {
  async getAllForTenant(tenantId: string): Promise<Deployment[]> {
    return apiClient.get<Deployment[]>(`/tenants/${tenantId}/deployments`);
  },

  async getById(tenantId: string, deploymentId: string): Promise<Deployment> {
    return apiClient.get<Deployment>(`/tenants/${tenantId}/deployments/${deploymentId}`);
  },

  async create(tenantId: string, data: CreateDeploymentRequest): Promise<Deployment> {
    return apiClient.post<Deployment>(`/tenants/${tenantId}/deployments`, data);
  },

  async delete(tenantId: string, deploymentId: string): Promise<void> {
    return apiClient.delete<void>(`/tenants/${tenantId}/deployments/${deploymentId}`);
  },

  async getConnectionInfo(tenantId: string, deploymentId: string): Promise<ConnectionInfo> {
    return apiClient.get<ConnectionInfo>(`/tenants/${tenantId}/deployments/${deploymentId}/connection`);
  },

  async scale(tenantId: string, deploymentId: string, data: ScaleDeploymentRequest): Promise<Deployment> {
    return apiClient.patch<Deployment>(`/tenants/${tenantId}/deployments/${deploymentId}/scale`, data);
  },

  async upgradeVersion(tenantId: string, deploymentId: string, data: UpgradeVersionRequest): Promise<Deployment> {
    return apiClient.patch<Deployment>(`/tenants/${tenantId}/deployments/${deploymentId}/version`, data);
  },

  async shutdown(tenantId: string, deploymentId: string): Promise<void> {
    return apiClient.post<void>(`/tenants/${tenantId}/deployments/${deploymentId}/actions/shutdown`);
  },

  async start(tenantId: string, deploymentId: string): Promise<void> {
    return apiClient.post<void>(`/tenants/${tenantId}/deployments/${deploymentId}/actions/start`);
  },

  async restart(tenantId: string, deploymentId: string): Promise<void> {
    return apiClient.post<void>(`/tenants/${tenantId}/deployments/${deploymentId}/actions/restart`);
  },

  async getPrometheusConfig(tenantId: string, deploymentId: string): Promise<PrometheusConfig> {
    return apiClient.get<PrometheusConfig>(`/tenants/${tenantId}/deployments/${deploymentId}/monitoring/prometheus`);
  },

  async updatePrometheus(tenantId: string, deploymentId: string, data: PrometheusRequest): Promise<PrometheusConfig> {
    return apiClient.patch<PrometheusConfig>(`/tenants/${tenantId}/deployments/${deploymentId}/monitoring/prometheus`, data);
  },

  async updateMonitoring(tenantId: string, deploymentId: string, data: MonitoringRequest): Promise<void> {
    return apiClient.patch<void>(`/tenants/${tenantId}/deployments/${deploymentId}/monitoring`, data);
  },

  async updateBackup(tenantId: string, deploymentId: string, data: BackupRequest): Promise<void> {
    return apiClient.patch<void>(`/tenants/${tenantId}/deployments/${deploymentId}/backup`, data);
  },
};
