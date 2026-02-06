import copy
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.services.mongo_repo import get_repo
from app.services.k8s_client import get_k8s_client
from app.services.tenants_service import validate_dns_safe


BASE_RS_CR = {
    "apiVersion": "mongodb.com/v1",
    "kind": "MongoDB",
    "metadata": {
        "name": "",
        "namespace": "",
        "labels": {}
    },
    "spec": {
        "type": "ReplicaSet",
        "members": 3,
        "version": "",
        "opsManager": {
            "configMapRef": {"name": ""}
        },
        "credentials": "",
        "security": {
            "authentication": {
                "enabled": True,
                "modes": ["SCRAM"]
            }
        },
        "users": []
    }
}


def create_replicaset_deployment(
    tenant_id: str,
    deployment_id: str,
    mongo_version: str,
    members: int,
    display_name: str,
    environment: str,
    created_by: str = "system"
) -> Dict[str, Any]:
    if not validate_dns_safe(deployment_id):
        raise ValueError(f"deploymentId '{deployment_id}' is not DNS-safe (must be [a-z0-9-], max 63 chars)")

    repo = get_repo()
    k8s = get_k8s_client()

    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    if repo.get_deployment(tenant_id, deployment_id):
        raise ValueError(f"Deployment {deployment_id} already exists for tenant {tenant_id}")

    namespace = tenant["namespace"]

    existing_cr = k8s.get_mongodb_cr(namespace, deployment_id)
    if existing_cr:
        raise ValueError(f"MongoDB CR {deployment_id} already exists in namespace {namespace}")

    cr_body = copy.deepcopy(BASE_RS_CR)
    cr_body["metadata"]["name"] = deployment_id
    cr_body["metadata"]["namespace"] = namespace
    cr_body["metadata"]["labels"]["mdb.example.com/tenantId"] = tenant_id
    cr_body["spec"]["version"] = mongo_version
    cr_body["spec"]["members"] = members
    cr_body["spec"]["opsManager"]["configMapRef"]["name"] = f"om-{tenant_id}-project"
    cr_body["spec"]["credentials"] = f"om-{tenant_id}-credentials"
    cr_body["spec"]["users"] = [
        {
            "name": "dbAdmin",
            "db": "admin",
            "passwordSecretRef": {"name": "mongodb-admin-secret"},
            "roles": [{"name": "root", "db": "admin"}],
            "scramCredentialsSecretName": f"{deployment_id}-admin-scram"
        }
    ]

    k8s.create_mongodb_cr(namespace, cr_body)

    deployment_doc = {
        "_id": f"{tenant_id}:{deployment_id}",
        "tenantId": tenant_id,
        "deploymentId": deployment_id,
        "namespace": namespace,
        "k8sName": deployment_id,
        "type": "ReplicaSet",
        "displayName": display_name,
        "environment": environment,
        "plan": "gold",
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

    repo.insert_deployment(deployment_doc)

    return {
        "tenantId": tenant_id,
        "deploymentId": deployment_id,
        "mongoVersion": mongo_version,
        "members": members,
        "state": "Creating"
    }


def get_deployment_details(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    repo = get_repo()
    k8s = get_k8s_client()

    deployment = repo.get_deployment(tenant_id, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment {deployment_id} not found for tenant {tenant_id}")

    result = {
        "tenantId": deployment["tenantId"],
        "deploymentId": deployment["deploymentId"],
        "displayName": deployment["displayName"],
        "environment": deployment["environment"],
        "mongoVersion": deployment["lastRequestedSpec"]["mongoVersion"],
        "members": deployment["lastRequestedSpec"]["members"],
        "createdAt": deployment["createdAt"],
        "state": deployment["lastKnownStatus"].get("phase", "Unknown")
    }

    cr = k8s.get_mongodb_cr(deployment["namespace"], deployment_id)
    if cr and "status" in cr:
        result["k8sPhase"] = cr["status"].get("phase", "Unknown")

    return result


def list_tenant_deployments(tenant_id: str) -> list[Dict[str, Any]]:
    repo = get_repo()

    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    deployments = repo.list_deployments(tenant_id)

    return [
        {
            "tenantId": d["tenantId"],
            "deploymentId": d["deploymentId"],
            "displayName": d["displayName"],
            "environment": d["environment"],
            "mongoVersion": d["lastRequestedSpec"]["mongoVersion"],
            "members": d["lastRequestedSpec"]["members"],
            "state": d["lastKnownStatus"].get("phase", "Unknown"),
            "createdAt": d["createdAt"]
        }
        for d in deployments
    ]


def delete_deployment(tenant_id: str, deployment_id: str) -> bool:
    """
    Delete a deployment by removing the MongoDB CR from Kubernetes
    and the deployment document from control-plane DB.
    Returns True if something was deleted, False if nothing existed.
    """
    repo = get_repo()
    k8s = get_k8s_client()

    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    namespace = tenant["namespace"]

    k8s_deleted = k8s.delete_mongodb_cr(namespace, deployment_id)
    db_deleted = repo.delete_deployment(tenant_id, deployment_id)

    return k8s_deleted or db_deleted
