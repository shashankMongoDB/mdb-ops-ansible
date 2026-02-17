import re
import secrets
import string
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from kubernetes import client as k8s_client
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


def onboard_tenant(tenant_id: str, display_name: str, plan: str = "enterprise") -> Dict[str, Any]:
    if not validate_dns_safe(tenant_id):
        raise ValueError(f"tenantId '{tenant_id}' is not DNS-safe (must be [a-z0-9-], max 63 chars)")

    if plan not in ["enterprise", "community"]:
        raise ValueError(f"Invalid plan: {plan}. Must be 'enterprise' or 'community'")

    repo = get_repo()
    k8s = get_k8s_client()

    if repo.get_tenant(tenant_id):
        raise ValueError(f"Tenant {tenant_id} already exists")

    namespace = f"{config.MCP_NAMESPACE_PREFIX}{tenant_id}"
    project_name = None

    k8s.ensure_namespace(
        name=namespace,
        labels={
            "mdb.example.com/tenantId": tenant_id,
            "mdb.example.com/plan": plan
        }
    )

    # Only create Ops Manager resources for enterprise plan
    if plan == "enterprise":
        project_name = f"mdb-{tenant_id}-project"
        
        # Create ConfigMap with project name - OM project will be created by operator
        # sslMMSCAConfigMap tells the operator which configmap contains the CA for OM TLS
        k8s.ensure_configmap(
            namespace=namespace,
            name=f"om-{tenant_id}-project",
            data={
                "baseUrl": config.MCP_OPS_MANAGER_URL,
                "projectName": project_name,
                "orgId": config.MCP_OPS_MANAGER_ORG,
                "sslMMSCAConfigMap": "om-ca-combined"
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
        
        # Combined CA configmap: OM CA + system root CAs
        # Required so the MCK automation agent can trust both the Ops Manager TLS cert
        # and public HTTPS endpoints (e.g. fastdl.mongodb.org for binary downloads)
        k8s.create_combined_ca_configmap(
            target_namespace=namespace,
            source_namespace=config.MCP_OPERATOR_NAMESPACE,
            source_configmap="om-ca",
            target_configmap="om-ca-combined"
        )

        # ServiceAccount for MongoDB pods (enterprise)
        k8s.ensure_service_account(
            namespace=namespace,
            name="mongodb-enterprise-database-pods"
        )
    else:
        # Community plan: Create ServiceAccount, Role, and RoleBinding for operator
        # ServiceAccount name must match what the community operator expects
        k8s.ensure_service_account(
            namespace=namespace,
            name="mongodb-database"
        )

        # Role with permissions for secrets, configmaps, and pods
        rules = [
            k8s_client.V1PolicyRule(
                api_groups=[""],
                resources=["secrets", "configmaps"],
                verbs=["get", "list", "watch"]
            ),
            k8s_client.V1PolicyRule(
                api_groups=[""],
                resources=["pods"],
                verbs=["get", "list", "watch", "update", "patch"]
            )
        ]

        k8s.ensure_role(
            namespace=namespace,
            name="mongodb-database-role",
            rules=rules
        )

        # RoleBinding to bind ServiceAccount to Role
        k8s.ensure_role_binding(
            namespace=namespace,
            name="mongodb-database-rolebinding",
            role_name="mongodb-database-role",
            service_account_name="mongodb-database"
        )

    # Admin password secret for both plans
    admin_password = generate_password()
    k8s.ensure_secret(
        namespace=namespace,
        name="mongodb-admin-secret",
        string_data={"password": admin_password}
    )

    tenant_doc = {
        "_id": tenant_id,
        "tenantId": tenant_id,
        "namespace": namespace,
        "displayName": display_name,
        "plan": plan,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": "Active"
    }

    if plan == "enterprise":
        tenant_doc["opsManager"] = {
            "projectName": project_name,
            "orgId": config.MCP_OPS_MANAGER_ORG
            # projectId will be discovered lazily by backup_service when needed
        }

    repo.insert_tenant(tenant_doc)

    return {
        "tenantId": tenant_id,
        "namespace": namespace,
        "projectName": project_name,
        "status": "Active",
        "plan": plan
    }


def delete_tenant(tenant_id: str) -> bool:
    """
    Delete a tenant by:
    1. Deleting all MongoDB CRs in the tenant namespace (enterprise or community)
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
    plan = tenant.get("plan", "enterprise")  # Default to enterprise for existing tenants

    # Delete CRs based on plan
    if plan == "enterprise":
        mongo_crs = k8s.list_mongodb_enterprise_crs(namespace)
        for cr in mongo_crs:
            cr_name = cr.get("metadata", {}).get("name")
            if cr_name:
                k8s.delete_mongodb_enterprise_cr(namespace, cr_name)
    else:  # community
        mongo_crs = k8s.list_mongodb_community_crs(namespace)
        for cr in mongo_crs:
            cr_name = cr.get("metadata", {}).get("name")
            if cr_name:
                k8s.delete_mongodb_community_cr(namespace, cr_name)

    k8s.delete_namespace(namespace)

    repo.delete_all_tenant_deployments(tenant_id)
    repo.delete_tenant(tenant_id)

    return True
