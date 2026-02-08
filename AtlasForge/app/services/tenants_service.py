import re
import secrets
import string
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app import config
from app.services.mongo_repo import get_repo
from app.services.k8s_client import get_k8s_client


def validate_dns_safe(value: str, max_length: int = 63) -> bool:
    pattern = re.compile(r'^[a-z0-9-]+$')
    return bool(pattern.match(value)) and len(value) <= max_length


def generate_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def list_tenants() -> List[Dict[str, Any]]:
    """List all tenants"""
    repo = get_repo()
    tenants = repo.list_tenants()
    
    # Remove MongoDB _id field and sanitize for API response
    result = []
    for tenant in tenants:
        if '_id' in tenant:
            tenant.pop('_id')
        result.append(tenant)
    
    return result


def get_tenant(tenant_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific tenant by ID"""
    repo = get_repo()
    tenant = repo.get_tenant(tenant_id)
    
    if tenant and '_id' in tenant:
        tenant.pop('_id')
    
    return tenant


def onboard_tenant(tenant_id: str, display_name: str) -> Dict[str, Any]:
    if not validate_dns_safe(tenant_id):
        raise ValueError(f"tenantId '{tenant_id}' is not DNS-safe (must be [a-z0-9-], max 63 chars)")

    repo = get_repo()
    k8s = get_k8s_client()

    if repo.get_tenant(tenant_id):
        raise ValueError(f"Tenant {tenant_id} already exists")

    namespace = f"{config.MCP_NAMESPACE_PREFIX}{tenant_id}"
    project_name = f"mdb-{tenant_id}-project"

    k8s.ensure_namespace(
        name=namespace,
        labels={"mdb.example.com/tenantId": tenant_id}
    )

    k8s.ensure_configmap(
        namespace=namespace,
        name=f"om-{tenant_id}-project",
        data={
            "baseUrl": config.MCP_OPS_MANAGER_URL,
            "projectName": project_name,
            "orgId": config.MCP_OPS_MANAGER_ORG
        }
    )

    k8s.ensure_secret(
        namespace=namespace,
        name=f"om-{tenant_id}-credentials",
        string_data={
            "user": config.MCP_OM_GLOBAL_PUBLIC_KEY,
            "publicApiKey": config.MCP_OM_GLOBAL_PRIVATE_KEY
        }
    )

    admin_password = generate_password()
    k8s.ensure_secret(
        namespace=namespace,
        name="mongodb-admin-secret",
        string_data={"password": admin_password}
    )

    # MCK expects this ServiceAccount for MongoDB StatefulSet pods.
    # Without it, pods fail with 'serviceaccount ... not found' and deployments never become Ready.
    k8s.ensure_service_account(
        namespace=namespace,
        name="mongodb-kubernetes-database-pods"
    )

    tenant_doc = {
        "_id": tenant_id,
        "tenantId": tenant_id,
        "namespace": namespace,
        "displayName": display_name,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": "Active",
        "opsManager": {
            "projectName": project_name
        }
    }

    repo.insert_tenant(tenant_doc)

    return {
        "tenantId": tenant_id,
        "namespace": namespace,
        "projectName": project_name,
        "status": "Active"
    }


def delete_tenant(tenant_id: str) -> bool:
    """
    Delete a tenant by:
    1. Deleting all MongoDB CRs in the tenant namespace
    2. Deleting the namespace
    3. Deleting all deployment documents from control-plane DB
    4. Deleting the tenant document from control-plane DB
    Returns True if something was deleted, False if nothing existed.
    """
    repo = get_repo()
    k8s = get_k8s_client()

    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        return False

    namespace = tenant["namespace"]

    mongo_crs = k8s.list_mongodb_crs(namespace)
    for cr in mongo_crs:
        cr_name = cr.get("metadata", {}).get("name")
        if cr_name:
            k8s.delete_mongodb_cr(namespace, cr_name)

    k8s.delete_namespace(namespace)

    repo.delete_all_tenant_deployments(tenant_id)
    repo.delete_tenant(tenant_id)

    return True
