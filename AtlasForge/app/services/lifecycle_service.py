from typing import Dict, Any
from app.services.mongo_repo import get_repo
from app.services.k8s_client import get_k8s_client
from app.services import monitoring_service


def get_connection_info(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Get connection information for a MongoDB deployment.
    Returns connection URI and mongosh example.
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

    service_name = f"{deployment_id}-svc"
    port = 27017

    mongo_uri = f"mongodb://{service_name}.{namespace}.svc.cluster.local:{port}"
    mongosh_example = f'mongosh "{mongo_uri}"'

    return {
        "tenantId": tenant_id,
        "deploymentId": deployment_id,
        "mongoUri": mongo_uri,
        "mongoshExample": mongosh_example
    }


def update_backup_setting(tenant_id: str, deployment_id: str, enabled: bool) -> Dict[str, Any]:
    """
    Enable or disable backup for a MongoDB deployment by patching the CR.
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
    Deletes each pod in order and waits for it to become ready before proceeding.
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
