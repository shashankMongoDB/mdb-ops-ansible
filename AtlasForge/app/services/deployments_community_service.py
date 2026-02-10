"""
Community MongoDB deployments service.
Handles MongoDBCommunity CRs (mongodbcommunity.mongodb.com/v1) without Ops Manager.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.services.k8s_client import get_k8s_client

logger = logging.getLogger(__name__)


def create_community_replicaset_cr(
    tenant_id: str,
    deployment_id: str,
    namespace: str,
    mongo_version: str,
    members: int = 3
) -> Dict[str, Any]:
    """
    Build a MongoDBCommunity CR for ReplicaSet.
    No Ops Manager references.
    """
    cr_body = {
        "apiVersion": "mongodbcommunity.mongodb.com/v1",
        "kind": "MongoDBCommunity",
        "metadata": {
            "name": deployment_id,
            "namespace": namespace,
            "labels": {
                "mdb.example.com/tenantId": tenant_id,
                "mdb.example.com/deploymentId": deployment_id
            }
        },
        "spec": {
            "type": "ReplicaSet",
            "members": members,
            "version": mongo_version,
            "security": {
                "authentication": {
                    "modes": ["SCRAM"]
                }
            },
            "users": [
                {
                    "name": "admin",
                    "db": "admin",
                    "passwordSecretRef": {
                        "name": "mongodb-admin-secret"
                    },
                    "roles": [
                        {"name": "clusterAdmin", "db": "admin"},
                        {"name": "userAdminAnyDatabase", "db": "admin"},
                        {"name": "dbAdminAnyDatabase", "db": "admin"},
                        {"name": "readWriteAnyDatabase", "db": "admin"}
                    ],
                    "scramCredentialsSecretName": f"{deployment_id}-admin-scram"
                }
            ],
            "additionalMongodConfig": {
                "storage.wiredTiger.engineConfig.journalCompressor": "snappy"
            }
        }
    }
    
    logger.info(f"Built community ReplicaSet CR: {namespace}/{deployment_id}, members={members}, version={mongo_version}")
    return cr_body


def create_deployment_community(
    tenant_id: str,
    deployment_id: str,
    namespace: str,
    deployment_type: str,
    mongo_version: str,
    display_name: str,
    environment: str,
    members: Optional[int] = None,
    created_by: str = "system"
) -> Dict[str, Any]:
    """
    Create a community MongoDB deployment (MongoDBCommunity CR).
    Only supports ReplicaSet for now.
    """
    logger.info(f"Creating community deployment: {tenant_id}/{deployment_id}, type={deployment_type}")
    
    if deployment_type not in ["ReplicaSet"]:
        raise ValueError(f"Community plan only supports ReplicaSet type. Got: {deployment_type}")
    
    k8s = get_k8s_client()
    
    # Check if CR already exists
    existing_cr = k8s.get_mongodb_community_cr(namespace, deployment_id)
    if existing_cr:
        logger.error(f"Community MongoDB CR already exists: {namespace}/{deployment_id}")
        raise ValueError(f"Community MongoDB CR {deployment_id} already exists in namespace {namespace}")
    
    # Build and create CR
    if members is None:
        members = 3
    
    cr_body = create_community_replicaset_cr(tenant_id, deployment_id, namespace, mongo_version, members)
    k8s.create_mongodb_community_cr(namespace, cr_body)
    
    logger.info(f"Created community MongoDB CR: {namespace}/{deployment_id}")
    
    # Build deployment document for control plane DB
    deployment_doc = {
        "_id": f"{tenant_id}:{deployment_id}",
        "tenantId": tenant_id,
        "deploymentId": deployment_id,
        "namespace": namespace,
        "k8sName": deployment_id,
        "type": deployment_type,
        "plan": "community",
        "displayName": display_name,
        "environment": environment,
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
    
    # Build response
    response = {
        "tenantId": tenant_id,
        "deploymentId": deployment_id,
        "type": deployment_type,
        "mongoVersion": mongo_version,
        "members": members,
        "state": "Creating"
    }
    
    return deployment_doc, response


def get_community_deployment_status(namespace: str, deployment_id: str) -> Dict[str, Any]:
    """
    Get status of a community MongoDB deployment from the CR.
    """
    k8s = get_k8s_client()
    
    cr = k8s.get_mongodb_community_cr(namespace, deployment_id)
    if not cr:
        return {"phase": "Unknown"}
    
    status = cr.get("status", {})
    phase = status.get("phase", "Unknown")
    
    # MongoDBCommunity CR typically has: phase, version, currentStatefulSetReplicas, etc.
    return {
        "phase": phase,
        "currentStatefulSetReplicas": status.get("currentStatefulSetReplicas"),
        "version": status.get("version")
    }


def delete_deployment_community(namespace: str, deployment_id: str) -> bool:
    """
    Delete a community MongoDB deployment CR.
    """
    k8s = get_k8s_client()
    
    logger.info(f"Deleting community deployment: {namespace}/{deployment_id}")
    deleted = k8s.delete_mongodb_community_cr(namespace, deployment_id)
    
    if deleted:
        logger.info(f"Deleted community MongoDB CR: {namespace}/{deployment_id}")
    else:
        logger.warning(f"Community MongoDB CR not found: {namespace}/{deployment_id}")
    
    return deleted


def scale_deployment_community(
    namespace: str,
    deployment_id: str,
    new_members: int
) -> None:
    """
    Scale a community MongoDB ReplicaSet by patching the CR.
    """
    k8s = get_k8s_client()
    
    logger.info(f"Scaling community deployment: {namespace}/{deployment_id} to {new_members} members")
    
    patch = {
        "spec": {
            "members": new_members
        }
    }
    
    k8s.patch_mongodb_community_cr(namespace, deployment_id, patch)
    logger.info(f"Patched community MongoDB CR with members={new_members}")


def upgrade_version_community(
    namespace: str,
    deployment_id: str,
    new_version: str
) -> None:
    """
    Upgrade MongoDB version for a community deployment by patching the CR.
    """
    k8s = get_k8s_client()
    
    logger.info(f"Upgrading community deployment: {namespace}/{deployment_id} to version {new_version}")
    
    patch = {
        "spec": {
            "version": new_version
        }
    }
    
    k8s.patch_mongodb_community_cr(namespace, deployment_id, patch)
    logger.info(f"Patched community MongoDB CR with version={new_version}")


def shutdown_deployment_community(namespace: str, deployment_id: str) -> Dict[str, Any]:
    """
    Shutdown a community deployment by scaling StatefulSet to 0 replicas.
    Community operator may not support this directly via CR, so we manipulate the StatefulSet.
    """
    k8s = get_k8s_client()
    
    logger.info(f"Shutting down community deployment: {namespace}/{deployment_id}")
    
    # Get current StatefulSet
    try:
        sts = k8s.apps_v1.read_namespaced_stateful_set(name=deployment_id, namespace=namespace)
        previous_replicas = sts.spec.replicas
        
        # Scale to 0
        sts.spec.replicas = 0
        k8s.apps_v1.patch_namespaced_stateful_set(name=deployment_id, namespace=namespace, body=sts)
        
        logger.info(f"Shutdown community deployment: {namespace}/{deployment_id}, replicas: {previous_replicas} -> 0")
        
        return {
            "action": "shutdown",
            "previousReplicas": previous_replicas,
            "currentReplicas": 0
        }
    except Exception as e:
        logger.error(f"Failed to shutdown community deployment: {namespace}/{deployment_id}: {e}")
        raise


def start_deployment_community(namespace: str, deployment_id: str, target_members: int) -> Dict[str, Any]:
    """
    Start a community deployment by restoring StatefulSet replicas.
    """
    k8s = get_k8s_client()
    
    logger.info(f"Starting community deployment: {namespace}/{deployment_id} with {target_members} replicas")
    
    try:
        sts = k8s.apps_v1.read_namespaced_stateful_set(name=deployment_id, namespace=namespace)
        
        # Restore replicas
        sts.spec.replicas = target_members
        k8s.apps_v1.patch_namespaced_stateful_set(name=deployment_id, namespace=namespace, body=sts)
        
        logger.info(f"Started community deployment: {namespace}/{deployment_id}, replicas set to {target_members}")
        
        return {
            "action": "start",
            "replicas": target_members
        }
    except Exception as e:
        logger.error(f"Failed to start community deployment: {namespace}/{deployment_id}: {e}")
        raise


def restart_deployment_community(namespace: str, deployment_id: str) -> Dict[str, Any]:
    """
    Restart a community deployment by performing a rolling restart of pods.
    """
    k8s = get_k8s_client()
    
    logger.info(f"Restarting community deployment: {namespace}/{deployment_id}")
    
    try:
        # Annotate StatefulSet to trigger rolling restart
        sts = k8s.apps_v1.read_namespaced_stateful_set(name=deployment_id, namespace=namespace)
        
        if not sts.spec.template.metadata.annotations:
            sts.spec.template.metadata.annotations = {}
        
        sts.spec.template.metadata.annotations["kubectl.kubernetes.io/restartedAt"] = datetime.now(timezone.utc).isoformat()
        
        k8s.apps_v1.patch_namespaced_stateful_set(name=deployment_id, namespace=namespace, body=sts)
        
        logger.info(f"Restarted community deployment: {namespace}/{deployment_id}")
        
        return {
            "action": "restart",
            "status": "Rolling restart initiated"
        }
    except Exception as e:
        logger.error(f"Failed to restart community deployment: {namespace}/{deployment_id}: {e}")
        raise
