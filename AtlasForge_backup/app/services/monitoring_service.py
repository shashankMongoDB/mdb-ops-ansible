from typing import Dict, Any, Optional
from app.services.mongo_repo import get_repo
from app.services.k8s_client import get_k8s_client


def enable_prometheus_metrics(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Enable Prometheus metrics for a MongoDB deployment by:
    1. Patching the MongoDB CR to enable spec.prometheus
    2. Creating a LoadBalancer Service to expose port 9216
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

    patch = {
        "spec": {
            "prometheus": {
                "username": "prometheus-user",
                "passwordSecretRef": {
                    "name": "mongodb-admin-secret"
                }
            }
        }
    }
    k8s.patch_mongodb_cr(namespace, deployment_id, patch)

    selector_labels = {
        "app": f"{deployment_id}-svc"
    }
    k8s.ensure_metrics_service(namespace, deployment_id, selector_labels)

    repo.update_deployment(tenant_id, deployment_id, {
        "prometheusEnabled": True
    })

    return {
        "enabled": True,
        "namespace": namespace,
        "serviceName": f"{deployment_id}-metrics",
        "port": 9216
    }


def disable_prometheus_metrics(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Disable Prometheus metrics for a MongoDB deployment by:
    1. Patching the MongoDB CR to remove spec.prometheus
    2. Deleting the metrics Service
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
    if cr:
        patch = {
            "spec": {
                "prometheus": None
            }
        }
        k8s.patch_mongodb_cr(namespace, deployment_id, patch)

    service_name = f"{deployment_id}-metrics"
    k8s.delete_service(namespace, service_name)

    repo.update_deployment(tenant_id, deployment_id, {
        "prometheusEnabled": False
    })

    return {"enabled": False}


def get_prometheus_config(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Get Prometheus metrics configuration for a MongoDB deployment.
    Returns enabled status, service info, and external access details.
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

    prometheus_enabled = cr.get("spec", {}).get("prometheus") is not None

    if not prometheus_enabled:
        return {"enabled": False}

    service_name = f"{deployment_id}-metrics"
    svc_info = k8s.get_service(namespace, service_name)

    result = {
        "enabled": True,
        "namespace": namespace,
        "serviceName": service_name,
        "port": 9216,
        "metricsPath": "/metrics"
    }

    if svc_info:
        external_ips = svc_info.get("externalIPs", [])
        if external_ips and len(external_ips) > 0:
            ingress = external_ips[0]
            if hasattr(ingress, 'ip') and ingress.ip:
                result["externalHost"] = ingress.ip
            elif hasattr(ingress, 'hostname') and ingress.hostname:
                result["externalHost"] = ingress.hostname

        ports = svc_info.get("ports", [])
        if ports and len(ports) > 0:
            port_info = ports[0]
            if port_info.get("nodePort"):
                result["externalPort"] = port_info["nodePort"]
                result["serviceType"] = "NodePort"
            else:
                result["externalPort"] = 9216
                result["serviceType"] = svc_info.get("type", "LoadBalancer")

    return result
