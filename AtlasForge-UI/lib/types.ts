export interface Tenant {
  tenantId: string;
  displayName?: string;
  namespace?: string;
  createdAt?: string;
  environment?: string;
  notes?: string;
}

export interface DeploymentStatus {
  phase: 'Running' | 'Provisioning' | 'Scaling' | 'Stopped' | 'Error' | 'Deleted' | 'Unknown';
  ready?: number;
  desired?: number;
  timestamp?: string;
}

export interface Deployment {
  tenantId: string;
  deploymentId: string;
  type: 'Standalone' | 'ReplicaSet' | 'ShardedCluster';
  mongoVersion: string;
  displayName?: string;
  environment?: string;
  members?: number;
  shardCount?: number;
  mongodsPerShardCount?: number;
  mongosCount?: number;
  configServerCount?: number;
  status?: DeploymentStatus;
  createdAt?: string;
}

export interface ConnectionInfo {
  mongoUri: string;
  mongoshExample: string;
  hosts?: string[];
}

export interface PrometheusConfig {
  enabled: boolean;
  externalHost?: string;
  externalPort?: number;
  metricsPath?: string;
}

export interface BackupConfig {
  enabled: boolean;
}

export interface TenantWithStats extends Tenant {
  deploymentCount: number;
  runningCount: number;
  stoppedCount: number;
  errorCount: number;
}

export interface CreateTenantRequest {
  tenantId: string;
  displayName?: string;
  environment?: string;
  notes?: string;
}

export interface CreateDeploymentRequest {
  deploymentId: string;
  type?: 'Standalone' | 'ReplicaSet' | 'ShardedCluster';
  mongoVersion: string;
  members?: number;
  shardCount?: number;
  mongodsPerShardCount?: number;
  mongosCount?: number;
  configServerCount?: number;
  displayName?: string;
  environment?: string;
}

export interface ScaleDeploymentRequest {
  members: number;
}

export interface UpgradeVersionRequest {
  mongoVersion: string;
}

export interface MonitoringRequest {
  prometheusEnabled: boolean;
}

export interface PrometheusRequest {
  enabled: boolean;
}

export interface BackupRequest {
  enabled: boolean;
}

export interface ApiError {
  detail: string;
  status?: number;
}
