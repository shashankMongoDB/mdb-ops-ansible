from typing import Optional, Literal, Any
from pydantic import BaseModel, Field


class TenantCreateRequest(BaseModel):
    tenantId: str = Field(..., description="DNS-safe tenant identifier (a-z0-9-, max 63 chars)")
    displayName: str = Field(..., description="Human-readable tenant name")
    plan: Literal["enterprise", "community"] = Field("enterprise", description="Deployment flavor: enterprise (Ops Manager) or community (standalone operator)")


class TenantCreateResponse(BaseModel):
    tenantId: str
    namespace: str
    projectName: Optional[str] = None
    status: str
    plan: str


class DeploymentCreateRequest(BaseModel):
    deploymentId: str = Field(..., description="DNS-safe deployment identifier")
    type: str = Field("ReplicaSet", description="Deployment type: Standalone, ReplicaSet, or ShardedCluster")
    mongoVersion: str = Field(..., description="MongoDB version (e.g., 8.0.3)")
    displayName: str = Field(..., description="Human-readable deployment name")
    environment: str = Field("prod", description="Environment (prod, staging, dev, etc.)")
    
    # ReplicaSet specific
    members: Optional[int] = Field(None, ge=1, le=50, description="Number of replica set members (ReplicaSet only)")
    
    # ShardedCluster specific
    shardCount: Optional[int] = Field(None, ge=1, description="Number of shards (ShardedCluster only)")
    mongodsPerShardCount: Optional[int] = Field(None, ge=1, description="Mongod members per shard (ShardedCluster only)")
    mongosCount: Optional[int] = Field(None, ge=1, description="Number of mongos routers (ShardedCluster only)")
    configServerCount: Optional[int] = Field(None, ge=3, description="Number of config servers (ShardedCluster only)")


class DeploymentCreateResponse(BaseModel):
    tenantId: str
    deploymentId: str
    type: str
    mongoVersion: str
    state: str
    members: Optional[int] = None
    shardCount: Optional[int] = None
    mongodsPerShardCount: Optional[int] = None
    mongosCount: Optional[int] = None
    configServerCount: Optional[int] = None


class DeploymentDetailResponse(BaseModel):
    tenantId: str
    deploymentId: str
    type: str
    displayName: str
    environment: str
    mongoVersion: str
    createdAt: str
    state: str
    members: Optional[int] = None
    k8sPhase: Optional[str] = None


class DeploymentListItem(BaseModel):
    tenantId: str
    deploymentId: str
    type: str
    displayName: str
    environment: str
    mongoVersion: str
    state: str
    createdAt: str
    members: Optional[int] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


class PrometheusEnableRequest(BaseModel):
    enabled: bool = Field(..., description="Enable or disable Prometheus metrics")


class PrometheusConfigResponse(BaseModel):
    enabled: bool
    namespace: Optional[str] = None
    serviceName: Optional[str] = None
    port: Optional[int] = None
    metricsPath: Optional[str] = None
    externalHost: Optional[str] = None
    externalPort: Optional[int] = None
    serviceType: Optional[str] = None


class ConnectionInfoResponse(BaseModel):
    namespace: str
    deploymentId: str
    replicaSet: Optional[str] = None
    internalUri: Optional[str] = None
    externalHostPort: Optional[str] = None
    externalUri: Optional[str] = None
    externalPrimaryHostPort: Optional[str] = None
    externalPrimaryUri: Optional[str] = None
    externalSecondaryHostPort: Optional[str] = None
    externalSecondaryUri: Optional[str] = None
    error: Optional[str] = None
    status: Optional[str] = None  # "shutdown" or "running"
    message: Optional[str] = None  # Human-readable message
    operation: Optional[str] = None
    progress: Optional[int] = None
    operationMessage: Optional[str] = None
    targetVersion: Optional[str] = None
    targetReplicas: Optional[int] = None
    currentVersion: Optional[str] = None
    currentReplicas: Optional[int] = None
    readyReplicas: Optional[int] = None
    totalReplicas: Optional[int] = None
    replicas: Optional[list[dict[str, Any]]] = None
    crPhase: Optional[str] = None
    crMessage: Optional[str] = None
    crActualVersion: Optional[str] = None


class BackupUpdateRequest(BaseModel):
    enabled: bool = Field(..., description="Enable or disable backup")


class BackupUpdateResponse(BaseModel):
    tenantId: str
    deploymentId: str
    backupEnabled: bool


class MonitoringUpdateRequest(BaseModel):
    prometheusEnabled: bool = Field(..., description="Enable or disable Prometheus monitoring")


class MonitoringUpdateResponse(BaseModel):
    tenantId: str
    deploymentId: str
    prometheusEnabled: bool


class ShutdownResponse(BaseModel):
    tenantId: str
    deploymentId: str
    action: str
    previousReplicas: int
    currentReplicas: int


class StartResponse(BaseModel):
    tenantId: str
    deploymentId: str
    action: str
    replicas: int


class RestartResponse(BaseModel):
    tenantId: str
    deploymentId: str
    action: str
    status: str


class ScaleRequest(BaseModel):
    members: int = Field(..., ge=1, description="Desired number of replica set members")


class ScaleResponse(BaseModel):
    tenantId: str
    deploymentId: str
    clusterType: str
    oldMembers: int
    newMembers: int
    warning: Optional[str] = None


class VersionUpgradeRequest(BaseModel):
    mongoVersion: str = Field(..., description="Target MongoDB version (e.g., 8.0.3)")


class VersionUpgradeResponse(BaseModel):
    tenantId: str
    deploymentId: str
    clusterType: str
    oldVersion: str
    newVersion: str
    message: Optional[str] = None
    warning: Optional[str] = None


class PrometheusScrapeConfigResponse(BaseModel):
    jobName: str = Field(..., description="Prometheus job name for this deployment")
    metricsPath: str = Field(..., description="Metrics endpoint path (e.g., /metrics)")
    username: str = Field(..., description="Basic auth username for Prometheus")
    passwordMasked: str = Field(..., description="Masked password (e.g., ****ABCD)")
    targets: list[str] = Field(..., description="List of scrape targets (node-ip:port)")
    labels: dict = Field(..., description="Labels to apply to scraped metrics")
    workerNodeIps: list[str] = Field(..., description="All available worker node IPs")
    nodePort: int = Field(..., description="NodePort for metrics service")
    canRevealPassword: bool = Field(..., description="True if password can be revealed (firstViewedAt is null)")


class PrometheusPasswordRevealResponse(BaseModel):
    username: str = Field(..., description="Basic auth username")
    password: str = Field(..., description="Full password (shown only once)")


class PrometheusPasswordRotateResponse(BaseModel):
    message: str = Field(..., description="Success message")
    passwordVersion: int = Field(..., description="New password version number")


class BackupStatusResponse(BaseModel):
    backupEnabled: bool = Field(..., description="Whether backup is enabled")
    policyName: Optional[str] = Field(None, description="Backup policy name")
    status: str = Field(..., description="Backup status: NEVER_RUN / ACTIVE / ERROR")
    lastSnapshotTime: Optional[str] = Field(None, description="Last snapshot time (ISO)")
    pitrEnabled: bool = Field(..., description="Point-in-time restore enabled")
    pitrWindowStart: Optional[str] = Field(None, description="PITR window start")
    pitrWindowEnd: Optional[str] = Field(None, description="PITR window end")
    error: Optional[str] = Field(None, description="Error message if status is ERROR")


class BackupPolicyResponse(BaseModel):
    policyId: str = Field(..., description="Policy identifier")
    name: str = Field(..., description="Policy name")
    description: str = Field(..., description="Policy description")
    frequency: str = Field(..., description="Backup frequency")
    retention: str = Field(..., description="Retention period")


class BackupPolicySetRequest(BaseModel):
    policyId: str = Field(..., description="Policy ID to assign")


class BackupPolicySetResponse(BaseModel):
    message: str = Field(..., description="Success message")


class BackupSnapshotTriggerResponse(BaseModel):
    message: str = Field(..., description="Success message")
    snapshotId: Optional[str] = Field(None, description="Snapshot ID")
    status: Optional[str] = Field(None, description="Snapshot status")
    createdAt: Optional[str] = Field(None, description="Created timestamp")


class BackupSnapshotResponse(BaseModel):
    snapshotId: str = Field(..., description="Snapshot identifier")
    type: str = Field(..., description="Snapshot type: scheduled or on-demand")
    status: str = Field(..., description="Snapshot status")
    createdAt: Optional[str] = Field(None, description="Created timestamp (ISO)")
    expiresAt: Optional[str] = Field(None, description="Expiration timestamp (ISO)")


# DB Users
class DBUserRole(BaseModel):
    db: str = Field(..., description="Database name for this role")
    name: str = Field(..., description="Role name (e.g., readWrite, clusterMonitor)")


class CreateDBUserRequest(BaseModel):
    username: str = Field(..., description="Database username")
    db: str = Field(..., description="Default database name")
    roles: list[DBUserRole] = Field(..., description="Array of roles for the user")


class DBUserResponse(BaseModel):
    username: str
    db: str
    roles: list[dict]
    createdAt: str
    updatedAt: Optional[str] = None
    connectionUri: Optional[str] = None


class DBUserConnectionResponse(BaseModel):
    username: str
    db: str
    roles: list[dict]
    externalUri: Optional[str] = None
    internalUri: Optional[str] = None
    externalPrimaryUri: Optional[str] = None
    externalSecondaryUri: Optional[str] = None


# Community Backup
class FilesystemBackupConfig(BaseModel):
    backupHost: str = Field(..., description="NFS/EFS hostname or IP")
    backupPath: str = Field(..., description="Directory path on remote storage")
    subDirectory: Optional[str] = Field(None, description="Optional subdirectory")


class CommunityBackupUpdateRequest(BaseModel):
    enabled: bool = Field(..., description="Enable or disable backup")
    type: Optional[str] = Field(None, description="Backup type: s3 or filesystem")
    s3Bucket: Optional[str] = Field(None, description="S3 bucket name")
    s3Prefix: Optional[str] = Field(None, description="S3 prefix/folder path")
    s3Region: Optional[str] = Field(None, description="S3 region")
    filesystem: Optional[FilesystemBackupConfig] = Field(None, description="Filesystem backup config")
    schedule: Optional[str] = Field(None, description="Cron schedule")
    retentionDays: Optional[int] = Field(None, description="Retention in days")


class CommunityBackupStatusResponse(BaseModel):
    enabled: bool
    type: Optional[str] = None  # "s3" or "filesystem"
    status: str
    schedule: Optional[str] = None
    lastSuccessfulTime: Optional[str] = None
    s3Bucket: Optional[str] = None
    s3Prefix: Optional[str] = None
    s3Region: Optional[str] = None
    s3Path: Optional[str] = None
    target: Optional[str] = None  # For filesystem: "host:/path"
    retentionDays: Optional[int] = None
    snapshots: Optional[list] = None
    message: Optional[str] = None


# Community Backup Restore
class RestoreBackupRequest(BaseModel):
    snapshotFilename: str = Field(..., description="Snapshot filename to restore")
    dropExisting: bool = Field(True, description="Drop existing collections before restore")


class RestoreBackupResponse(BaseModel):
    message: str
    jobName: str
    namespace: str
    snapshot: str
    dropExisting: bool
    status: str
    checkStatusCommand: str


class RestoreJobStatusResponse(BaseModel):
    jobName: str
    namespace: str
    status: str
    succeeded: int
    failed: int
    active: int
    startTime: Optional[str] = None
    completionTime: Optional[str] = None
    logs: str
