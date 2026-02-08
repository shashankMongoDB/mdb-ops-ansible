import copy
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.services.mongo_repo import get_repo
from app.services.k8s_client import get_k8s_client
from app.services.tenants_service import validate_dns_safe


BASE_STANDALONE_CR = {
    "apiVersion": "mongodb.com/v1",
    "kind": "MongoDB",
    "metadata": {
        "name": "",
        "namespace": "",
        "labels": {}
    },
    "spec": {
        "type": "Standalone",
        "version": "",
        "opsManager": {
            "configMapRef": {"name": ""}
        },
        "credentials": ""
    }
}


BASE_RS_CR = {
    "apiVersion": "mongodb.com/v1",
    "kind": "MongoDB",
    "metadata": {
        "name": "",
        "namespace": "",
        "labels": {}
    },
    "spec": {
        "type": "ReplicaSet",
        "members": 3,
        "version": "",
        "opsManager": {
            "configMapRef": {"name": ""}
        },
        "credentials": "",
        "security": {
            "authentication": {
                "enabled": True,
                "modes": ["SCRAM"]
            }
        },
        "users": []
    }
}


BASE_SHARDED_CR = {
    "apiVersion": "mongodb.com/v1",
    "kind": "MongoDB",
    "metadata": {
        "name": "",
        "namespace": "",
        "labels": {}
    },
    "spec": {
        "type": "ShardedCluster",
        "version": "",
        "shardCount": 2,
        "mongodsPerShardCount": 3,
        "mongosCount": 2,
        "configServerCount": 3,
        "opsManager": {
            "configMapRef": {"name": ""}
        },
        "credentials": "",
        "security": {
            "authentication": {
                "enabled": True,
                "modes": ["SCRAM"]
            }
        }
    }
}


def create_deployment(
    tenant_id: str,
    deployment_id: str,
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
) -> Dict[str, Any]:
    """
    Create a MongoDB deployment of type Standalone, ReplicaSet, or ShardedCluster.
    """
    if not validate_dns_safe(deployment_id):
        raise ValueError(f"deploymentId '{deployment_id}' is not DNS-safe (must be [a-z0-9-], max 63 chars)")

    if deployment_type not in ["Standalone", "ReplicaSet", "ShardedCluster"]:
        raise ValueError(f"Invalid deployment type: {deployment_type}. Must be Standalone, ReplicaSet, or ShardedCluster")

    repo = get_repo()
    k8s = get_k8s_client()

    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    if repo.get_deployment(tenant_id, deployment_id):
        raise ValueError(f"Deployment {deployment_id} already exists for tenant {tenant_id}")

    namespace = tenant["namespace"]

    existing_cr = k8s.get_mongodb_cr(namespace, deployment_id)
    if existing_cr:
        raise ValueError(f"MongoDB CR {deployment_id} already exists in namespace {namespace}")

    if deployment_type == "Standalone":
        cr_body = _create_standalone_cr(tenant_id, deployment_id, namespace, mongo_version)
        deployment_doc = _create_standalone_doc(tenant_id, deployment_id, namespace, display_name, environment, mongo_version, created_by)
        response = {
            "tenantId": tenant_id,
            "deploymentId": deployment_id,
            "type": "Standalone",
            "mongoVersion": mongo_version,
            "state": "Creating"
        }

    elif deployment_type == "ReplicaSet":
        if members is None:
            members = 3
        cr_body = _create_replicaset_cr(tenant_id, deployment_id, namespace, mongo_version, members)
        deployment_doc = _create_replicaset_doc(tenant_id, deployment_id, namespace, display_name, environment, mongo_version, members, created_by)
        response = {
            "tenantId": tenant_id,
            "deploymentId": deployment_id,
            "type": "ReplicaSet",
            "mongoVersion": mongo_version,
            "members": members,
            "state": "Creating"
        }

    elif deployment_type == "ShardedCluster":
        if shard_count is None or mongods_per_shard_count is None or mongos_count is None or config_server_count is None:
            raise ValueError("ShardedCluster requires shardCount, mongodsPerShardCount, mongosCount, and configServerCount")
        
        if shard_count < 1:
            raise ValueError("shardCount must be at least 1")
        if mongods_per_shard_count < 1:
            raise ValueError("mongodsPerShardCount must be at least 1")
        if mongos_count < 1:
            raise ValueError("mongosCount must be at least 1")
        if config_server_count < 3:
            raise ValueError("configServerCount must be at least 3")

        cr_body = _create_sharded_cr(tenant_id, deployment_id, namespace, mongo_version, shard_count, mongods_per_shard_count, mongos_count, config_server_count)
        deployment_doc = _create_sharded_doc(tenant_id, deployment_id, namespace, display_name, environment, mongo_version, shard_count, mongods_per_shard_count, mongos_count, config_server_count, created_by)
        response = {
            "tenantId": tenant_id,
            "deploymentId": deployment_id,
            "type": "ShardedCluster",
            "mongoVersion": mongo_version,
            "shardCount": shard_count,
            "mongodsPerShardCount": mongods_per_shard_count,
            "mongosCount": mongos_count,
            "configServerCount": config_server_count,
            "state": "Creating"
        }

    k8s.create_mongodb_cr(namespace, cr_body)
    repo.insert_deployment(deployment_doc)

    return response


def _create_standalone_cr(tenant_id: str, deployment_id: str, namespace: str, mongo_version: str) -> Dict[str, Any]:
    """
    Create a Standalone MongoDB CR.
    
    Note: Standalone deployments cannot be secured with SCRAM authentication in Kubernetes
    when using MongoDB Enterprise Operator. Security and users configuration must be omitted
    to allow the operator to successfully create the StatefulSet and pod. Standalone instances
    are left unsecured and intended for dev/test environments only.
    
    See MongoDB Enterprise Operator documentation for details.
    """
    cr_body = copy.deepcopy(BASE_STANDALONE_CR)
    cr_body["metadata"]["name"] = deployment_id
    cr_body["metadata"]["namespace"] = namespace
    cr_body["metadata"]["labels"]["mdb.example.com/tenantId"] = tenant_id
    cr_body["spec"]["version"] = mongo_version
    cr_body["spec"]["opsManager"]["configMapRef"]["name"] = f"om-{tenant_id}-project"
    cr_body["spec"]["credentials"] = f"om-{tenant_id}-credentials"
    
    # DO NOT add spec.security or spec.users for Standalone deployments
    # The operator cannot reconcile Standalone with authentication enabled
    
    return cr_body


def _create_replicaset_cr(tenant_id: str, deployment_id: str, namespace: str, mongo_version: str, members: int) -> Dict[str, Any]:
    """Create a ReplicaSet MongoDB CR."""
    cr_body = copy.deepcopy(BASE_RS_CR)
    cr_body["metadata"]["name"] = deployment_id
    cr_body["metadata"]["namespace"] = namespace
    cr_body["metadata"]["labels"]["mdb.example.com/tenantId"] = tenant_id
    cr_body["spec"]["version"] = mongo_version
    cr_body["spec"]["members"] = members
    cr_body["spec"]["opsManager"]["configMapRef"]["name"] = f"om-{tenant_id}-project"
    cr_body["spec"]["credentials"] = f"om-{tenant_id}-credentials"
    cr_body["spec"]["users"] = [
        {
            "name": "dbAdmin",
            "db": "admin",
            "passwordSecretRef": {"name": "mongodb-admin-secret"},
            "roles": [{"name": "root", "db": "admin"}],
            "scramCredentialsSecretName": f"{deployment_id}-admin-scram"
        }
    ]
    return cr_body


def _create_sharded_cr(tenant_id: str, deployment_id: str, namespace: str, mongo_version: str, shard_count: int, mongods_per_shard_count: int, mongos_count: int, config_server_count: int) -> Dict[str, Any]:
    """Create a ShardedCluster MongoDB CR."""
    cr_body = copy.deepcopy(BASE_SHARDED_CR)
    cr_body["metadata"]["name"] = deployment_id
    cr_body["metadata"]["namespace"] = namespace
    cr_body["metadata"]["labels"]["mdb.example.com/tenantId"] = tenant_id
    cr_body["spec"]["version"] = mongo_version
    cr_body["spec"]["shardCount"] = shard_count
    cr_body["spec"]["mongodsPerShardCount"] = mongods_per_shard_count
    cr_body["spec"]["mongosCount"] = mongos_count
    cr_body["spec"]["configServerCount"] = config_server_count
    cr_body["spec"]["opsManager"]["configMapRef"]["name"] = f"om-{tenant_id}-project"
    cr_body["spec"]["credentials"] = f"om-{tenant_id}-credentials"
    return cr_body


def _create_standalone_doc(tenant_id: str, deployment_id: str, namespace: str, display_name: str, environment: str, mongo_version: str, created_by: str) -> Dict[str, Any]:
    """Create deployment document for Standalone."""
    return {
        "_id": f"{tenant_id}:{deployment_id}",
        "tenantId": tenant_id,
        "deploymentId": deployment_id,
        "namespace": namespace,
        "k8sName": deployment_id,
        "type": "Standalone",
        "displayName": display_name,
        "environment": environment,
        "plan": "gold",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "createdBy": created_by,
        "lastUpdatedAt": datetime.now(timezone.utc).isoformat(),
        "lastRequestedSpec": {
            "mongoVersion": mongo_version
        },
        "lastKnownStatus": {
            "phase": "Creating"
        }
    }


def _create_replicaset_doc(tenant_id: str, deployment_id: str, namespace: str, display_name: str, environment: str, mongo_version: str, members: int, created_by: str) -> Dict[str, Any]:
    """Create deployment document for ReplicaSet."""
    return {
        "_id": f"{tenant_id}:{deployment_id}",
        "tenantId": tenant_id,
        "deploymentId": deployment_id,
        "namespace": namespace,
        "k8sName": deployment_id,
        "type": "ReplicaSet",
        "displayName": display_name,
        "environment": environment,
        "plan": "gold",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "createdBy": created_by,
        "lastUpdatedAt": datetime.now(timezone.utc).isoformat(),
        "lastRequestedSpec": {
            "mongoVersion": mongo_version,
            "members": members
        },
        "lastKnownStatus": {
            "phase": "Creating"
        }
    }


def _create_sharded_doc(tenant_id: str, deployment_id: str, namespace: str, display_name: str, environment: str, mongo_version: str, shard_count: int, mongods_per_shard_count: int, mongos_count: int, config_server_count: int, created_by: str) -> Dict[str, Any]:
    """Create deployment document for ShardedCluster."""
    return {
        "_id": f"{tenant_id}:{deployment_id}",
        "tenantId": tenant_id,
        "deploymentId": deployment_id,
        "namespace": namespace,
        "k8sName": deployment_id,
        "type": "ShardedCluster",
        "displayName": display_name,
        "environment": environment,
        "plan": "gold",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "createdBy": created_by,
        "lastUpdatedAt": datetime.now(timezone.utc).isoformat(),
        "lastRequestedSpec": {
            "mongoVersion": mongo_version,
            "shardCount": shard_count,
            "mongodsPerShardCount": mongods_per_shard_count,
            "mongosCount": mongos_count,
            "configServerCount": config_server_count
        },
        "lastKnownStatus": {
            "phase": "Creating"
        }
    }


def get_deployment_details(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    repo = get_repo()
    k8s = get_k8s_client()

    deployment = repo.get_deployment(tenant_id, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment {deployment_id} not found for tenant {tenant_id}")

    result = {
        "tenantId": deployment["tenantId"],
        "deploymentId": deployment["deploymentId"],
        "displayName": deployment["displayName"],
        "environment": deployment["environment"],
        "mongoVersion": deployment["lastRequestedSpec"]["mongoVersion"],
        "createdAt": deployment["createdAt"],
        "state": deployment["lastKnownStatus"].get("phase", "Unknown")
    }
    
    # Add members only if present (ReplicaSet)
    if "members" in deployment["lastRequestedSpec"]:
        result["members"] = deployment["lastRequestedSpec"]["members"]

    cr = k8s.get_mongodb_cr(deployment["namespace"], deployment_id)
    if cr and "status" in cr:
        result["k8sPhase"] = cr["status"].get("phase", "Unknown")

    return result


def list_tenant_deployments(tenant_id: str) -> list[Dict[str, Any]]:
    repo = get_repo()

    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    deployments = repo.list_deployments(tenant_id)

    result = []
    for d in deployments:
        item = {
            "tenantId": d["tenantId"],
            "deploymentId": d["deploymentId"],
            "displayName": d["displayName"],
            "environment": d["environment"],
            "mongoVersion": d["lastRequestedSpec"]["mongoVersion"],
            "state": d["lastKnownStatus"].get("phase", "Unknown"),
            "createdAt": d["createdAt"]
        }
        
        # Add members only if present (ReplicaSet)
        if "members" in d["lastRequestedSpec"]:
            item["members"] = d["lastRequestedSpec"]["members"]
        
        result.append(item)
    
    return result


def delete_deployment(tenant_id: str, deployment_id: str) -> bool:
    """
    Delete a deployment by removing the MongoDB CR from Kubernetes
    and the deployment document from control-plane DB.
    Returns True if something was deleted, False if nothing existed.
    """
    repo = get_repo()
    k8s = get_k8s_client()

    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    namespace = tenant["namespace"]

    k8s_deleted = k8s.delete_mongodb_cr(namespace, deployment_id)
    db_deleted = repo.delete_deployment(tenant_id, deployment_id)

    return k8s_deleted or db_deleted
