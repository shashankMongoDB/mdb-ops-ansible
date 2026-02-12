from typing import Dict, Any
from app.services.mongo_repo import get_repo
from app.services.k8s_client import get_k8s_client
from app.services import monitoring_service
from app.services import deployments_community_service
from app.services import backup_service


def get_connection_info(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Get connection information for a MongoDB deployment.
    
    Automatically creates NodePort service for external access.
    Returns both internal (K8s) and external (VPC) connection URIs.
    
    Supports both enterprise and community deployments.
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
    plan = tenant.get("plan", "enterprise")

    # Get CR based on plan to read replica set name
    if plan == "community":
        cr = k8s.get_mongodb_community_cr(namespace, deployment_id)
    else:
        cr = k8s.get_mongodb_enterprise_cr(namespace, deployment_id)
    
    if not cr:
        raise ValueError(f"MongoDB CR {deployment_id} not found in namespace {namespace}")

    # Get replica set name from CR
    replica_set_name = deployment_id  # Default
    if plan == "community":
        # MongoDBCommunity CR
        replica_set_name = cr.get("spec", {}).get("replicaSet", deployment_id)
    else:
        # MongoDB Enterprise CR
        replica_set_name = cr.get("metadata", {}).get("name", deployment_id)

    # Internal service (ClusterIP)
    internal_service = f"{deployment_id}-svc"
    internal_host_port = f"{internal_service}.{namespace}.svc.cluster.local:27017"
    internal_uri = f"mongodb://{internal_host_port}/?replicaSet={replica_set_name}"
    
    # Ensure external NodePort service exists
    try:
        external_service_name, node_port = k8s.ensure_external_service(namespace, deployment_id)
        worker_node_ip = k8s.get_worker_node_ip()
        
        external_host_port = f"{worker_node_ip}:{node_port}"
        external_uri = f"mongodb://{external_host_port}/?replicaSet={replica_set_name}"
        
        return {
            "namespace": namespace,
            "deploymentId": deployment_id,
            "replicaSet": replica_set_name,
            "internalUri": internal_uri,
            "externalHostPort": external_host_port,
            "externalUri": external_uri
        }
        
    except Exception as e:
        # Fallback if external service creation fails
        return {
            "namespace": namespace,
            "deploymentId": deployment_id,
            "replicaSet": replica_set_name,
            "internalUri": internal_uri,
            "externalHostPort": None,
            "externalUri": None,
            "error": f"Failed to create external service: {str(e)}"
        }


def update_backup_setting(tenant_id: str, deployment_id: str, enabled: bool) -> Dict[str, Any]:
    """
    Enable or disable backup for a MongoDB deployment by patching the CR.
    Only supported for enterprise deployments with Ops Manager.
    """
    repo = get_repo()
    k8s = get_k8s_client()

    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    # Check plan - backup only supported for enterprise
    plan = tenant.get("plan", "enterprise")
    if plan == "community":
        raise ValueError("Backup is not supported for community deployments")

    deployment = repo.get_deployment(tenant_id, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment {deployment_id} not found for tenant {tenant_id}")

    namespace = tenant["namespace"]

    cr = k8s.get_mongodb_cr(namespace, deployment_id)
    if not cr:
        raise ValueError(f"MongoDB CR {deployment_id} not found in namespace {namespace}")

    if enabled:
        patch = {
            "spec": {
                "backup": {
                    "mode": "enabled"
                }
            }
        }
    else:
        patch = {
            "spec": {
                "backup": None
            }
        }

    k8s.patch_mongodb_cr(namespace, deployment_id, patch)

    repo.update_deployment(tenant_id, deployment_id, {
        "lastRequestedSpec.backupEnabled": enabled
    })

    # If enabling backup, ensure backup config + policy in Ops Manager
    if enabled:
        print(f"[LIFECYCLE] Backup enabled, ensuring OM config for {tenant_id}/{deployment_id}")
        try:
            backup_service.ensure_backup_config_and_policy(tenant_id, deployment_id)
        except Exception as e:
            # Don't fail the PATCH if OM is not ready - just log
            print(f"[LIFECYCLE] Could not ensure backup config (OM may not be ready): {str(e)}")

    return {
        "tenantId": tenant_id,
        "deploymentId": deployment_id,
        "backupEnabled": enabled
    }


def update_monitoring_setting(tenant_id: str, deployment_id: str, prometheus_enabled: bool) -> Dict[str, Any]:
    """
    Enable or disable monitoring (Prometheus) for a MongoDB deployment.
    Delegates to existing Prometheus integration.
    """
    if prometheus_enabled:
        result = monitoring_service.enable_prometheus_metrics(tenant_id, deployment_id)
    else:
        result = monitoring_service.disable_prometheus_metrics(tenant_id, deployment_id)

    repo = get_repo()
    repo.update_deployment(tenant_id, deployment_id, {
        "lastRequestedSpec.prometheusEnabled": prometheus_enabled
    })

    return {
        "tenantId": tenant_id,
        "deploymentId": deployment_id,
        "prometheusEnabled": prometheus_enabled
    }


def shutdown_deployment(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Shutdown a deployment by scaling the StatefulSet to 0 replicas.
    Stores the previous replica count for later restoration.
    Supports both enterprise and community deployments.
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
    plan = tenant.get("plan", "enterprise")
    
    # Route to community service if needed
    if plan == "community":
        result = deployments_community_service.shutdown_deployment_community(namespace, deployment_id)
        # Store shutdown info in DB
        repo.update_deployment(tenant_id, deployment_id, {
            "lastRequestedSpec.membersBeforeShutdown": result["previousReplicas"]
        })
        return {
            "tenantId": tenant_id,
            "deploymentId": deployment_id,
            **result
        }
    
    # Enterprise logic continues below

    cr = k8s.get_mongodb_cr(namespace, deployment_id)
    if not cr:
        raise ValueError(f"MongoDB CR {deployment_id} not found in namespace {namespace}")

    statefulset_name = deployment_id
    sts = k8s.get_statefulset(namespace, statefulset_name)
    if not sts:
        raise ValueError(f"StatefulSet {statefulset_name} not found in namespace {namespace}")

    previous_replicas = sts.spec.replicas

    k8s.patch_statefulset_replicas(namespace, statefulset_name, 0)

    repo.update_deployment(tenant_id, deployment_id, {
        "lastRequestedSpec.membersBeforeShutdown": previous_replicas
    })

    return {
        "tenantId": tenant_id,
        "deploymentId": deployment_id,
        "action": "shutdown",
        "previousReplicas": previous_replicas,
        "currentReplicas": 0
    }


def start_deployment(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Start a previously shutdown deployment by scaling the StatefulSet back up.
    Supports both enterprise and community deployments.
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
    plan = tenant.get("plan", "enterprise")
    
    # Get target members from stored shutdown info
    members_before_shutdown = deployment.get("lastRequestedSpec", {}).get("membersBeforeShutdown", 3)
    
    # Route to community service if needed
    if plan == "community":
        result = deployments_community_service.start_deployment_community(namespace, deployment_id, members_before_shutdown)
        return {
            "tenantId": tenant_id,
            "deploymentId": deployment_id,
            **result
        }
    
    # Enterprise logic continues below

    cr = k8s.get_mongodb_cr(namespace, deployment_id)
    if not cr:
        raise ValueError(f"MongoDB CR {deployment_id} not found in namespace {namespace}")

    statefulset_name = deployment_id
    sts = k8s.get_statefulset(namespace, statefulset_name)
    if not sts:
        raise ValueError(f"StatefulSet {statefulset_name} not found in namespace {namespace}")

    members_before_shutdown = deployment.get("lastRequestedSpec", {}).get("membersBeforeShutdown")
    if members_before_shutdown:
        desired_replicas = members_before_shutdown
    else:
        desired_replicas = cr.get("spec", {}).get("members", 3)

    k8s.patch_statefulset_replicas(namespace, statefulset_name, desired_replicas)

    repo.update_deployment(tenant_id, deployment_id, {
        "lastRequestedSpec.membersBeforeShutdown": None
    })

    return {
        "tenantId": tenant_id,
        "deploymentId": deployment_id,
        "action": "start",
        "replicas": desired_replicas
    }


def restart_deployment(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Restart a deployment by performing a rolling restart of all pods.
    Supports both enterprise and community deployments.
    """
    repo = get_repo()
    k8s = get_k8s_client()

    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")
    
    namespace = tenant["namespace"]
    plan = tenant.get("plan", "enterprise")
    
    # Route to community service if needed
    if plan == "community":
        result = deployments_community_service.restart_deployment_community(namespace, deployment_id)
        return {
            "tenantId": tenant_id,
            "deploymentId": deployment_id,
            **result
        }
    
    # Enterprise logic continues below

    deployment = repo.get_deployment(tenant_id, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment {deployment_id} not found for tenant {tenant_id}")

    namespace = tenant["namespace"]

    cr = k8s.get_mongodb_cr(namespace, deployment_id)
    if not cr:
        raise ValueError(f"MongoDB CR {deployment_id} not found in namespace {namespace}")

    statefulset_name = deployment_id
    sts = k8s.get_statefulset(namespace, statefulset_name)
    if not sts:
        raise ValueError(f"StatefulSet {statefulset_name} not found in namespace {namespace}")

    pods = k8s.list_pods_for_statefulset(namespace, statefulset_name)

    for pod in pods:
        pod_name = pod.metadata.name
        
        k8s.delete_pod(namespace, pod_name)
        
        k8s.wait_for_pod_ready(namespace, pod_name, timeout=300)

    return {
        "tenantId": tenant_id,
        "deploymentId": deployment_id,
        "action": "restart",
        "status": "rolling"
    }
