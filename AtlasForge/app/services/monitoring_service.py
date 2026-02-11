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


def generate_strong_password(length: int = 20) -> str:
    """
    Generate a strong random password.
    """
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def get_prometheus_scrape_config(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Get Prometheus scrape configuration with MASKED password.
    
    Returns:
    - jobName, metricsPath, username, passwordMasked
    - targets, labels, workerNodeIps, nodePort
    - canRevealPassword: true if firstViewedAt is null
    
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

    # Read password from secret and ALWAYS mask it
    password_raw = k8s.get_secret_data(namespace, secret_name, secret_key)
    if not password_raw:
        raise ValueError(f"Password secret {secret_name} not found or empty in namespace {namespace}")

    password_masked = mask_password(password_raw)

    # Check if can reveal password
    prometheus_meta = deployment.get("prometheus", {})
    first_viewed_at = prometheus_meta.get("firstViewedAt")
    can_reveal_password = (first_viewed_at is None)

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
        "passwordMasked": password_masked,
        "targets": targets,
        "labels": labels,
        "workerNodeIps": worker_ips,
        "nodePort": node_port,
        "canRevealPassword": can_reveal_password
    }


def reveal_prometheus_password(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Reveal the full Prometheus password ONCE.
    
    Only works if firstViewedAt is null.
    After revealing, sets firstViewedAt to now.
    
    Returns: { username, password } with FULL password.
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

    # Check if already revealed
    prometheus_meta = deployment.get("prometheus", {})
    first_viewed_at = prometheus_meta.get("firstViewedAt")
    
    if first_viewed_at is not None:
        raise ValueError("Password already revealed. Rotate to generate a new one.")

    namespace = tenant["namespace"]
    plan = tenant.get("plan", "enterprise")

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

    # Read full password from secret
    password = k8s.get_secret_data(namespace, secret_name, secret_key)
    if not password:
        raise ValueError(f"Password secret {secret_name} not found or empty in namespace {namespace}")

    # Mark as revealed
    repo.update_deployment(tenant_id, deployment_id, {
        "prometheus.firstViewedAt": datetime.now(timezone.utc).isoformat()
    })

    return {
        "username": username,
        "password": password
    }


def rotate_prometheus_password(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Rotate Prometheus password.
    
    Generates a new random password, updates mongodb-admin-secret in K8s,
    resets firstViewedAt to null, and optionally increments passwordVersion.
    
    Returns success message.
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

    # Get CR to read prometheus config
    if plan == "community":
        cr = k8s.get_mongodb_community_cr(namespace, deployment_id)
    else:
        cr = k8s.get_mongodb_enterprise_cr(namespace, deployment_id)
    
    if not cr:
        raise ValueError(f"MongoDB CR {deployment_id} not found in namespace {namespace}")

    prometheus_spec = cr.get("spec", {}).get("prometheus", {})
    password_secret_ref = prometheus_spec.get("passwordSecretRef", {})
    secret_name = password_secret_ref.get("name", "mongodb-admin-secret")
    secret_key = password_secret_ref.get("key", "password")

    # Generate new password
    new_password = generate_strong_password()

    # Update secret in K8s
    k8s.update_secret_data(namespace, secret_name, secret_key, new_password)

    # Reset firstViewedAt and increment version
    prometheus_meta = deployment.get("prometheus", {})
    password_version = prometheus_meta.get("passwordVersion", 0)
    
    repo.update_deployment(tenant_id, deployment_id, {
        "prometheus.firstViewedAt": None,
        "prometheus.passwordVersion": password_version + 1,
        "prometheus.lastRotatedAt": datetime.now(timezone.utc).isoformat()
    })

    return {
        "message": "Password rotated successfully. You can now reveal the new password once.",
        "passwordVersion": password_version + 1
    }
