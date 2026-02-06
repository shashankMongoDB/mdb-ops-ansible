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
    ErrorResponse
)
from app.services import tenants_service
from app.services import deployments_service

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
    try:
        result = deployments_service.create_replicaset_deployment(
            tenant_id=tenantId,
            deployment_id=request.deploymentId,
            mongo_version=request.mongoVersion,
            members=request.members,
            display_name=request.displayName,
            environment=request.environment
        )
        return result
    except ValueError as e:
        if "already exists" in str(e):
            raise HTTPException(status_code=409, detail=str(e))
        elif "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error creating deployment")
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
