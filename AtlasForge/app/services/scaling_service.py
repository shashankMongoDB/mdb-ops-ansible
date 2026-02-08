from typing import Dict, Any, Optional, Tuple
from packaging import version
from app.services.mongo_repo import get_repo
from app.services.k8s_client import get_k8s_client


def scale_deployment(tenant_id: str, deployment_id: str, members: int) -> Dict[str, Any]:
    """
    Scale a MongoDB deployment by changing the number of members.
    Enforces best practices: minimum 3 members, warns on even numbers.
    """
    repo = get_repo()
    k8s = get_k8s_client()

    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    deployment = repo.get_deployment(tenant_id, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment {deployment_id} not found for tenant {tenant_id}")

    namespace = tenant["namespace"]

    cr = k8s.get_mongodb_cr(namespace, deployment_id)
    if not cr:
        raise ValueError(f"MongoDB CR {deployment_id} not found in namespace {namespace}")

    cluster_type = cr.get("spec", {}).get("type", "ReplicaSet")
    
    if cluster_type == "ShardedCluster":
        raise ValueError("Scaling for ShardedCluster is not yet implemented")

    current_members = cr.get("spec", {}).get("members", 3)

    if members < 3:
        raise ValueError("Replica set must have at least 3 members")

    warning = None
    if members % 2 == 0:
        warning = "Using an even number of members is not recommended. Consider 3, 5, 7, ... to avoid election ties"

    patch = {
        "spec": {
            "members": members
        }
    }
    k8s.patch_mongodb_cr(namespace, deployment_id, patch)

    repo.update_deployment(tenant_id, deployment_id, {
        "lastRequestedSpec.members": members
    })

    return {
        "tenantId": tenant_id,
        "deploymentId": deployment_id,
        "clusterType": cluster_type,
        "oldMembers": current_members,
        "newMembers": members,
        "warning": warning
    }


def parse_version(version_string: str) -> Tuple[int, int, int]:
    """
    Parse a MongoDB version string like "8.0.3" or "7.0.14-ent" into (major, minor, patch).
    Strips suffixes like "-ent".
    """
    clean_version = version_string.split("-")[0]
    
    parts = clean_version.split(".")
    if len(parts) < 2:
        raise ValueError(f"Invalid version format: {version_string}")
    
    major = int(parts[0])
    minor = int(parts[1])
    patch = int(parts[2]) if len(parts) > 2 else 0
    
    return (major, minor, patch)


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two MongoDB version strings.
    Returns:
      -1 if v1 < v2
       0 if v1 == v2
       1 if v1 > v2
    """
    try:
        parsed_v1 = parse_version(v1)
        parsed_v2 = parse_version(v2)
        
        if parsed_v1 < parsed_v2:
            return -1
        elif parsed_v1 > parsed_v2:
            return 1
        else:
            return 0
    except ValueError:
        ver1 = version.parse(v1.split("-")[0])
        ver2 = version.parse(v2.split("-")[0])
        
        if ver1 < ver2:
            return -1
        elif ver1 > ver2:
            return 1
        else:
            return 0


def upgrade_version(tenant_id: str, deployment_id: str, mongo_version: str) -> Dict[str, Any]:
    """
    Upgrade MongoDB version for a deployment.
    Blocks downgrades, allows same version (no-op), permits upgrades.
    """
    repo = get_repo()
    k8s = get_k8s_client()

    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    deployment = repo.get_deployment(tenant_id, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment {deployment_id} not found for tenant {tenant_id}")

    namespace = tenant["namespace"]

    cr = k8s.get_mongodb_cr(namespace, deployment_id)
    if not cr:
        raise ValueError(f"MongoDB CR {deployment_id} not found in namespace {namespace}")

    cluster_type = cr.get("spec", {}).get("type", "ReplicaSet")
    current_version = cr.get("spec", {}).get("version", "")

    comparison = compare_versions(mongo_version, current_version)

    if comparison < 0:
        raise ValueError(
            f"Downgrades are not supported via this API. "
            f"Current version: {current_version}, requested: {mongo_version}"
        )

    if comparison == 0:
        return {
            "tenantId": tenant_id,
            "deploymentId": deployment_id,
            "clusterType": cluster_type,
            "oldVersion": current_version,
            "newVersion": mongo_version,
            "message": f"No change: deployment is already at version {mongo_version}"
        }

    patch = {
        "spec": {
            "version": mongo_version
        }
    }
    k8s.patch_mongodb_cr(namespace, deployment_id, patch)

    repo.update_deployment(tenant_id, deployment_id, {
        "lastRequestedSpec.mongoVersion": mongo_version
    })

    return {
        "tenantId": tenant_id,
        "deploymentId": deployment_id,
        "clusterType": cluster_type,
        "oldVersion": current_version,
        "newVersion": mongo_version
    }
