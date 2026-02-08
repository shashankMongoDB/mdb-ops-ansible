from typing import Optional
from pydantic import BaseModel, Field


class TenantCreateRequest(BaseModel):
    tenantId: str = Field(..., description="DNS-safe tenant identifier (a-z0-9-, max 63 chars)")
    displayName: str = Field(..., description="Human-readable tenant name")


class TenantCreateResponse(BaseModel):
    tenantId: str
    namespace: str
    projectName: str
    status: str


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
    displayName: str
    environment: str
    mongoVersion: str
    members: int
    createdAt: str
    state: str
    k8sPhase: Optional[str] = None


class DeploymentListItem(BaseModel):
    tenantId: str
    deploymentId: str
    displayName: str
    environment: str
    mongoVersion: str
    members: int
    state: str
    createdAt: str


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
    tenantId: str
    deploymentId: str
    mongoUri: str
    mongoshExample: str


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
