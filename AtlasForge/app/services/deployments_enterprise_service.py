"""
Enterprise MongoDB deployments service.
Handles MongoDB CRs (mongodb.com/v1) with Ops Manager integration.

This module is a thin wrapper that delegates to the existing deployments_service.py
for backward compatibility. All enterprise-specific logic remains in deployments_service.py.
"""
import logging
from typing import Dict, Any, Optional
from app.services import deployments_service

logger = logging.getLogger(__name__)


def create_deployment_enterprise(
    tenant_id: str,
    deployment_id: str,
    namespace: str,
    deployment_type: str,
    mongo_version: str,
    display_name: str,
    environment: str,
    members: Optional[int] = None,
    shard_count: Optional[int] = None,
    mongods_per_shard_count: Optional[int] = None,
    mongos_count: Optional[int] = None,
    config_server_count: Optional[int] = None,
    created_by: str = "system"
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Create an enterprise MongoDB deployment using Ops Manager.
    
    This delegates to the existing create_deployment function in deployments_service.py
    which already handles enterprise deployments with Ops Manager.
    
    Returns: (deployment_doc, response)
    """
    logger.info(f"Creating enterprise deployment: {tenant_id}/{deployment_id}, type={deployment_type}")
    
    # The existing create_deployment function handles all the enterprise logic
    # It creates MongoDB CRs (mongodb.com/v1) with Ops Manager configuration
    response = deployments_service.create_deployment(
        tenant_id=tenant_id,
        deployment_id=deployment_id,
        deployment_type=deployment_type,
        mongo_version=mongo_version,
        display_name=display_name,
        environment=environment,
        members=members,
        shard_count=shard_count,
        mongods_per_shard_count=mongods_per_shard_count,
        mongos_count=mongos_count,
        config_server_count=config_server_count,
        created_by=created_by
    )
    
    # The create_deployment function already inserts into DB and returns the response
    # For consistency with community service, we need to return both doc and response
    # But since the existing function already inserted, we'll construct a minimal doc
    # This is just for API consistency - the real doc is already in DB
    deployment_doc = {
        "_id": f"{tenant_id}:{deployment_id}",
        "tenantId": tenant_id,
        "deploymentId": deployment_id,
        "plan": "enterprise"
    }
    
    return deployment_doc, response


# Note: Other enterprise operations (scale, upgrade, delete, etc.) are already
# implemented in deployments_service.py and work with enterprise MongoDB CRs.
# They don't need wrappers here since the routing logic in deployments_service.py
# will handle dispatching based on tenant plan.
