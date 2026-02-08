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
    mongoVersion: str = Field(..., description="MongoDB version (e.g., 8.0.3)")
    members: int = Field(3, ge=1, le=50, description="Number of replica set members")
    displayName: str = Field(..., description="Human-readable deployment name")
    environment: str = Field("prod", description="Environment (prod, staging, dev, etc.)")


class DeploymentCreateResponse(BaseModel):
    tenantId: str
    deploymentId: str
    mongoVersion: str
    members: int
    state: str


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
