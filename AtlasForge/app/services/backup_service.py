"""
Backup Service for Enterprise Deployments

Integrates with Ops Manager REST API for backup operations.
Only supports Enterprise plan deployments.

ProjectId Discovery:
- Lazily discovers Ops Manager projectId by looking up projectName
- Caches projectId in tenant/deployment documents for future use
- Read-only: Never creates or deletes OM projects
- Tolerates "project not found" (operator may not have created it yet)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.services.mongo_repo import get_repo
from app.services.opsmanager_backup_client import get_om_backup_client
from app.services.opsmanager_project_client import get_om_project_client


def _check_enterprise_plan(tenant: Dict[str, Any]) -> None:
    """Check if tenant is enterprise plan, raise error if not"""
    plan = tenant.get("plan", "enterprise")
    if plan != "enterprise":
        raise ValueError("Backup via Ops Manager is only available for Enterprise deployments.")


def _discover_and_cache_project_id(tenant: Dict[str, Any], deployment: Dict[str, Any]) -> Optional[str]:
    """
    Lazily discover Ops Manager projectId by name lookup (read-only).
    
    - Checks if already cached in deployment or tenant
    - If not, looks up project by name in Ops Manager (does NOT create)
    - Caches projectId in tenant and deployment documents
    - Returns projectId or None if project not found yet
    """
    repo = get_repo()
    om_project_client = get_om_project_client()
    
    # Check if already cached in deployment
    if deployment.get("omProjectId"):
        return deployment["omProjectId"]
    
    # Check if already cached in tenant
    tenant_project_id = tenant.get("opsManager", {}).get("projectId")
    if tenant_project_id:
        # Cache in deployment too
        repo.update_deployment(
            tenant["tenantId"],
            deployment["deploymentId"],
            {"omProjectId": tenant_project_id}
        )
        return tenant_project_id
    
    # Not cached anywhere - try to discover from Ops Manager
    project_name = tenant.get("opsManager", {}).get("projectName")
    org_id = tenant.get("opsManager", {}).get("orgId")
    
    if not project_name or not org_id:
        return None  # Can't look up without project name
    
    try:
        # Read-only lookup - do NOT create
        project = om_project_client.get_project_by_name(org_id, project_name)
        
        if not project:
            # Project not found yet - operator may not have created it
            return None
        
        project_id = project.get("id")
        
        # Cache projectId in tenant document
        if "opsManager" not in tenant:
            tenant["opsManager"] = {}
        tenant["opsManager"]["projectId"] = project_id
        repo.update_tenant(tenant["tenantId"], {"opsManager": tenant["opsManager"]})
        
        # Cache projectId in deployment document
        repo.update_deployment(
            tenant["tenantId"],
            deployment["deploymentId"],
            {"omProjectId": project_id}
        )
        
        return project_id
        
    except Exception:
        # Ops Manager not reachable or other error - return None
        return None


def get_backup_status(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Get backup status for a deployment.
    
    Returns:
    - backupEnabled: bool
    - policyName: string or null
    - status: "NEVER_RUN" / "ACTIVE" / "ERROR"
    - lastSnapshotTime: ISO string or null
    - pitrEnabled: bool
    - pitrWindowStart: ISO string or null
    - pitrWindowEnd: ISO string or null
    
    Raises ValueError if not Enterprise plan.
    """
    repo = get_repo()
    om_client = get_om_backup_client()

    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    _check_enterprise_plan(tenant)

    deployment = repo.get_deployment(tenant_id, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment {deployment_id} not found for tenant {tenant_id}")

    # Lazily discover and cache projectId (read-only lookup)
    om_project_id = _discover_and_cache_project_id(tenant, deployment)
    cluster_name = deployment.get("rsName") or deployment.get("clusterName") or deployment_id
    
    if not om_project_id:
        # OM project not found yet - operator may not have created it
        return {
            "backupEnabled": False,
            "policyName": None,
            "status": "NOT_READY",
            "lastSnapshotTime": None,
            "pitrEnabled": False,
            "pitrWindowStart": None,
            "pitrWindowEnd": None
        }

    try:
        backup_config = om_client.get_backup_config(om_project_id, cluster_name)
        
        if not backup_config:
            return {
                "backupEnabled": False,
                "policyName": None,
                "status": "NEVER_RUN",
                "lastSnapshotTime": None,
                "pitrEnabled": False,
                "pitrWindowStart": None,
                "pitrWindowEnd": None
            }

        # Parse OM backup config
        status_name = backup_config.get("statusName", "NEVER_RUN")
        
        # Get last snapshot info
        snapshots = om_client.list_snapshots(om_project_id, cluster_name, limit=1)
        last_snapshot_time = None
        if snapshots and len(snapshots) > 0:
            created = snapshots[0].get("created")
            if created:
                last_snapshot_time = created

        # PITR info
        pitr_enabled = backup_config.get("pointInTimeWindowHours", 0) > 0
        pitr_window_start = None
        pitr_window_end = None
        
        if pitr_enabled:
            # OM may provide window info
            pitr_window_start = backup_config.get("pitrWindowStart")
            pitr_window_end = backup_config.get("pitrWindowEnd")

        return {
            "backupEnabled": True,
            "policyName": backup_config.get("policyName", "Default"),
            "status": status_name,
            "lastSnapshotTime": last_snapshot_time,
            "pitrEnabled": pitr_enabled,
            "pitrWindowStart": pitr_window_start,
            "pitrWindowEnd": pitr_window_end
        }

    except Exception as e:
        # If OM API fails, return error status
        return {
            "backupEnabled": False,
            "policyName": None,
            "status": "ERROR",
            "lastSnapshotTime": None,
            "pitrEnabled": False,
            "pitrWindowStart": None,
            "pitrWindowEnd": None,
            "error": str(e)
        }


def list_backup_policies(tenant_id: str) -> List[Dict[str, Any]]:
    """
    List available backup policies for a tenant.
    
    Returns list of:
    - policyId: string
    - name: string
    - description: string
    - frequency: string (e.g., "hourly", "daily")
    - retention: string (e.g., "7 days", "30 days")
    
    Raises ValueError if not Enterprise plan.
    """
    repo = get_repo()
    om_client = get_om_backup_client()

    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    _check_enterprise_plan(tenant)

    # Get any deployment to discover OM project ID
    deployments = repo.list_tenant_deployments(tenant_id)
    if not deployments or len(deployments) == 0:
        return []

    # Lazily discover projectId from first deployment
    om_project_id = _discover_and_cache_project_id(tenant, deployments[0])
    if not om_project_id:
        return []  # OM project not found yet

    try:
        configs = om_client.list_backup_policies(om_project_id)
        
        policies = []
        for config in configs:
            # Extract policy info from OM backup config
            policy_id = config.get("clusterId", config.get("groupId"))
            policy_name = config.get("policyName", "Default")
            status = config.get("statusName", "UNKNOWN")
            
            policies.append({
                "policyId": policy_id,
                "name": policy_name,
                "description": f"Status: {status}",
                "frequency": "Scheduled",  # OM manages this
                "retention": "As configured in Ops Manager"
            })
        
        return policies

    except Exception as e:
        raise ValueError(f"Failed to list backup policies: {str(e)}")


def set_backup_policy(tenant_id: str, deployment_id: str, policy_id: str) -> Dict[str, Any]:
    """
    Assign a backup policy to a deployment.
    
    Returns success message.
    
    Raises ValueError if not Enterprise plan.
    """
    repo = get_repo()
    om_client = get_om_backup_client()

    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    _check_enterprise_plan(tenant)

    deployment = repo.get_deployment(tenant_id, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment {deployment_id} not found for tenant {tenant_id}")

    # Lazily discover projectId
    om_project_id = _discover_and_cache_project_id(tenant, deployment)
    cluster_name = deployment.get("rsName") or deployment.get("clusterName") or deployment_id
    
    if not om_project_id:
        raise ValueError("Ops Manager project not found yet. Deployment may still be initializing.")

    try:
        # Update backup config with new policy
        config = {
            "policyId": policy_id
        }
        om_client.update_backup_config(om_project_id, cluster_name, config)
        
        return {
            "message": f"Backup policy updated successfully for deployment {deployment_id}"
        }

    except Exception as e:
        raise ValueError(f"Failed to set backup policy: {str(e)}")


def trigger_backup_snapshot(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Trigger an on-demand snapshot.
    
    Returns snapshot info.
    
    Raises ValueError if not Enterprise plan.
    """
    repo = get_repo()
    om_client = get_om_backup_client()

    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    _check_enterprise_plan(tenant)

    deployment = repo.get_deployment(tenant_id, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment {deployment_id} not found for tenant {tenant_id}")

    # Lazily discover projectId
    om_project_id = _discover_and_cache_project_id(tenant, deployment)
    cluster_name = deployment.get("rsName") or deployment.get("clusterName") or deployment_id
    
    if not om_project_id:
        raise ValueError("Ops Manager project not found yet. Deployment may still be initializing.")

    try:
        snapshot = om_client.trigger_snapshot(
            om_project_id, 
            cluster_name,
            description=f"On-demand snapshot for {deployment_id} at {datetime.now(timezone.utc).isoformat()}"
        )
        
        return {
            "message": "Snapshot triggered successfully",
            "snapshotId": snapshot.get("id"),
            "status": snapshot.get("status", "IN_PROGRESS"),
            "createdAt": snapshot.get("created")
        }

    except Exception as e:
        raise ValueError(f"Failed to trigger snapshot: {str(e)}")


def list_backup_snapshots(tenant_id: str, deployment_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    List backup snapshots for a deployment.
    
    Returns list of:
    - snapshotId: string
    - type: "scheduled" or "on-demand"
    - status: "IN_PROGRESS" / "COMPLETED" / "FAILED"
    - createdAt: ISO string
    - expiresAt: ISO string or null
    
    Raises ValueError if not Enterprise plan.
    """
    repo = get_repo()
    om_client = get_om_backup_client()

    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    _check_enterprise_plan(tenant)

    deployment = repo.get_deployment(tenant_id, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment {deployment_id} not found for tenant {tenant_id}")

    # Lazily discover projectId
    om_project_id = _discover_and_cache_project_id(tenant, deployment)
    cluster_name = deployment.get("rsName") or deployment.get("clusterName") or deployment_id
    
    if not om_project_id:
        return []  # OM project not found yet

    try:
        om_snapshots = om_client.list_snapshots(om_project_id, cluster_name, limit=limit)
        
        snapshots = []
        for snap in om_snapshots:
            snapshot_type = "on-demand" if snap.get("description", "").lower().startswith("on-demand") else "scheduled"
            
            snapshots.append({
                "snapshotId": snap.get("id"),
                "type": snapshot_type,
                "status": snap.get("status", "UNKNOWN"),
                "createdAt": snap.get("created"),
                "expiresAt": snap.get("expires")
            })
        
        return snapshots

    except Exception as e:
        raise ValueError(f"Failed to list snapshots: {str(e)}")
