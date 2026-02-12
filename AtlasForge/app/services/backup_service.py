"""
Backup Service for Enterprise Deployments

Integrates with Ops Manager REST API for backup operations.
Only supports Enterprise plan deployments.
"""

from typing import Dict, Any, List
from datetime import datetime, timezone
from app.services.mongo_repo import get_repo
from app.services.opsmanager_backup_client import get_om_backup_client


def _check_enterprise_plan(tenant: Dict[str, Any]) -> None:
    """Check if tenant is enterprise plan, raise error if not"""
    plan = tenant.get("plan", "enterprise")
    if plan != "enterprise":
        raise ValueError("Backup via Ops Manager is only available for Enterprise deployments.")


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

    # Get OM project ID and cluster name
    om_project_id = deployment.get("omProjectId")
    cluster_name = deployment.get("rsName") or deployment.get("clusterName") or deployment_id
    
    if not om_project_id:
        # If no OM project ID, backup not configured yet
        return {
            "backupEnabled": False,
            "policyName": None,
            "status": "NEVER_RUN",
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

    # Get any deployment to find OM project ID
    deployments = repo.list_tenant_deployments(tenant_id)
    if not deployments or len(deployments) == 0:
        return []

    om_project_id = deployments[0].get("omProjectId")
    if not om_project_id:
        return []

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

    om_project_id = deployment.get("omProjectId")
    cluster_name = deployment.get("rsName") or deployment.get("clusterName") or deployment_id
    
    if not om_project_id:
        raise ValueError("Ops Manager project ID not found for this deployment")

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

    om_project_id = deployment.get("omProjectId")
    cluster_name = deployment.get("rsName") or deployment.get("clusterName") or deployment_id
    
    if not om_project_id:
        raise ValueError("Ops Manager project ID not found for this deployment")

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

    om_project_id = deployment.get("omProjectId")
    cluster_name = deployment.get("rsName") or deployment.get("clusterName") or deployment_id
    
    if not om_project_id:
        return []

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
