"""
Helper functions for Community MongoDB backup user creation.

Community MongoDB doesn't use MongoDBUser CR, so we create users directly.
"""

import secrets
import string
from kubernetes import client
from kubernetes.stream import stream


def create_backup_user_directly(k8s_client, namespace: str, deployment_id: str, external_uri: str) -> str:
    """
    Create MongoDB backup user directly using mongosh via kubectl exec.
    
    Args:
        k8s_client: Kubernetes client
        namespace: K8s namespace
        deployment_id: MongoDB deployment ID
        external_uri: External MongoDB connection string (NodePort)
    
    Returns:
        Generated password
    """
    # Generate secure password
    alphabet = string.ascii_letters + string.digits
    backup_password = ''.join(secrets.choice(alphabet) for _ in range(24))
    
    # Get the first pod to exec into
    pods = k8s_client.core_v1.list_namespaced_pod(
        namespace=namespace,
        label_selector=f"app={deployment_id}-svc"
    )
    
    if not pods.items:
        raise ValueError(f"No pods found for deployment {deployment_id}")
    
    pod_name = pods.items[0].metadata.name
    
    # Create user command
    create_user_js = f"""
db = db.getSiblingDB('admin');
try {{
    db.createUser({{
        user: 'backupuser',
        pwd: '{backup_password}',
        roles: [
            {{ role: 'backup', db: 'admin' }},
            {{ role: 'clusterMonitor', db: 'admin' }},
            {{ role: 'readAnyDatabase', db: 'admin' }}
        ]
    }});
    print('BACKUP_USER_CREATED');
}} catch(e) {{
    if (e.code === 51003) {{
        db.updateUser('backupuser', {{
            pwd: '{backup_password}',
            roles: [
                {{ role: 'backup', db: 'admin' }},
                {{ role: 'clusterMonitor', db: 'admin' }},
                {{ role: 'readAnyDatabase', db: 'admin' }}
            ]
        }});
        print('BACKUP_USER_UPDATED');
    }} else {{
        print('ERROR: ' + e.message);
        throw e;
    }}
}}
"""
    
    # Execute via mongosh
    command = ['/bin/bash', '-c', f'mongosh --quiet --eval \'{create_user_js}\'']
    
    try:
        resp = stream(
            k8s_client.core_v1.connect_get_namespaced_pod_exec,
            pod_name,
            namespace,
            command=command,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False
        )
        
        print(f"[COMMUNITY_BACKUP] MongoDB user creation response: {resp}")
        
        if 'BACKUP_USER_CREATED' in resp or 'BACKUP_USER_UPDATED' in resp:
            print(f"[COMMUNITY_BACKUP] Successfully created/updated backup user in pod {pod_name}")
            return backup_password
        else:
            raise ValueError(f"Failed to create backup user. Output: {resp}")
            
    except Exception as e:
        print(f"[COMMUNITY_BACKUP] Error executing mongosh command: {e}")
        raise ValueError(f"Failed to create MongoDB backup user: {str(e)}")
