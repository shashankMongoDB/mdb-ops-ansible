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
    plan = tenant.get("plan", "enterprise")

    # Get CR based on plan
    if plan == "community":
        cr = k8s.get_mongodb_community_cr(namespace, deployment_id)
    else:
        cr = k8s.get_mongodb_enterprise_cr(namespace, deployment_id)
    
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
    
    # Patch CR based on plan
    if plan == "community":
        k8s.patch_mongodb_community_cr(namespace, deployment_id, patch)
    else:
        k8s.patch_mongodb_enterprise_cr(namespace, deployment_id, patch)

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
    plan = tenant.get("plan", "enterprise")

    # Get CR based on plan
    if plan == "community":
        cr = k8s.get_mongodb_community_cr(namespace, deployment_id)
    else:
        cr = k8s.get_mongodb_enterprise_cr(namespace, deployment_id)
    
    if cr:
        patch = {
            "spec": {
                "prometheus": None
            }
        }
        # Patch CR based on plan
        if plan == "community":
            k8s.patch_mongodb_community_cr(namespace, deployment_id, patch)
        else:
            k8s.patch_mongodb_enterprise_cr(namespace, deployment_id, patch)

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
    plan = tenant.get("plan", "enterprise")

    # Get CR based on plan
    if plan == "community":
        cr = k8s.get_mongodb_community_cr(namespace, deployment_id)
    else:
        cr = k8s.get_mongodb_enterprise_cr(namespace, deployment_id)
    
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


def mask_password(pw: str) -> str:
    """
    Mask password showing only last 4 characters.
    """
    if not pw:
        return "****"
    if len(pw) <= 4:
        return "****"
    return "*" * (len(pw) - 4) + pw[-4:]


def get_prometheus_scrape_config(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Get ready-to-use Prometheus scrape configuration for a deployment.
    Includes YAML config, worker node IPs, and credentials.
    
    Password is shown in full only on first view (when prometheus.firstViewedAt is null).
    Subsequent views show masked password.
    
    Supports both enterprise and community deployments.
    """
    from datetime import datetime, timezone
    
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

    # Auto-enable Prometheus if not already enabled
    prometheus_enabled = deployment.get("prometheusEnabled", False)
    if not prometheus_enabled:
        # Enable Prometheus metrics
        if plan == "community":
            cr = k8s.get_mongodb_community_cr(namespace, deployment_id)
        else:
            cr = k8s.get_mongodb_enterprise_cr(namespace, deployment_id)
        
        if not cr:
            raise ValueError(f"MongoDB CR {deployment_id} not found in namespace {namespace}")

        # Check if prometheus is already configured in CR
        cr_has_prometheus = cr.get("spec", {}).get("prometheus") is not None
        
        if not cr_has_prometheus:
            # Patch CR to enable prometheus
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
            
            if plan == "community":
                k8s.patch_mongodb_community_cr(namespace, deployment_id, patch)
            else:
                k8s.patch_mongodb_enterprise_cr(namespace, deployment_id, patch)

            selector_labels = {
                "app": f"{deployment_id}-svc"
            }
            k8s.ensure_metrics_service(namespace, deployment_id, selector_labels)

            repo.update_deployment(tenant_id, deployment_id, {
                "prometheusEnabled": True
            })
            
            # Reload deployment
            deployment = repo.get_deployment(tenant_id, deployment_id)

    # Get CR to read prometheus config
    if plan == "community":
        cr = k8s.get_mongodb_community_cr(namespace, deployment_id)
    else:
        cr = k8s.get_mongodb_enterprise_cr(namespace, deployment_id)
    
    if not cr:
        raise ValueError(f"MongoDB CR {deployment_id} not found in namespace {namespace}")

    prometheus_spec = cr.get("spec", {}).get("prometheus", {})
    username = prometheus_spec.get("username", "prometheus-user")
    password_secret_ref = prometheus_spec.get("passwordSecretRef", {})
    secret_name = password_secret_ref.get("name", "mongodb-admin-secret")
    secret_key = password_secret_ref.get("key", "password")

    # Read password from secret
    password_raw = k8s.get_secret_data(namespace, secret_name, secret_key)
    if not password_raw:
        raise ValueError(f"Password secret {secret_name} not found or empty in namespace {namespace}")

    # Check if this is first view
    prometheus_meta = deployment.get("prometheus", {})
    first_viewed_at = prometheus_meta.get("firstViewedAt")
    
    if first_viewed_at is None:
        # First view - show full password and mark as viewed
        password = password_raw
        repo.update_deployment(tenant_id, deployment_id, {
            "prometheus.firstViewedAt": datetime.now(timezone.utc).isoformat()
        })
        is_first_view = True
    else:
        # Subsequent view - mask password
        password = mask_password(password_raw)
        is_first_view = False

    # Get metrics service
    service_name = f"{deployment_id}-metrics"
    svc_info = k8s.get_service(namespace, service_name)
    
    if not svc_info:
        raise ValueError(f"Metrics service {service_name} not found in namespace {namespace}")

    # Extract NodePort
    node_port = None
    ports = svc_info.get("ports", [])
    if ports and len(ports) > 0:
        node_port = ports[0].get("nodePort")
    
    if not node_port:
        raise ValueError(f"Metrics service {service_name} does not have a NodePort configured")

    # Get worker node IPs
    worker_ips = k8s.list_worker_node_ips()
    if not worker_ips:
        raise ValueError("No worker nodes found in the cluster")

    # Build targets (use first worker IP)
    targets = [f"{worker_ips[0]}:{node_port}"]

    # Build job name and labels
    job_name = f"mongo-{deployment_id}"
    labels = {"app": job_name}

    return {
        "jobName": job_name,
        "metricsPath": "/metrics",
        "username": username,
        "password": password,
        "targets": targets,
        "labels": labels,
        "workerNodeIps": worker_ips,
        "nodePort": node_port,
        "isFirstView": is_first_view
    }
