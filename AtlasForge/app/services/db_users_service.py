import secrets
import string
from datetime import datetime, timezone
from typing import Dict, Any, List
from kubernetes import client

from app.services.mongo_repo import MongoRepository
from app.services.k8s_client import K8sClient
from app.services.lifecycle_service import get_connection_info


def get_repo() -> MongoRepository:
    return MongoRepository()


def get_k8s_client() -> K8sClient:
    return K8sClient()


def generate_password(length: int = 24) -> str:
    """Generate a strong random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_db_user(
    tenant_id: str,
    deployment_id: str,
    username: str,
    db: str,
    role_preset: str
) -> Dict[str, Any]:
    """
    Create a MongoDB database user.
    
    Creates:
    - Secret with password
    - MongoDBUser CR
    - Metadata in control plane DB
    
    Returns user info with connection URI.
    """
    repo = get_repo()
    k8s = get_k8s_client()

    # Validate inputs
    if not username or not db or not role_preset:
        raise ValueError("username, db, and rolePreset are required")

    if role_preset not in ["readWrite", "read", "dbAdmin"]:
        raise ValueError("rolePreset must be one of: readWrite, read, dbAdmin")

    # Get tenant and deployment
    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    deployment = repo.get_deployment(tenant_id, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment {deployment_id} not found")

    namespace = tenant["namespace"]
    plan = tenant.get("plan", "enterprise")

    # Check if user already exists
    existing_user = repo.get_db_user(tenant_id, deployment_id, username)
    if existing_user:
        raise ValueError(f"User {username} already exists for deployment {deployment_id}")

    # Generate password
    password = generate_password()

    # Create Secret
    secret_name = f"mdb-user-{deployment_id}-{username}"
    secret = client.V1Secret(
        api_version="v1",
        kind="Secret",
        metadata=client.V1ObjectMeta(
            name=secret_name,
            namespace=namespace
        ),
        type="Opaque",
        string_data={
            "password": password
        }
    )

    try:
        k8s.core_v1.create_namespaced_secret(namespace, secret)
        print(f"[DB_USER] Created secret: {secret_name}")
    except client.exceptions.ApiException as e:
        if e.status == 409:
            raise ValueError(f"Secret {secret_name} already exists")
        raise

    # Create MongoDBUser CR
    mongodb_user_name = f"{deployment_id}-{username}"
    
    mongodb_user_cr = {
        "apiVersion": "mongodb.com/v1",
        "kind": "MongoDBUser",
        "metadata": {
            "name": mongodb_user_name,
            "namespace": namespace
        },
        "spec": {
            "db": db,
            "username": username,
            "passwordSecretKeyRef": {
                "name": secret_name,
                "key": "password"
            },
            "roles": [
                {
                    "name": role_preset,
                    "db": db
                }
            ],
            "mongodbResourceRef": {
                "name": deployment_id
            }
        }
    }

    try:
        k8s.custom_objects.create_namespaced_custom_object(
            group="mongodb.com",
            version="v1",
            namespace=namespace,
            plural="mongodbusers",
            body=mongodb_user_cr
        )
        print(f"[DB_USER] Created MongoDBUser CR: {mongodb_user_name}")
    except client.exceptions.ApiException as e:
        # Rollback: delete the secret
        k8s.core_v1.delete_namespaced_secret(secret_name, namespace)
        if e.status == 409:
            raise ValueError(f"MongoDBUser {mongodb_user_name} already exists")
        raise

    # Store metadata
    created_at = datetime.now(timezone.utc).isoformat()
    user_doc = {
        "_id": f"{tenant_id}:{deployment_id}:{username}",
        "tenantId": tenant_id,
        "deploymentId": deployment_id,
        "username": username,
        "db": db,
        "roles": [{"db": db, "role": role_preset}],
        "secretName": secret_name,
        "createdAt": created_at
    }

    repo.insert_db_user(user_doc)
    print(f"[DB_USER] Stored metadata for user: {username}")

    # Get connection info
    conn_info = get_connection_info(tenant_id, deployment_id)
    replica_set = conn_info.get("replicaSet", deployment_id)
    external_host_port = conn_info.get("externalHostPort")

    # Build connection URI
    connection_uri = None
    if external_host_port:
        connection_uri = f"mongodb://{username}:{password}@{external_host_port}/{db}?replicaSet={replica_set}"

    return {
        "username": username,
        "db": db,
        "roles": [{"db": db, "role": role_preset}],
        "createdAt": created_at,
        "connectionUri": connection_uri
    }


def list_db_users(tenant_id: str, deployment_id: str) -> List[Dict[str, Any]]:
    """
    List all DB users for a deployment.
    
    Returns metadata only (no passwords).
    """
    repo = get_repo()

    # Verify tenant and deployment exist
    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    deployment = repo.get_deployment(tenant_id, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment {deployment_id} not found")

    users = repo.list_db_users(tenant_id, deployment_id)

    # Return clean list without _id
    result = []
    for user in users:
        result.append({
            "username": user["username"],
            "db": user["db"],
            "roles": user["roles"],
            "createdAt": user["createdAt"]
        })

    return result


def get_user_connection(
    tenant_id: str,
    deployment_id: str,
    username: str
) -> Dict[str, Any]:
    """
    Get connection URIs for a specific DB user.
    
    Returns external and internal URIs with credentials.
    """
    repo = get_repo()
    k8s = get_k8s_client()

    # Get user metadata
    user = repo.get_db_user(tenant_id, deployment_id, username)
    if not user:
        raise ValueError(f"User {username} not found for deployment {deployment_id}")

    # Get tenant info
    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    namespace = tenant["namespace"]
    secret_name = user["secretName"]

    # Read password from Secret
    try:
        secret = k8s.core_v1.read_namespaced_secret(secret_name, namespace)
        password = secret.data["password"]
        # Decode base64
        import base64
        password = base64.b64decode(password).decode("utf-8")
    except client.exceptions.ApiException as e:
        if e.status == 404:
            raise ValueError(f"Secret {secret_name} not found")
        raise

    # Get connection info
    conn_info = get_connection_info(tenant_id, deployment_id)
    replica_set = conn_info.get("replicaSet", deployment_id)
    external_host_port = conn_info.get("externalHostPort")
    internal_uri_base = conn_info.get("internalUri", "")
    
    # Extract internal host from base URI
    # mongodb://host:port -> host:port
    internal_host = internal_uri_base.replace("mongodb://", "").split("?")[0] if internal_uri_base else None

    db = user["db"]

    # Build URIs with credentials
    external_uri = None
    if external_host_port:
        external_uri = f"mongodb://{username}:{password}@{external_host_port}/{db}?replicaSet={replica_set}"

    internal_uri = None
    if internal_host:
        internal_uri = f"mongodb://{username}:{password}@{internal_host}/{db}?replicaSet={replica_set}"

    return {
        "username": username,
        "db": db,
        "roles": user["roles"],
        "externalUri": external_uri,
        "internalUri": internal_uri
    }
