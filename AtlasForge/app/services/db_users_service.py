import secrets
import string
import json
from datetime import datetime, timezone
from typing import Dict, Any, List
from urllib.parse import quote_plus
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


def _get_admin_password(k8s: K8sClient, namespace: str, deployment_id: str) -> str:
    admin_secret_names = [f"{deployment_id}-admin-admin", f"{deployment_id}-admin"]
    for secret_name in admin_secret_names:
        try:
            secret = k8s.core_v1.read_namespaced_secret(secret_name, namespace)
            encoded = (secret.data or {}).get("password")
            if not encoded:
                continue
            import base64
            return base64.b64decode(encoded).decode("utf-8")
        except client.exceptions.ApiException as e:
            if e.status != 404:
                raise
            continue
    raise ValueError(f"Could not find admin credentials secret. Tried: {', '.join(admin_secret_names)}")


def _get_primary_pod_name(k8s: K8sClient, namespace: str, deployment_id: str) -> str:
    pods = k8s.core_v1.list_namespaced_pod(
        namespace=namespace,
        label_selector=f"app={deployment_id}-svc"
    )
    if not pods.items:
        raise ValueError(f"No pods found for deployment {deployment_id}")

    pod_names = [p.metadata.name for p in pods.items if p.metadata and p.metadata.name]
    for pod_name in pod_names:
        try:
            resp = k8s.exec_in_pod(
                pod_name=pod_name,
                namespace=namespace,
                container='mongod',
                command=['/bin/bash', '-c', "mongosh --quiet --eval 'JSON.stringify(db.hello())'"],
            )
            payload = None
            for line in str(resp).splitlines()[::-1]:
                line = line.strip()
                if line.startswith('{') and line.endswith('}'):
                    payload = line
                    break
            if not payload:
                continue
            hello = json.loads(payload)
            if hello.get("isWritablePrimary"):
                return pod_name
        except Exception:
            continue

    # Fallback if we couldn't resolve role yet
    return pod_names[0]


def _get_secondary_pod_name(k8s: K8sClient, namespace: str, deployment_id: str, primary_pod: str) -> str | None:
    pods = k8s.core_v1.list_namespaced_pod(
        namespace=namespace,
        label_selector=f"app={deployment_id}-svc"
    )
    pod_names = [p.metadata.name for p in pods.items if p.metadata and p.metadata.name]
    for pod_name in sorted(pod_names, reverse=True):
        if pod_name != primary_pod:
            return pod_name
    return None


def create_db_user(
    tenant_id: str,
    deployment_id: str,
    username: str,
    db: str,
    roles: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Create a MongoDB database user.
    
    Creates:
    - Secret with password
    - MongoDBUser CR
    - Metadata in control plane DB
    
    Returns user info with connection URI.
    
    Args:
        tenant_id: Tenant identifier
        deployment_id: Deployment identifier
        username: Database username
        db: Default database name
        roles: List of roles, each with 'db' and 'name' keys
            e.g., [{"db": "appdb", "name": "readWrite"}, {"db": "admin", "name": "clusterMonitor"}]
    """
    repo = get_repo()
    k8s = get_k8s_client()

    # Validate inputs
    if not username or not db or not roles:
        raise ValueError("username, db, and roles are required")
    
    if not isinstance(roles, list) or len(roles) == 0:
        raise ValueError("roles must be a non-empty array")
    
    # Validate each role
    for role in roles:
        if not isinstance(role, dict) or 'db' not in role or 'name' not in role:
            raise ValueError("Each role must have 'db' and 'name' keys")

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

    # Create MongoDB user (different approach for Community vs Enterprise)
    mongodb_user_name = f"{deployment_id}-{username}"
    
    if plan == "community":
        # For Community: Create user directly via mongosh exec
        print(f"[DB_USER] Creating Community MongoDB user via mongosh...")
        
        try:
            pod_name = _get_primary_pod_name(k8s, namespace, deployment_id)
            admin_password = _get_admin_password(k8s, namespace, deployment_id)
            print(f"[DB_USER] Using primary pod for user creation: {pod_name}")

            # Build roles for MongoDB
            roles_list = [{"role": role["name"], "db": role["db"]} for role in roles]
            roles_json = json.dumps(roles_list)
            
            # Create user command using here-doc to avoid escaping issues
            # Connect as admin to create the user
            create_user_script = f"""mongosh --quiet -u admin -p '{admin_password}' --authenticationDatabase admin <<'MONGOEOF'
db = db.getSiblingDB('{db}');
try {{
    db.createUser({{
        user: '{username}',
        pwd: '{password}',
        roles: {roles_json}
    }});
    print('USER_CREATED');
}} catch(e) {{
    if (e.code === 51003) {{
        print('USER_ALREADY_EXISTS');
    }} else {{
        print('ERROR: ' + e.message);
        throw e;
    }}
}}
MONGOEOF
"""
            
            command = ['/bin/bash', '-c', create_user_script]
            
            resp = k8s.exec_in_pod(
                pod_name=pod_name,
                namespace=namespace,
                container='mongod',
                command=command,
            )
            
            print(f"[DB_USER] MongoDB user creation response: {resp}")
            
            if 'USER_CREATED' not in resp:
                # Rollback
                k8s.core_v1.delete_namespaced_secret(secret_name, namespace)
                raise ValueError(f"Failed to create MongoDB user. Output: {resp}")
                
            print(f"[DB_USER] Successfully created user in MongoDB: {username}")
            
        except Exception as e:
            # Rollback: delete the secret
            try:
                k8s.core_v1.delete_namespaced_secret(secret_name, namespace)
            except:
                pass
            raise ValueError(f"Failed to create Community MongoDB user: {str(e)}")
    
    else:
        # For Enterprise: Use MongoDBUser CR
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
                        "name": role["name"],
                        "db": role["db"]
                    }
                    for role in roles
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
        "roles": roles,
        "secretName": secret_name,
        "createdAt": created_at
    }

    repo.insert_db_user(user_doc)
    print(f"[DB_USER] Stored metadata for user: {username}")

    # Get connection info
    conn_info = get_connection_info(tenant_id, deployment_id)
    external_host_port = conn_info.get("externalHostPort")

    # Build connection URI with URL-encoded password (handles special characters)
    connection_uri = None
    if external_host_port:
        encoded_password = quote_plus(password)
        connection_uri = f"mongodb://{username}:{encoded_password}@{external_host_port}/{db}"

    return {
        "username": username,
        "db": db,
        "roles": roles,
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

    # Get tenant plan to determine auth strategy
    plan = tenant.get("plan", "enterprise")
    
    # Get connection info
    conn_info = get_connection_info(tenant_id, deployment_id)
    external_host_port = conn_info.get("externalHostPort")
    external_primary_host_port = conn_info.get("externalPrimaryHostPort")
    external_secondary_host_port = conn_info.get("externalSecondaryHostPort")
    internal_uri_base = conn_info.get("internalUri", "")

    # Hard fallback: ensure generic external endpoint even if connection info response missed it.
    if not external_host_port:
        try:
            _, node_port = k8s.ensure_external_service(namespace, deployment_id)
            worker_node_ip = k8s.get_worker_node_ip()
            external_host_port = f"{worker_node_ip}:{node_port}"
        except Exception:
            external_host_port = None

    # Hard fallback for role-specific endpoints (match overview behavior)
    if plan == "community" and (not external_primary_host_port or not external_secondary_host_port):
        try:
            worker_node_ip = k8s.get_worker_node_ip()
            primary_pod = _get_primary_pod_name(k8s, namespace, deployment_id)

            if not external_primary_host_port and primary_pod:
                _, primary_node_port = k8s.ensure_external_service_for_pod(namespace, deployment_id, primary_pod, "primary")
                external_primary_host_port = f"{worker_node_ip}:{primary_node_port}"

            if not external_secondary_host_port:
                secondary_pod = _get_secondary_pod_name(k8s, namespace, deployment_id, primary_pod)
                if secondary_pod:
                    _, secondary_node_port = k8s.ensure_external_service_for_pod(namespace, deployment_id, secondary_pod, "secondary")
                    external_secondary_host_port = f"{worker_node_ip}:{secondary_node_port}"
        except Exception:
            pass
    
    # Extract internal host from base URI
    # mongodb://host:port -> host:port
    internal_host = internal_uri_base.replace("mongodb://", "").split("?")[0] if internal_uri_base else None

    db = user["db"]

    # URL-encode password to handle special characters
    encoded_password = quote_plus(password)

    # Build URIs with credentials and encoded password
    # For Community: users are created via direct commands, so we need authSource parameter
    # For Enterprise: MongoDBUser CR handles authentication, no authSource needed
    external_uri = None
    if external_host_port:
        if plan == "community":
            # Community MongoDB needs authSource parameter
            # Users are created in their database but authenticated against admin
            external_uri = f"mongodb://{username}:{encoded_password}@{external_host_port}/{db}?authSource={db}"
        else:
            # Enterprise MongoDB
            external_uri = f"mongodb://{username}:{encoded_password}@{external_host_port}/{db}"

    internal_uri = None
    if internal_host:
        if plan == "community":
            # Community MongoDB needs authSource parameter
            internal_uri = f"mongodb://{username}:{encoded_password}@{internal_host}/{db}?authSource={db}"
        else:
            # Enterprise MongoDB
            internal_uri = f"mongodb://{username}:{encoded_password}@{internal_host}/{db}"

    external_primary_uri = None
    if external_primary_host_port:
        if plan == "community":
            external_primary_uri = f"mongodb://{username}:{encoded_password}@{external_primary_host_port}/{db}?authSource={db}"
        else:
            external_primary_uri = f"mongodb://{username}:{encoded_password}@{external_primary_host_port}/{db}"

    external_secondary_uri = None
    if external_secondary_host_port:
        if plan == "community":
            external_secondary_uri = f"mongodb://{username}:{encoded_password}@{external_secondary_host_port}/{db}?authSource={db}"
        else:
            external_secondary_uri = f"mongodb://{username}:{encoded_password}@{external_secondary_host_port}/{db}"

    return {
        "username": username,
        "db": db,
        "roles": user["roles"],
        "externalHostPort": external_host_port,
        "externalUri": external_uri,
        "externalPrimaryHostPort": external_primary_host_port,
        "internalUri": internal_uri,
        "externalPrimaryUri": external_primary_uri,
        "externalSecondaryHostPort": external_secondary_host_port,
        "externalSecondaryUri": external_secondary_uri
    }


def update_user_roles(
    tenant_id: str,
    deployment_id: str,
    username: str,
    roles: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Update roles for an existing DB user.
    
    Updates:
    - MongoDBUser CR spec.roles
    - User metadata in control plane DB
    
    Args:
        tenant_id: Tenant identifier
        deployment_id: Deployment identifier
        username: Database username
        roles: New roles array with 'db' and 'name' keys
    """
    repo = get_repo()
    k8s = get_k8s_client()

    # Validate inputs
    if not roles or not isinstance(roles, list):
        raise ValueError("roles must be a non-empty array")
    
    for role in roles:
        if not isinstance(role, dict) or 'db' not in role or 'name' not in role:
            raise ValueError("Each role must have 'db' and 'name' keys")

    # Get existing user
    user = repo.get_db_user(tenant_id, deployment_id, username)
    if not user:
        raise ValueError(f"User {username} not found for deployment {deployment_id}")

    # Get tenant info
    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    namespace = tenant["namespace"]
    mongodb_user_name = f"{deployment_id}-{username}"
    plan = tenant.get("plan", "enterprise")

    if plan == "community":
        try:
            pod_name = _get_primary_pod_name(k8s, namespace, deployment_id)
            admin_password = _get_admin_password(k8s, namespace, deployment_id)
            user_db = user.get("db", "admin")
            roles_json = json.dumps([{"role": role["name"], "db": role["db"]} for role in roles])

            update_user_script = f"""mongosh --quiet -u admin -p '{admin_password}' --authenticationDatabase admin <<'MONGOEOF'
db = db.getSiblingDB('{user_db}');
try {{
    db.updateUser('{username}', {{ roles: {roles_json} }});
    print('USER_UPDATED');
}} catch(e) {{
    print('ERROR: ' + e.message);
    throw e;
}}
MONGOEOF
"""
            resp = k8s.exec_in_pod(
                pod_name=pod_name,
                namespace=namespace,
                container='mongod',
                command=['/bin/bash', '-c', update_user_script],
            )
            print(f"[DB_USER] Community update user response: {resp}")
            if 'USER_UPDATED' not in str(resp):
                raise ValueError(f"Failed to update Community MongoDB user roles. Output: {resp}")
        except Exception as e:
            raise ValueError(f"Failed to update Community MongoDB user roles: {str(e)}")
    else:

        # Update MongoDBUser CR
        try:
            # Get existing CR
            existing_cr = k8s.custom_objects.get_namespaced_custom_object(
                group="mongodb.com",
                version="v1",
                namespace=namespace,
                plural="mongodbusers",
                name=mongodb_user_name
            )

            # Update roles in spec
            existing_cr["spec"]["roles"] = [
                {"name": role["name"], "db": role["db"]}
                for role in roles
            ]

            # Patch the CR
            k8s.custom_objects.patch_namespaced_custom_object(
                group="mongodb.com",
                version="v1",
                namespace=namespace,
                plural="mongodbusers",
                name=mongodb_user_name,
                body=existing_cr
            )
            print(f"[DB_USER] Updated MongoDBUser CR roles: {mongodb_user_name}")

        except client.exceptions.ApiException as e:
            if e.status == 404:
                raise ValueError(f"MongoDBUser CR {mongodb_user_name} not found")
            raise

    # Update metadata
    updated_at = datetime.now(timezone.utc).isoformat()
    
    from app.services.mongo_repo import MongoRepository
    repo_instance = MongoRepository()
    repo_instance.db_users.update_one(
        {"_id": f"{tenant_id}:{deployment_id}:{username}"},
        {
            "$set": {
                "roles": roles,
                "updatedAt": updated_at
            }
        }
    )
    print(f"[DB_USER] Updated metadata for user: {username}")

    return {
        "username": username,
        "db": user["db"],
        "roles": roles,
        "createdAt": user.get("createdAt"),
        "updatedAt": updated_at
    }


def delete_user(
    tenant_id: str,
    deployment_id: str,
    username: str
) -> Dict[str, Any]:
    """
    Delete a DB user.
    
    Deletes:
    - MongoDBUser CR
    - Secret with password
    - User metadata from control plane DB
    
    Returns:
        Success confirmation
    """
    repo = get_repo()
    k8s = get_k8s_client()

    # Get existing user to get secret name
    user = repo.get_db_user(tenant_id, deployment_id, username)
    if not user:
        raise ValueError(f"User {username} not found for deployment {deployment_id}")

    # Get tenant info
    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    namespace = tenant["namespace"]
    plan = tenant.get("plan", "enterprise")
    mongodb_user_name = f"{deployment_id}-{username}"
    secret_name = user["secretName"]
    user_db = user.get("db", "admin")

    # Delete MongoDB user (different approach for Community vs Enterprise)
    if plan == "community":
        # For Community: Drop user directly via mongosh exec
        print(f"[DB_USER] Deleting Community MongoDB user via mongosh...")
        
        try:
            pod_name = _get_primary_pod_name(k8s, namespace, deployment_id)
            admin_password = _get_admin_password(k8s, namespace, deployment_id)
            
            drop_user_script = f"""mongosh --quiet -u admin -p '{admin_password}' --authenticationDatabase admin <<'MONGOEOF'
db = db.getSiblingDB('{user_db}');
try {{
    db.dropUser('{username}');
    print('USER_DROPPED');
}} catch(e) {{
    print('ERROR: ' + e.message);
}}
MONGOEOF
"""

            resp = k8s.exec_in_pod(
                pod_name=pod_name,
                namespace=namespace,
                container='mongod',
                command=['/bin/bash', '-c', drop_user_script],
            )
            
            print(f"[DB_USER] Drop user response: {resp}")
                
        except Exception as e:
            print(f"[DB_USER] Warning: Could not drop user from MongoDB: {e}")
            # Continue anyway to clean up K8s resources
    
    else:
        # For Enterprise: Delete MongoDBUser CR
        try:
            k8s.custom_objects.delete_namespaced_custom_object(
                group="mongodb.com",
                version="v1",
                namespace=namespace,
                plural="mongodbusers",
                name=mongodb_user_name
            )
            print(f"[DB_USER] Deleted MongoDBUser CR: {mongodb_user_name}")
        except client.exceptions.ApiException as e:
            if e.status == 404:
                print(f"[DB_USER] MongoDBUser CR {mongodb_user_name} not found, skipping")
            else:
                raise

    # Delete Secret
    try:
        k8s.core_v1.delete_namespaced_secret(secret_name, namespace)
        print(f"[DB_USER] Deleted secret: {secret_name}")
    except client.exceptions.ApiException as e:
        if e.status == 404:
            print(f"[DB_USER] Secret {secret_name} not found, skipping")
        else:
            raise

    # Delete metadata
    from app.services.mongo_repo import MongoRepository
    repo_instance = MongoRepository()
    repo_instance.db_users.delete_one(
        {"_id": f"{tenant_id}:{deployment_id}:{username}"}
    )
    print(f"[DB_USER] Deleted metadata for user: {username}")

    return {
        "deleted": True,
        "username": username
    }
