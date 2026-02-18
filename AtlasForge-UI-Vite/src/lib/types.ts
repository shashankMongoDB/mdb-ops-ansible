export interface Tenant {
  tenantId: string;
  displayName?: string;
  plan?: 'enterprise' | 'community';
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
  namespace: string;
  deploymentId: string;
  replicaSet: string;
  internalUri: string;
  externalHostPort?: string | null;
  externalUri?: string | null;
  externalPrimaryHostPort?: string | null;
  externalPrimaryUri?: string | null;
  externalSecondaryHostPort?: string | null;
  externalSecondaryUri?: string | null;
  error?: string | null;
}

export interface PrometheusConfig {
  enabled: boolean;
  externalHost?: string;
  externalPort?: number;
  metricsPath?: string;
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
  plan?: 'enterprise' | 'community';
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

export interface ApiError {
  detail: string;
  status?: number;
}

export interface PrometheusScrapeConfig {
  jobName: string;
  metricsPath: string;
  username: string;
  passwordMasked: string;
  targets: string[];
  labels: Record<string, string>;
  workerNodeIps: string[];
  nodePort: number;
  canRevealPassword: boolean;
}

export interface PrometheusPasswordReveal {
  username: string;
  password: string;
}

export interface PrometheusPasswordRotate {
  message: string;
  passwordVersion: number;
}

export interface BackupStatus {
  backupEnabled: boolean;
  policyName: string | null;
  status: string;
  lastSnapshotTime: string | null;
  pitrEnabled: boolean;
  pitrWindowStart: string | null;
  pitrWindowEnd: string | null;
  error?: string;
}

export interface BackupPolicy {
  policyId: string;
  name: string;
  description: string;
  frequency: string;
  retention: string;
}

export interface BackupSnapshot {
  snapshotId: string;
  type: string;
  status: string;
  createdAt: string | null;
  expiresAt: string | null;
}
