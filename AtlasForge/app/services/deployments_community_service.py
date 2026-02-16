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
    Shutdown a community deployment by deleting the MongoDBCommunity CR.
    This stops the operator from reconciling, then we force delete pods.
    PVCs are preserved so data is not lost.
    """
    k8s = get_k8s_client()
    
    logger.info(f"Shutting down community deployment: {namespace}/{deployment_id}")
    
    # Step 1: Get current CR to save spec for restart
    cr = k8s.get_mongodb_community_cr(namespace, deployment_id)
    if not cr:
        raise ValueError(f"MongoDBCommunity CR {deployment_id} not found in namespace {namespace}")
    
    spec = cr.get("spec", {})
    metadata = cr.get("metadata", {})
    previous_replicas = spec.get("members", 3)
    
    # Save full CR for restart
    shutdown_info = {
        "cr_spec": spec,
        "cr_metadata_labels": metadata.get("labels", {}),
        "cr_metadata_annotations": metadata.get("annotations", {}),
        "previous_replicas": previous_replicas
    }
    
    logger.info(f"Saved CR spec for {deployment_id}, members={previous_replicas}")
    
    # Step 2: Delete MongoDBCommunity CR
    try:
        k8s.custom_objects.delete_namespaced_custom_object(
            group="mongodbcommunity.mongodb.com",
            version="v1",
            namespace=namespace,
            plural="mongodbcommunity",
            name=deployment_id
        )
        logger.info(f"Deleted MongoDBCommunity CR: {namespace}/{deployment_id}")
    except Exception as e:
        logger.error(f"Failed to delete MongoDBCommunity CR: {e}")
        raise ValueError(f"Failed to delete MongoDBCommunity CR: {e}")
    
    # Step 3: Wait for operator to process deletion
    import time
    time.sleep(2)
    
    # Step 4: Force delete all pods
    try:
        pods = k8s.core_v1.list_namespaced_pod(
            namespace=namespace,
            label_selector=f"app={deployment_id}-svc"
        )
        
        logger.info(f"Found {len(pods.items)} pods to delete for {deployment_id}")
        
        for pod in pods.items:
            try:
                k8s.delete_pod(namespace, pod.metadata.name, grace_period=0)
                logger.info(f"Force deleted pod: {pod.metadata.name}")
            except Exception as pod_e:
                logger.warning(f"Could not delete pod {pod.metadata.name}: {pod_e}")
            
    except Exception as e:
        logger.warning(f"Error during pod cleanup: {e}")
    
    logger.info(f"Shutdown complete for community deployment: {namespace}/{deployment_id}")
    
    return {
        "action": "shutdown",
        "previousReplicas": previous_replicas,
        "currentReplicas": 0,
        "shutdownInfo": shutdown_info
    }


def start_deployment_community(namespace: str, deployment_id: str, shutdown_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Start a community deployment by recreating the MongoDBCommunity CR.
    The CR spec is restored from shutdown_info saved during shutdown.
    Pods will automatically be created by the operator.
    """
    k8s = get_k8s_client()
    
    logger.info(f"Starting community deployment: {namespace}/{deployment_id}")
    
    if not shutdown_info or "cr_spec" not in shutdown_info:
        raise ValueError(f"No shutdown info found for {deployment_id}. Cannot restore without saved CR spec.")
    
    cr_spec = shutdown_info.get("cr_spec")
    cr_labels = shutdown_info.get("cr_metadata_labels", {})
    cr_annotations = shutdown_info.get("cr_metadata_annotations", {})
    previous_replicas = shutdown_info.get("previous_replicas", 3)
    
    logger.info(f"Restoring MongoDBCommunity CR for {deployment_id} with {previous_replicas} members")
    
    # Recreate the MongoDBCommunity CR
    mongodb_cr = {
        "apiVersion": "mongodbcommunity.mongodb.com/v1",
        "kind": "MongoDBCommunity",
        "metadata": {
            "name": deployment_id,
            "namespace": namespace,
            "labels": cr_labels,
            "annotations": cr_annotations
        },
        "spec": cr_spec
    }
    
    try:
        k8s.custom_objects.create_namespaced_custom_object(
            group="mongodbcommunity.mongodb.com",
            version="v1",
            namespace=namespace,
            plural="mongodbcommunity",
            body=mongodb_cr
        )
        logger.info(f"Recreated MongoDBCommunity CR: {namespace}/{deployment_id}")
    except Exception as e:
        logger.error(f"Failed to recreate MongoDBCommunity CR: {e}")
        raise ValueError(f"Failed to recreate MongoDBCommunity CR: {e}")
    
    logger.info(f"Start complete for community deployment: {namespace}/{deployment_id}")
    
    return {
        "action": "start",
        "replicas": previous_replicas
    }


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
