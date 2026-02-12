"""
MongoDB Control Plane - FastAPI Microservice

This service provides a control plane for managing MongoDB deployments on Kubernetes
using the MongoDB Enterprise Operator (MCK) and Ops Manager.

REQUIRED ENVIRONMENT VARIABLES:
  MCP_MONGODB_URI              - MongoDB connection string for control-plane metadata
  MCP_DB_NAME                  - Database name for metadata (default: mdb_control_plane)
  MCP_KUBECONFIG_PATH          - Path to kubeconfig file (default: /home/ubuntu/.kube/config)
  MCP_NAMESPACE_PREFIX         - Kubernetes namespace prefix (default: mdb-)
  MCP_OPS_MANAGER_URL          - Ops Manager base URL
  MCP_OPS_MANAGER_ORG          - Ops Manager organization ID
  MCP_OM_GLOBAL_PUBLIC_KEY     - Ops Manager API public key
  MCP_OM_GLOBAL_PRIVATE_KEY    - Ops Manager API private key
  MCP_LOG_LEVEL                - Logging level (default: INFO)
  MCP_SERVICE_PORT             - Service port (default: 8001)

HOW TO RUN:
  uvicorn app.main:app --host 0.0.0.0 --port 8001

MAIN ENDPOINTS:
  POST /tenants                              - Onboard a new tenant
  POST /tenants/{tenantId}/deployments       - Create a MongoDB ReplicaSet deployment
  GET  /tenants/{tenantId}/deployments       - List all deployments for a tenant
  GET  /tenants/{tenantId}/deployments/{id}  - Get deployment details
"""

import logging
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app import config
from app.models.dto import (
    TenantCreateRequest,
    TenantCreateResponse,
    DeploymentCreateRequest,
    DeploymentCreateResponse,
    DeploymentDetailResponse,
    DeploymentListItem,
    ErrorResponse,
    PrometheusEnableRequest,
    PrometheusConfigResponse,
    PrometheusScrapeConfigResponse,
    PrometheusPasswordRevealResponse,
    PrometheusPasswordRotateResponse,
    ConnectionInfoResponse,
    BackupUpdateRequest,
    BackupUpdateResponse,
    BackupStatusResponse,
    BackupPolicyResponse,
    BackupPolicySetRequest,
    BackupPolicySetResponse,
    BackupSnapshotTriggerResponse,
    BackupSnapshotResponse,
    MonitoringUpdateRequest,
    MonitoringUpdateResponse,
    ShutdownResponse,
    StartResponse,
    RestartResponse,
    ScaleRequest,
    ScaleResponse,
    VersionUpgradeRequest,
    VersionUpgradeResponse,
    CreateDBUserRequest,
    DBUserResponse,
    DBUserConnectionResponse
)
from app.services import tenants_service
from app.services import deployments_service
from app.services import monitoring_service
from app.services import lifecycle_service
from app.services import scaling_service
from app.services import backup_service
from app.services import db_users_service

logging.basicConfig(
    level=getattr(logging, config.MCP_LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MongoDB Control Plane",
    description="Control plane for MongoDB deployments on Kubernetes",
    version="1.0.0"
)

# Add CORS middleware to allow UI to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your UI domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/tenants", response_model=List[dict])
def list_tenants():
    """List all tenants"""
    try:
        tenants = tenants_service.list_tenants()
        return tenants
    except Exception as e:
        logger.exception("Error listing tenants")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/tenants/{tenantId}", response_model=dict)
def get_tenant(tenantId: str = Path(..., description="Tenant identifier")):
    """Get a specific tenant by ID"""
    try:
        tenant = tenants_service.get_tenant(tenant_id=tenantId)
        if not tenant:
            raise HTTPException(status_code=404, detail=f"Tenant {tenantId} not found")
        return tenant
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting tenant")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/tenants", response_model=TenantCreateResponse, status_code=201)
def create_tenant(request: TenantCreateRequest):
    try:
        result = tenants_service.onboard_tenant(
            tenant_id=request.tenantId,
            display_name=request.displayName,
            plan=request.plan
        )
        return result
    except ValueError as e:
        if "already exists" in str(e):
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error creating tenant")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post(
    "/tenants/{tenantId}/deployments",
    response_model=DeploymentCreateResponse,
    status_code=201
)
def create_deployment(
    tenantId: str = Path(..., description="Tenant identifier"),
    request: DeploymentCreateRequest = None
):
    logger.info(f"POST /tenants/{tenantId}/deployments - deploymentId: {request.deploymentId}, type: {request.type}")
    try:
        result = deployments_service.create_deployment(
            tenant_id=tenantId,
            deployment_id=request.deploymentId,
            deployment_type=request.type,
            mongo_version=request.mongoVersion,
            display_name=request.displayName,
            environment=request.environment,
            members=request.members,
            shard_count=request.shardCount,
            mongods_per_shard_count=request.mongodsPerShardCount,
            mongos_count=request.mongosCount,
            config_server_count=request.configServerCount
        )
        logger.info(f"Successfully created deployment: {tenantId}/{request.deploymentId}")
        return result
    except ValueError as e:
        if "already exists" in str(e):
            logger.warning(f"Deployment already exists: {tenantId}/{request.deploymentId}")
            raise HTTPException(status_code=409, detail=str(e))
        elif "not found" in str(e):
            logger.warning(f"Tenant not found: {tenantId}")
            raise HTTPException(status_code=404, detail=str(e))
        logger.error(f"Validation error creating deployment {tenantId}/{request.deploymentId}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error creating deployment {tenantId}/{request.deploymentId}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get(
    "/tenants/{tenantId}/deployments",
    response_model=List[DeploymentListItem]
)
def list_deployments(tenantId: str = Path(..., description="Tenant identifier")):
    try:
        deployments = deployments_service.list_tenant_deployments(tenant_id=tenantId)
        return deployments
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error listing deployments")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get(
    "/tenants/{tenantId}/deployments/{deploymentId}",
    response_model=DeploymentDetailResponse
)
def get_deployment(
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier")
):
    try:
        deployment = deployments_service.get_deployment_details(
            tenant_id=tenantId,
            deployment_id=deploymentId
        )
        return deployment
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error getting deployment")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.delete(
    "/tenants/{tenantId}/deployments/{deploymentId}",
    status_code=204
)
def delete_deployment(
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier")
):
    try:
        deleted = deployments_service.delete_deployment(
            tenant_id=tenantId,
            deployment_id=deploymentId
        )
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Deployment {deploymentId} not found for tenant {tenantId}")
        return None
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error deleting deployment")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.delete("/tenants/{tenantId}", status_code=204)
def delete_tenant(tenantId: str = Path(..., description="Tenant identifier")):
    try:
        deleted = tenants_service.delete_tenant(tenant_id=tenantId)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Tenant {tenantId} not found")
        return None
    except Exception as e:
        logger.exception("Error deleting tenant")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.patch(
    "/tenants/{tenantId}/deployments/{deploymentId}/monitoring/prometheus",
    response_model=PrometheusConfigResponse
)
def update_prometheus_monitoring(
    request: PrometheusEnableRequest,
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier")
):
    try:
        if request.enabled:
            result = monitoring_service.enable_prometheus_metrics(
                tenant_id=tenantId,
                deployment_id=deploymentId
            )
        else:
            result = monitoring_service.disable_prometheus_metrics(
                tenant_id=tenantId,
                deployment_id=deploymentId
            )
        return result
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error updating Prometheus monitoring")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get(
    "/tenants/{tenantId}/deployments/{deploymentId}/monitoring/prometheus",
    response_model=PrometheusConfigResponse
)
def get_prometheus_monitoring(
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier")
):
    try:
        result = monitoring_service.get_prometheus_config(
            tenant_id=tenantId,
            deployment_id=deploymentId
        )
        return result
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error getting Prometheus monitoring config")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get(
    "/tenants/{tenantId}/deployments/{deploymentId}/monitoring/prometheus/config",
    response_model=PrometheusScrapeConfigResponse
)
def get_prometheus_scrape_config(
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier")
):
    """
    Get Prometheus scrape configuration with MASKED password.
    
    Returns YAML-ready configuration including:
    - Job name and metrics path
    - Basic auth credentials (MASKED password)
    - Target endpoints (worker-ip:nodePort)
    - List of all worker node IPs
    - Labels for scraped metrics
    - canRevealPassword flag (true if password not yet revealed)
    
    Automatically enables Prometheus metrics if not already enabled.
    Works for both Enterprise (MongoDB) and Community (MongoDBCommunity) deployments.
    """
    try:
        result = monitoring_service.get_prometheus_scrape_config(
            tenant_id=tenantId,
            deployment_id=deploymentId
        )
        return result
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error getting Prometheus scrape config")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post(
    "/tenants/{tenantId}/deployments/{deploymentId}/monitoring/prometheus/reveal",
    response_model=PrometheusPasswordRevealResponse
)
def reveal_prometheus_password(
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier")
):
    """
    Reveal the full Prometheus password ONCE.
    
    Only works if the password has not been revealed yet (firstViewedAt is null).
    After revealing, the password cannot be revealed again until rotated.
    
    Returns the full username and password.
    Works for both Enterprise and Community deployments.
    """
    try:
        result = monitoring_service.reveal_prometheus_password(
            tenant_id=tenantId,
            deployment_id=deploymentId
        )
        return result
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        if "already revealed" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error revealing Prometheus password")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post(
    "/tenants/{tenantId}/deployments/{deploymentId}/monitoring/prometheus/rotate",
    response_model=PrometheusPasswordRotateResponse
)
def rotate_prometheus_password(
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier")
):
    """
    Rotate the Prometheus password.
    
    Generates a new strong random password and updates the mongodb-admin-secret in Kubernetes.
    Resets firstViewedAt to null, allowing the password to be revealed once again.
    Increments the password version number.
    
    Returns success message and new password version.
    Works for both Enterprise and Community deployments.
    """
    try:
        result = monitoring_service.rotate_prometheus_password(
            tenant_id=tenantId,
            deployment_id=deploymentId
        )
        return result
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error rotating Prometheus password")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get(
    "/tenants/{tenantId}/deployments/{deploymentId}/connection",
    response_model=ConnectionInfoResponse
)
def get_connection_info(
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier")
):
    try:
        result = lifecycle_service.get_connection_info(
            tenant_id=tenantId,
            deployment_id=deploymentId
        )
        return result
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error getting connection info")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.patch(
    "/tenants/{tenantId}/deployments/{deploymentId}/backup",
    response_model=BackupUpdateResponse
)
def update_backup(
    request: BackupUpdateRequest,
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier")
):
    try:
        result = lifecycle_service.update_backup_setting(
            tenant_id=tenantId,
            deployment_id=deploymentId,
            enabled=request.enabled
        )
        return result
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error updating backup setting")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get(
    "/tenants/{tenantId}/deployments/{deploymentId}/backup/status",
    response_model=BackupStatusResponse
)
def get_backup_status(
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier")
):
    """
    Get backup status for an Enterprise deployment.
    
    Returns backup configuration including policy, status, last snapshot time, and PITR info.
    Only available for Enterprise plan deployments.
    """
    try:
        result = backup_service.get_backup_status(
            tenant_id=tenantId,
            deployment_id=deploymentId
        )
        return result
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        if "only available for Enterprise" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error getting backup status")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get(
    "/tenants/{tenantId}/backup/policies",
    response_model=list[BackupPolicyResponse]
)
def list_backup_policies(
    tenantId: str = Path(..., description="Tenant identifier")
):
    """
    List available backup policies for an Enterprise tenant.
    
    Returns list of policies from Ops Manager.
    Only available for Enterprise plan tenants.
    """
    try:
        result = backup_service.list_backup_policies(tenant_id=tenantId)
        return result
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        if "only available for Enterprise" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error listing backup policies")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post(
    "/tenants/{tenantId}/deployments/{deploymentId}/backup/policy",
    response_model=BackupPolicySetResponse
)
def set_backup_policy(
    request: BackupPolicySetRequest,
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier")
):
    """
    Set backup policy for an Enterprise deployment.
    
    Assigns the specified policy to this deployment's backup configuration.
    Only available for Enterprise plan deployments.
    """
    try:
        result = backup_service.set_backup_policy(
            tenant_id=tenantId,
            deployment_id=deploymentId,
            policy_id=request.policyId
        )
        return result
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        if "only available for Enterprise" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error setting backup policy")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post(
    "/tenants/{tenantId}/deployments/{deploymentId}/backup/snapshotNow",
    response_model=BackupSnapshotTriggerResponse
)
def trigger_backup_snapshot(
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier")
):
    """
    Trigger an on-demand backup snapshot for an Enterprise deployment.
    
    Creates an immediate snapshot via Ops Manager.
    Only available for Enterprise plan deployments.
    """
    try:
        result = backup_service.trigger_backup_snapshot(
            tenant_id=tenantId,
            deployment_id=deploymentId
        )
        return result
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        if "only available for Enterprise" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error triggering backup snapshot")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get(
    "/tenants/{tenantId}/deployments/{deploymentId}/backup/snapshots",
    response_model=list[BackupSnapshotResponse]
)
def list_backup_snapshots(
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier"),
    limit: int = 20
):
    """
    List backup snapshots for an Enterprise deployment.
    
    Returns list of snapshots with status and timestamps.
    Only available for Enterprise plan deployments.
    """
    try:
        result = backup_service.list_backup_snapshots(
            tenant_id=tenantId,
            deployment_id=deploymentId,
            limit=limit
        )
        return result
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        if "only available for Enterprise" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error listing backup snapshots")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post(
    "/tenants/{tenantId}/deployments/{deploymentId}/backup/policy"
)
def set_backup_policy_unsupported(
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier")
):
    """
    Change backup policy (NOT SUPPORTED via API).
    
    Use Ops Manager UI to change backup policies.
    """
    raise HTTPException(
        status_code=501,
        detail="Changing backup policy via API is not supported; use Ops Manager UI."
    )


@app.post(
    "/tenants/{tenantId}/deployments/{deploymentId}/backup/snapshotNow"
)
def trigger_snapshot_unsupported(
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier")
):
    """
    Trigger on-demand snapshot (NOT SUPPORTED via API).
    
    Use Ops Manager UI to trigger on-demand snapshots.
    """
    raise HTTPException(
        status_code=501,
        detail="On-demand snapshot via API is not supported; use Ops Manager UI."
    )


@app.post(
    "/tenants/{tenantId}/deployments/{deploymentId}/backup/restore"
)
def restore_backup(
    request: Dict[str, Any],
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier")
):
    """
    Restore a deployment from a snapshot.
    
    Creates a restore job in Ops Manager for automated (in-place) restore.
    Only available for Enterprise plan deployments.
    
    Body: { "snapshotId": "snapshot-id-here" }
    """
    try:
        snapshot_id = request.get("snapshotId")
        if not snapshot_id:
            raise HTTPException(status_code=400, detail="snapshotId is required")
        
        result = backup_service.restore_snapshot(tenantId, deploymentId, snapshot_id)
        return result
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        if "only available for Enterprise" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error restoring backup")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.patch(
    "/tenants/{tenantId}/deployments/{deploymentId}/monitoring",
    response_model=MonitoringUpdateResponse
)
def update_monitoring(
    request: MonitoringUpdateRequest,
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier")
):
    try:
        result = lifecycle_service.update_monitoring_setting(
            tenant_id=tenantId,
            deployment_id=deploymentId,
            prometheus_enabled=request.prometheusEnabled
        )
        return result
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error updating monitoring setting")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post(
    "/tenants/{tenantId}/deployments/{deploymentId}/actions/shutdown",
    response_model=ShutdownResponse,
    status_code=202
)
def shutdown_deployment(
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier")
):
    try:
        result = lifecycle_service.shutdown_deployment(
            tenant_id=tenantId,
            deployment_id=deploymentId
        )
        return result
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error shutting down deployment")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post(
    "/tenants/{tenantId}/deployments/{deploymentId}/actions/start",
    response_model=StartResponse,
    status_code=202
)
def start_deployment(
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier")
):
    try:
        result = lifecycle_service.start_deployment(
            tenant_id=tenantId,
            deployment_id=deploymentId
        )
        return result
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error starting deployment")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post(
    "/tenants/{tenantId}/deployments/{deploymentId}/actions/restart",
    response_model=RestartResponse,
    status_code=202
)
def restart_deployment(
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier")
):
    try:
        result = lifecycle_service.restart_deployment(
            tenant_id=tenantId,
            deployment_id=deploymentId
        )
        return result
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error restarting deployment")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.patch(
    "/tenants/{tenantId}/deployments/{deploymentId}/scale",
    response_model=ScaleResponse
)
def scale_deployment(
    request: ScaleRequest,
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier")
):
    try:
        result = scaling_service.scale_deployment(
            tenant_id=tenantId,
            deployment_id=deploymentId,
            members=request.members
        )
        return result
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error scaling deployment")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.patch(
    "/tenants/{tenantId}/deployments/{deploymentId}/version",
    response_model=VersionUpgradeResponse
)
def upgrade_deployment_version(
    request: VersionUpgradeRequest,
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier")
):
    try:
        result = scaling_service.upgrade_version(
            tenant_id=tenantId,
            deployment_id=deploymentId,
            mongo_version=request.mongoVersion
        )
        return result
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error upgrading deployment version")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# ============================================================
# DB Users
# ============================================================

@app.post(
    "/tenants/{tenantId}/deployments/{deploymentId}/users",
    response_model=DBUserResponse
)
def create_db_user(
    request: CreateDBUserRequest,
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier")
):
    """
    Create a database user for a MongoDB deployment.
    
    Creates MongoDBUser CR and Secret with specified roles, returns connection URI.
    
    Example request body:
    {
      "username": "appUser",
      "db": "appdb",
      "roles": [
        {"db": "appdb", "name": "readWrite"},
        {"db": "admin", "name": "clusterMonitor"}
      ]
    }
    """
    try:
        # Convert Pydantic models to dict for the service
        roles_dict = [{"db": r.db, "name": r.name} for r in request.roles]
        
        result = db_users_service.create_db_user(
            tenant_id=tenantId,
            deployment_id=deploymentId,
            username=request.username,
            db=request.db,
            roles=roles_dict
        )
        return result
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        if "already exists" in str(e):
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error creating DB user")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get(
    "/tenants/{tenantId}/deployments/{deploymentId}/users"
)
def list_db_users(
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier")
):
    """
    List all database users for a deployment.
    
    Returns metadata only (no passwords).
    """
    try:
        users = db_users_service.list_db_users(tenantId, deploymentId)
        return users
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error listing DB users")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get(
    "/tenants/{tenantId}/deployments/{deploymentId}/users/{username}/connection",
    response_model=DBUserConnectionResponse
)
def get_user_connection(
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier"),
    username: str = Path(..., description="Username")
):
    """
    Get connection URIs for a specific database user.
    
    Returns external and internal URIs with credentials.
    """
    try:
        result = db_users_service.get_user_connection(tenantId, deploymentId, username)
        return result
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error getting user connection")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.MCP_SERVICE_PORT)
