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
from typing import List
from fastapi import FastAPI, HTTPException, Path
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
    ConnectionInfoResponse,
    BackupUpdateRequest,
    BackupUpdateResponse,
    MonitoringUpdateRequest,
    MonitoringUpdateResponse,
    ShutdownResponse,
    StartResponse,
    RestartResponse,
    ScaleRequest,
    ScaleResponse,
    VersionUpgradeRequest,
    VersionUpgradeResponse
)
from app.services import tenants_service
from app.services import deployments_service
from app.services import monitoring_service
from app.services import lifecycle_service
from app.services import scaling_service

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


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/tenants", response_model=TenantCreateResponse, status_code=201)
def create_tenant(request: TenantCreateRequest):
    try:
        result = tenants_service.onboard_tenant(
            tenant_id=request.tenantId,
            display_name=request.displayName
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
