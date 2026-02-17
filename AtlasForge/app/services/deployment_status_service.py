"""
Deployment Status Service

Provides real-time status information for MongoDB deployments,
including pod status, replica set topology, and health checks.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.services.k8s_client import K8sClient
from app.services.mongo_repo import MongoRepository


def get_k8s_client() -> K8sClient:
    from app.services.k8s_client import get_k8s_client as get_client
    return get_client()


def get_repo() -> MongoRepository:
    from app.services.mongo_repo import get_repo as get_repository
    return get_repository()


def get_deployment_status(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Get comprehensive status for a deployment including pod status and topology.
    
    Returns:
        {
            "deploymentId": "rs-orders",
            "type": "ReplicaSet",
            "status": "running" | "pending" | "error" | "shutdown",
            "phase": "Running" | "Pending" | "Failed",
            "pods": [...],
            "readyReplicas": 3,
            "totalReplicas": 3,
            "topology": {...},
            "lastUpdated": "2026-02-16T10:30:00Z"
        }
    """
    repo = get_repo()
    k8s = get_k8s_client()
    
    # Get tenant and deployment
    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")
    
    deployment = repo.get_deployment(tenant_id, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment {deployment_id} not found")
    
    namespace = tenant["namespace"]
    deployment_type = deployment.get("type", "ReplicaSet")
    plan = tenant.get("plan", "enterprise")
    
    # Check if deployment is shutdown
    deployment_status = deployment.get("status", "running")
    if deployment_status == "shutdown":
        return {
            "deploymentId": deployment_id,
            "type": deployment_type,
            "status": "shutdown",
            "phase": "Shutdown",
            "pods": [],
            "readyReplicas": 0,
            "totalReplicas": 0,
            "message": "Deployment is currently shutdown",
            "lastUpdated": datetime.now(timezone.utc).isoformat()
        }
    
    # Get pod status based on deployment type
    if deployment_type == "ShardedCluster":
        return _get_sharded_cluster_status(namespace, deployment_id, deployment, plan)
    elif deployment_type == "ReplicaSet":
        return _get_replica_set_status(namespace, deployment_id, deployment, plan)
    else:
        return _get_standalone_status(namespace, deployment_id, deployment, plan)


def _get_replica_set_status(
    namespace: str,
    deployment_id: str,
    deployment: Dict[str, Any],
    plan: str
) -> Dict[str, Any]:
    """Get status for ReplicaSet deployment."""
    k8s = get_k8s_client()
    
    # Get pods
    if plan == "community":
        label_selector = f"app={deployment_id}-svc"
    else:
        label_selector = f"app={deployment_id}-svc"
    
    pods = k8s.core_v1.list_namespaced_pod(
        namespace=namespace,
        label_selector=label_selector
    )
    
    pod_list = []
    ready_count = 0
    
    for pod in pods.items:
        pod_status = _get_pod_info(pod)
        pod_list.append(pod_status)
        if pod_status["ready"]:
            ready_count += 1
    
    # Determine target replicas from CR spec first (source of truth), fallback to DB
    # Determine overall status and operation state
    total_replicas = _get_target_members_from_cr(namespace, deployment_id, plan, deployment)
    actual_replicas = len(pod_list)
    # Use CR spec version as source of truth for upgrade detection
    target_version = _get_target_version_from_cr(namespace, deployment_id, plan, deployment)
    pod_versions = [
        pod.get("version")
        for pod in pod_list
        if pod.get("version") and pod.get("version") != "unknown"
    ]

    if pod_versions and target_version:
        mixed_versions = len(set(pod_versions)) > 1
        has_target_mismatch = any(v != target_version for v in pod_versions)
        fully_ready = ready_count == total_replicas and actual_replicas == total_replicas
        has_upgrade_signal = mixed_versions or has_target_mismatch
        upgrading = has_upgrade_signal and not fully_ready
    else:
        has_upgrade_signal = False
        upgrading = False

    # During replica-count changes, always show scaling (even if versions are mixed).
    if actual_replicas != total_replicas:
        operation = "scaling"
        progress = int((actual_replicas / total_replicas) * 100) if total_replicas > 0 else 0
        operation_message = f"Scaling replicas ({actual_replicas}/{total_replicas} created)"
        status = "partial" if ready_count > 0 else "pending"
        phase = "Scaling"
    elif upgrading and has_upgrade_signal:
        operation = "upgrading"
        progress = int((ready_count / total_replicas) * 100) if total_replicas > 0 else 0
        operation_message = f"Upgrading MongoDB version ({ready_count}/{total_replicas} ready)"
        status = "partial" if ready_count < total_replicas else "running"
        phase = "Upgrading"
    elif ready_count == 0:
        operation = "pending"
        progress = 0
        operation_message = "Waiting for first replica to start"
        status = "pending"
        phase = "Pending"
    elif ready_count < total_replicas:
        operation = "stabilizing"
        progress = int((ready_count / total_replicas) * 100) if total_replicas > 0 else 0
        operation_message = f"Stabilizing replicas ({ready_count}/{total_replicas} ready)"
        status = "partial"
        phase = "Partial"
    else:
        operation = "running"
        progress = 100
        operation_message = "All replicas running"
        status = "running"
        phase = "Running"
    return {
        "deploymentId": deployment_id,
        "type": "ReplicaSet",
        "status": status,
        "phase": phase,
        "pods": pod_list,
        "readyReplicas": ready_count,
        "totalReplicas": total_replicas,
        "operation": operation,
        "progress": progress,
        "operationMessage": operation_message,
        "topology": {
            "replicaSet": {
                "name": deployment_id,
                "members": pod_list
            }
        },
        "lastUpdated": datetime.now(timezone.utc).isoformat()
    }


def _get_target_members_from_cr(
    namespace: str,
    deployment_id: str,
    plan: str,
    deployment: Dict[str, Any]
) -> int:
    """Get target member count from CR spec; fallback to DB deployment value."""
    k8s = get_k8s_client()
    fallback_members = deployment.get("members", 3)

    try:
        if plan == "community":
            cr = k8s.get_mongodb_community_cr(namespace, deployment_id)
        else:
            cr = k8s.get_mongodb_enterprise_cr(namespace, deployment_id)

        if cr:
            return cr.get("spec", {}).get("members", fallback_members) or fallback_members
    except Exception:
        pass

    return fallback_members


def _get_target_version_from_cr(
    namespace: str,
    deployment_id: str,
    plan: str,
    deployment: Dict[str, Any]
) -> str:
    """Get target MongoDB version from CR spec; fallback to DB deployment value."""
    k8s = get_k8s_client()
    fallback_version = deployment.get("lastRequestedSpec", {}).get("mongoVersion", "") or deployment.get("mongoVersion", "")

    try:
        if plan == "community":
            cr = k8s.get_mongodb_community_cr(namespace, deployment_id)
        else:
            cr = k8s.get_mongodb_enterprise_cr(namespace, deployment_id)

        if cr:
            return cr.get("spec", {}).get("version", fallback_version) or fallback_version
    except Exception:
        pass

    return fallback_version


def _get_sharded_cluster_status(
    namespace: str,
    deployment_id: str,
    deployment: Dict[str, Any],
    plan: str
) -> Dict[str, Any]:
    """Get status for ShardedCluster deployment."""
    k8s = get_k8s_client()
    
    shard_count = deployment.get("shardCount", 2)
    mongods_per_shard = deployment.get("mongodsPerShardCount", 3)
    mongos_count = deployment.get("mongosCount", 2)
    config_count = deployment.get("configServerCount", 3)
    
    total_replicas = 0
    ready_replicas = 0
    
    shards = []
    
    # Get status for each shard
    for i in range(shard_count):
        shard_name = f"{deployment_id}-shard-{i}"
        shard_pods = k8s.core_v1.list_namespaced_pod(
            namespace=namespace,
            label_selector=f"app={shard_name}-svc"
        )
        
        shard_members = []
        shard_ready = 0
        
        for pod in shard_pods.items:
            pod_info = _get_pod_info(pod)
            shard_members.append(pod_info)
            if pod_info["ready"]:
                shard_ready += 1
        
        total_replicas += len(shard_members)
        ready_replicas += shard_ready
        
        shards.append({
            "name": f"shard-{i}",
            "members": shard_members,
            "readyMembers": shard_ready,
            "totalMembers": len(shard_members)
        })
    
    # Get config server status
    config_pods = k8s.core_v1.list_namespaced_pod(
        namespace=namespace,
        label_selector=f"app={deployment_id}-configsvr-svc"
    )
    
    config_members = []
    config_ready = 0
    
    for pod in config_pods.items:
        pod_info = _get_pod_info(pod)
        config_members.append(pod_info)
        if pod_info["ready"]:
            config_ready += 1
    
    total_replicas += len(config_members)
    ready_replicas += config_ready
    
    # Get mongos status
    mongos_pods = k8s.core_v1.list_namespaced_pod(
        namespace=namespace,
        label_selector=f"app.kubernetes.io/instance={deployment_id}"
    )
    
    mongos_instances = []
    mongos_ready = 0
    
    for pod in mongos_pods.items:
        if "mongos" in pod.metadata.name:
            pod_info = _get_pod_info(pod)
            mongos_instances.append(pod_info)
            if pod_info["ready"]:
                mongos_ready += 1
    
    total_replicas += len(mongos_instances)
    ready_replicas += mongos_ready
    
    # Determine overall status
    if ready_replicas == 0:
        status = "pending"
        phase = "Pending"
    elif ready_replicas < total_replicas:
        status = "partial"
        phase = "Partial"
    else:
        status = "running"
        phase = "Running"
    
    return {
        "deploymentId": deployment_id,
        "type": "ShardedCluster",
        "status": status,
        "phase": phase,
        "pods": [],  # All pods are in topology
        "readyReplicas": ready_replicas,
        "totalReplicas": total_replicas,
        "topology": {
            "shards": shards,
            "configServers": {
                "members": config_members,
                "readyMembers": config_ready,
                "totalMembers": len(config_members)
            },
            "mongos": {
                "instances": mongos_instances,
                "readyInstances": mongos_ready,
                "totalInstances": len(mongos_instances)
            }
        },
        "lastUpdated": datetime.now(timezone.utc).isoformat()
    }


def _get_standalone_status(
    namespace: str,
    deployment_id: str,
    deployment: Dict[str, Any],
    plan: str
) -> Dict[str, Any]:
    """Get status for Standalone deployment."""
    k8s = get_k8s_client()
    
    # Community standalone uses different labels
    if plan == "community":
        label_selector = f"app={deployment_id}"
    else:
        label_selector = f"app={deployment_id}-svc"
    
    pods = k8s.core_v1.list_namespaced_pod(
        namespace=namespace,
        label_selector=label_selector
    )
    
    pod_list = []
    ready_count = 0
    
    for pod in pods.items:
        pod_status = _get_pod_info(pod)
        pod_list.append(pod_status)
        if pod_status["ready"]:
            ready_count += 1
    
    # Standalone should have 1 pod
    total_replicas = 1
    
    if ready_count == 0:
        status = "pending"
        phase = "Pending"
    else:
        status = "running"
        phase = "Running"
    
    return {
        "deploymentId": deployment_id,
        "type": "Standalone",
        "status": status,
        "phase": phase,
        "pods": pod_list,
        "readyReplicas": ready_count,
        "totalReplicas": total_replicas,
        "topology": {
            "standalone": {
                "pod": pod_list[0] if pod_list else None
            }
        },
        "lastUpdated": datetime.now(timezone.utc).isoformat()
    }


def _get_pod_info(pod) -> Dict[str, Any]:
    """Extract relevant information from a pod object."""
    # Get container statuses
    container_statuses = []
    if pod.status.container_statuses:
        for cs in pod.status.container_statuses:
            container_statuses.append({
                "name": cs.name,
                "ready": cs.ready,
                "restartCount": cs.restart_count,
                "state": _get_container_state(cs.state)
            })
    
    # Determine if pod is ready
    is_ready = False
    if pod.status.conditions:
        for condition in pod.status.conditions:
            if condition.type == "Ready" and condition.status == "True":
                is_ready = True
                break
    
    # Extract MongoDB version from container image
    mongo_version = "unknown"
    if pod.status.container_statuses:
        for cs in pod.status.container_statuses:
            image = getattr(cs, "image", "") or ""
            if "mongo" in image.lower() and ":" in image:
                mongo_version = image.rsplit(":", 1)[-1]
                break

    return {
        "name": pod.metadata.name,
        "status": pod.status.phase,
        "ready": is_ready,
        "version": mongo_version,
        "containerStatuses": container_statuses,
        "nodeName": pod.spec.node_name,
        "podIP": pod.status.pod_ip,
        "startTime": pod.status.start_time.isoformat() if pod.status.start_time else None,
        "message": pod.status.message or ""
    }


def _get_container_state(state) -> str:
    """Get human-readable container state."""
    if state.running:
        return "Running"
    elif state.waiting:
        return f"Waiting: {state.waiting.reason}"
    elif state.terminated:
        return f"Terminated: {state.terminated.reason}"
    else:
        return "Unknown"


def get_all_deployments_status(tenant_id: str) -> List[Dict[str, Any]]:
    """
    Get status for all deployments in a tenant.
    Useful for overview page with polling.
    """
    repo = get_repo()
    
    deployments = repo.list_deployments(tenant_id)
    
    status_list = []
    for deployment in deployments:
        try:
            status = get_deployment_status(tenant_id, deployment["deploymentId"])
            status_list.append(status)
        except Exception as e:
            # If one deployment fails, continue with others
            print(f"[STATUS] Error getting status for {deployment['deploymentId']}: {e}")
            status_list.append({
                "deploymentId": deployment["deploymentId"],
                "type": deployment.get("type", "Unknown"),
                "status": "error",
                "phase": "Error",
                "error": str(e),
                "lastUpdated": datetime.now(timezone.utc).isoformat()
            })
    
    return status_list
