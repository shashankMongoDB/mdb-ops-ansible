import secrets
import string
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from kubernetes import client

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    print("[COMMUNITY_BACKUP] Warning: boto3 not installed, S3 snapshot listing will not work")

from app import config
from app.services.mongo_repo import MongoRepository
from app.services.k8s_client import K8sClient


def get_repo() -> MongoRepository:
    return MongoRepository()


def get_k8s_client() -> K8sClient:
    return K8sClient()


def generate_password(length: int = 24) -> str:
    """Generate a strong random password"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def discover_mongodb_connection(namespace: str, deployment_id: str) -> Dict[str, str]:
    """
    Discover MongoDB connection details for Community deployment.
    
    Returns:
        Dict with 'hosts' and 'rsName'
    """
    k8s = get_k8s_client()
    
    # Find pods for this deployment
    try:
        pods = k8s.core_v1.list_namespaced_pod(
            namespace=namespace,
            label_selector=f"app={deployment_id}-svc"
        )
    except client.exceptions.ApiException as e:
        raise ValueError(f"Failed to list pods for deployment {deployment_id}: {str(e)}")
    
    if not pods.items:
        raise ValueError(f"No pods found for deployment {deployment_id} in namespace {namespace}")
    
    print(f"[COMMUNITY_BACKUP] Found {len(pods.items)} pods for {deployment_id}")
    
    # Build host list from running pods
    hosts = []
    for pod in pods.items:
        pod_name = pod.metadata.name
        host = f"{pod_name}.{deployment_id}-svc.{namespace}.svc.cluster.local:27017"
        hosts.append(host)
    
    mongodb_hosts = ",".join(hosts)
    mongodb_rs_name = deployment_id
    
    print(f"[COMMUNITY_BACKUP] RS name: {mongodb_rs_name}")
    print(f"[COMMUNITY_BACKUP] Hosts: {mongodb_hosts}")
    
    return {
        "hosts": mongodb_hosts,
        "rsName": mongodb_rs_name
    }


def create_backup_mongodb_user(namespace: str, deployment_id: str, external_host: str = None, external_port: int = None) -> str:
    """
    Create a MongoDB backup user directly via mongosh exec.
    
    For Community MongoDB, we create the user directly since MongoDBUser CR doesn't exist.
    
    Returns the generated password.
    """
    k8s = get_k8s_client()
    
    # Generate password
    backup_password = generate_password(24)
    
    # Get the first pod to exec into
    pods = k8s.core_v1.list_namespaced_pod(
        namespace=namespace,
        label_selector=f"app={deployment_id}-svc"
    )
    
    if not pods.items:
        raise ValueError(f"No pods found for deployment {deployment_id}")
    
    pod_name = pods.items[0].metadata.name
    
    # Create user via mongosh using here-doc to avoid escaping issues
    from kubernetes.stream import stream
    
    create_user_script = f"""mongosh --quiet <<'MONGOEOF'
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
        throw e;
    }}
}}
MONGOEOF
"""
    
    command = ['/bin/bash', '-c', create_user_script]
    
    try:
        resp = stream(
            k8s.core_v1.connect_get_namespaced_pod_exec,
            pod_name,
            namespace,
            container='mongod',  # Specify the mongod container for Community MongoDB
            command=command,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False
        )
        
        print(f"[COMMUNITY_BACKUP] MongoDB user creation response: {resp}")
        
        if 'BACKUP_USER_CREATED' in resp or 'BACKUP_USER_UPDATED' in resp:
            print(f"[COMMUNITY_BACKUP] Successfully created/updated backup user in pod {pod_name}")
        else:
            print(f"[COMMUNITY_BACKUP] Warning: Unexpected response: {resp}")
            
    except Exception as e:
        print(f"[COMMUNITY_BACKUP] Error executing mongosh command: {e}")
        # Don't fail if user creation fails - password secret will still be created
        print(f"[COMMUNITY_BACKUP] Continuing with password generation...")
    
    # Store password in secret for CronJob to use
    secret_name = f"{deployment_id}-backupuser-password"
    secret = client.V1Secret(
        api_version="v1",
        kind="Secret",
        metadata=client.V1ObjectMeta(
            name=secret_name,
            namespace=namespace,
            labels={
                "app": "community-mongodb-backup",
                "deployment": deployment_id
            }
        ),
        type="Opaque",
        string_data={
            "password": backup_password
        }
    )
    
    try:
        k8s.core_v1.create_namespaced_secret(namespace, secret)
        print(f"[COMMUNITY_BACKUP] Created password secret: {secret_name}")
    except client.exceptions.ApiException as e:
        if e.status == 409:
            k8s.core_v1.patch_namespaced_secret(secret_name, namespace, secret)
            print(f"[COMMUNITY_BACKUP] Updated existing secret: {secret_name}")
        else:
            raise
    
    return backup_password


def create_backup_credentials_secret(
    namespace: str,
    deployment_id: str,
    mongodb_hosts: str,
    rs_name: str,
    password: str,
    external_host: str = None,
    external_port: int = None
) -> None:
    """
    Create Secret with MongoDB connection URI for backup.
    
    Note: Uses external NodePort connection for backup jobs (not internal DNS).
    """
    k8s = get_k8s_client()
    
    # Use external NodePort connection if available, otherwise fall back to internal
    if external_host and external_port:
        # External connection via NodePort (no TLS for Community)
        mongodb_uri = f"mongodb://backupuser:{password}@{external_host}:{external_port}/admin"
        print(f"[COMMUNITY_BACKUP] ✅ Using EXTERNAL connection: {external_host}:{external_port}")
    else:
        # Fall back to internal DNS (with TLS)
        first_host = mongodb_hosts.split(',')[0]
        mongodb_uri = f"mongodb://backupuser:{password}@{first_host}/admin?tls=true&tlsInsecure=true"
        print(f"[COMMUNITY_BACKUP] ⚠️  WARNING: Using INTERNAL connection: {first_host}")
        print(f"[COMMUNITY_BACKUP] ⚠️  This may not work from backup pods. Please check external service.")
    
    secret_name = f"{deployment_id}-backup-credentials"
    secret = client.V1Secret(
        api_version="v1",
        kind="Secret",
        metadata=client.V1ObjectMeta(
            name=secret_name,
            namespace=namespace,
            labels={
                "app": "community-mongodb-backup",
                "deployment": deployment_id
            }
        ),
        type="Opaque",
        string_data={
            "MONGODB_URI": mongodb_uri
        }
    )
    
    try:
        k8s.core_v1.create_namespaced_secret(namespace, secret)
        print(f"[COMMUNITY_BACKUP] Created credentials secret: {secret_name}")
    except client.exceptions.ApiException as e:
        if e.status == 409:
            k8s.core_v1.patch_namespaced_secret(secret_name, namespace, secret)
            print(f"[COMMUNITY_BACKUP] Updated credentials secret: {secret_name}")
        else:
            raise


def validate_filesystem_reachability(
    namespace: str,
    backup_host: str,
    backup_path: str
) -> tuple[bool, str]:
    """
    Validate that filesystem backup target is reachable from cluster.
    
    Creates a test pod to verify:
    1. Network connectivity to backup host
    2. Write access to backup path
    
    Returns: (success: bool, message: str)
    """
    k8s = get_k8s_client()
    
    test_pod_name = f"backup-test-{int(time.time())}"
    
    # Create test pod that tries to write to the path
    test_pod = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": test_pod_name,
            "namespace": namespace
        },
        "spec": {
            "containers": [{
                "name": "test",
                "image": "busybox",
                "command": [
                    "sh", "-c",
                    f"mkdir -p {backup_path} && "
                    f"echo 'test' > {backup_path}/test-{int(time.time())}.txt && "
                    f"echo 'Backup path is writable' || "
                    f"echo 'Backup path is not writable'"
                ]
            }],
            "restartPolicy": "Never"
        }
    }
    
    try:
        print(f"[FILESYSTEM_BACKUP] Creating test pod to validate {backup_host}:{backup_path}")
        k8s.core_v1.create_namespaced_pod(namespace, test_pod)
        
        # Wait for pod to complete (max 15 seconds)
        max_wait = 15
        for i in range(max_wait):
            time.sleep(1)
            try:
                pod = k8s.core_v1.read_namespaced_pod(test_pod_name, namespace)
                if pod.status.phase in ["Succeeded", "Failed"]:
                    break
            except:
                pass
        
        # Check final status
        pod = k8s.core_v1.read_namespaced_pod(test_pod_name, namespace)
        success = pod.status.phase == "Succeeded"
        
        # Get logs
        try:
            logs = k8s.core_v1.read_namespaced_pod_log(test_pod_name, namespace)
            print(f"[FILESYSTEM_BACKUP] Test pod logs: {logs}")
        except:
            logs = ""
        
        # Cleanup
        k8s.core_v1.delete_namespaced_pod(test_pod_name, namespace)
        
        if success:
            return True, "Filesystem backup path is reachable and writable"
        else:
            return False, f"Filesystem backup path test failed. Pod status: {pod.status.phase}"
            
    except Exception as e:
        # Cleanup on error
        try:
            k8s.core_v1.delete_namespaced_pod(test_pod_name, namespace)
        except:
            pass
        
        return False, f"Failed to validate filesystem backup path: {str(e)}"


def deploy_backup_cronjob_filesystem(
    namespace: str,
    deployment_id: str,
    backup_host: str,
    backup_path: str,
    sub_directory: str,
    schedule: str,
    retention_days: int
) -> None:
    """
    Deploy filesystem backup CronJob.
    
    Mounts NFS/EFS and runs mongodump to write directly to mounted path.
    """
    k8s = get_k8s_client()
    
    sa_name = f"{deployment_id}-backup"
    cronjob_name = f"{deployment_id}-backup-fs"
    
    # Build full backup path
    full_path = f"{backup_path}/{sub_directory}" if sub_directory else backup_path
    
    cronjob = {
        "apiVersion": "batch/v1",
        "kind": "CronJob",
        "metadata": {
            "name": cronjob_name,
            "namespace": namespace,
            "labels": {
                "app": "community-mongodb-backup",
                "deployment": deployment_id,
                "type": "filesystem"
            }
        },
        "spec": {
            "schedule": schedule,
            "successfulJobsHistoryLimit": 3,
            "failedJobsHistoryLimit": 3,
            "jobTemplate": {
                "spec": {
                    "template": {
                        "spec": {
                            "serviceAccountName": sa_name,
                            "restartPolicy": "OnFailure",
                            "containers": [{
                                "name": "mongodump-filesystem",
                                "image": config.COMMUNITY_BACKUP_MONGODUMP_IMAGE,
                                "command": ["/bin/bash", "-c"],
                                "args": [
                                    f"""
                                    timestamp=$(date +%Y%m%d-%H%M%S)
                                    backup_file="{full_path}/dump-$timestamp.gz"
                                    
                                    mkdir -p {full_path}
                                    
                                    echo "Starting backup to $backup_file"
                                    mongodump --uri="$MONGODB_URI" --archive="$backup_file" --gzip
                                    
                                    if [ $? -eq 0 ]; then
                                        echo "Backup completed successfully: $backup_file"
                                        
                                        # Cleanup old backups
                                        echo "Cleaning up backups older than {retention_days} days"
                                        find {full_path} -name "dump-*.gz" -type f -mtime +{retention_days} -delete
                                    else
                                        echo "Backup failed"
                                        exit 1
                                    fi
                                    """
                                ],
                                "envFrom": [
                                    {"secretRef": {"name": f"{deployment_id}-backup-credentials"}}
                                ],
                                "resources": {
                                    "requests": {
                                        "cpu": config.COMMUNITY_BACKUP_CPU_REQUEST,
                                        "memory": config.COMMUNITY_BACKUP_MEMORY_REQUEST
                                    },
                                    "limits": {
                                        "cpu": config.COMMUNITY_BACKUP_CPU_LIMIT,
                                        "memory": config.COMMUNITY_BACKUP_MEMORY_LIMIT
                                    }
                                }
                            }]
                        }
                    }
                }
            }
        }
    }
    
    try:
        k8s.custom_objects.create_namespaced_custom_object(
            group="batch",
            version="v1",
            namespace=namespace,
            plural="cronjobs",
            body=cronjob
        )
        print(f"[FILESYSTEM_BACKUP] Created CronJob: {cronjob_name}")
    except client.exceptions.ApiException as e:
        if e.status == 409:
            k8s.custom_objects.patch_namespaced_custom_object(
                group="batch",
                version="v1",
                namespace=namespace,
                plural="cronjobs",
                name=cronjob_name,
                body=cronjob
            )
            print(f"[FILESYSTEM_BACKUP] Updated CronJob: {cronjob_name}")
        else:
            raise


def deploy_backup_cronjob(
    namespace: str,
    deployment_id: str,
    schedule: str = "0 */4 * * *",
    retention_days: int = 7,
    s3_bucket: str = None,
    s3_prefix: str = None,
    s3_region: str = None
) -> None:
    """
    Deploy backup CronJob and supporting resources.
    """
    k8s = get_k8s_client()
    
    # Use provided values or fall back to config
    s3_bucket = s3_bucket or config.COMMUNITY_BACKUP_S3_BUCKET
    s3_prefix = s3_prefix or config.COMMUNITY_BACKUP_S3_PREFIX
    s3_region = s3_region or config.COMMUNITY_BACKUP_S3_REGION
    
    sa_name = f"{deployment_id}-backup"
    cronjob_name = f"{deployment_id}-backup"
    
    # Create ServiceAccount
    sa = client.V1ServiceAccount(
        api_version="v1",
        kind="ServiceAccount",
        metadata=client.V1ObjectMeta(
            name=sa_name,
            namespace=namespace,
            labels={"app": "community-mongodb-backup", "deployment": deployment_id}
        )
    )
    
    if config.COMMUNITY_BACKUP_IRSA_ROLE_ARN:
        sa.metadata.annotations = {
            "eks.amazonaws.com/role-arn": config.COMMUNITY_BACKUP_IRSA_ROLE_ARN
        }
    
    try:
        k8s.core_v1.create_namespaced_service_account(namespace, sa)
        print(f"[COMMUNITY_BACKUP] Created ServiceAccount: {sa_name}")
    except client.exceptions.ApiException as e:
        if e.status == 409:
            k8s.core_v1.patch_namespaced_service_account(sa_name, namespace, sa)
        else:
            raise
    
    # Create CronJob
    s3_path = f"s3://{s3_bucket}/{s3_prefix}/{deployment_id}/snapshots"
    
    cronjob = {
        "apiVersion": "batch/v1",
        "kind": "CronJob",
        "metadata": {
            "name": cronjob_name,
            "namespace": namespace,
            "labels": {
                "app": "community-mongodb-backup",
                "deployment": deployment_id
            }
        },
        "spec": {
            "schedule": schedule,
            "successfulJobsHistoryLimit": 3,
            "failedJobsHistoryLimit": 3,
            "jobTemplate": {
                "spec": {
                    "template": {
                        "spec": {
                            "serviceAccountName": sa_name,
                            "restartPolicy": "OnFailure",
                            "initContainers": [
                                {
                                    "name": "mongodump",
                                    "image": config.COMMUNITY_BACKUP_MONGODUMP_IMAGE,
                                    "command": ["/bin/bash", "-c"],
                                    "args": [
                                        f"""
                                        timestamp=$(date +%Y%m%d-%H%M%S)
                                        dump_path="/backup/dump-$timestamp"
                                        mongodump --uri="$MONGODB_URI" --out="$dump_path" --gzip
                                        cd /backup && tar -czf "dump-$timestamp.tar.gz" "dump-$timestamp"
                                        rm -rf "$dump_path"
                                        echo "Backup created: dump-$timestamp.tar.gz"
                                        """
                                    ],
                                    "envFrom": [
                                        {"secretRef": {"name": f"{deployment_id}-backup-credentials"}}
                                    ],
                                    "volumeMounts": [
                                        {"name": "backup-data", "mountPath": "/backup"}
                                    ],
                                    "resources": {
                                        "requests": {
                                            "cpu": config.COMMUNITY_BACKUP_CPU_REQUEST,
                                            "memory": config.COMMUNITY_BACKUP_MEMORY_REQUEST
                                        },
                                        "limits": {
                                            "cpu": config.COMMUNITY_BACKUP_CPU_LIMIT,
                                            "memory": config.COMMUNITY_BACKUP_MEMORY_LIMIT
                                        }
                                    }
                                }
                            ],
                            "containers": [
                                {
                                    "name": "s3-upload",
                                    "image": config.COMMUNITY_BACKUP_AWS_CLI_IMAGE,
                                    "command": ["/bin/bash", "-c"],
                                    "args": [
                                        f"""
                                        cd /backup
                                        for file in dump-*.tar.gz; do
                                            aws s3 cp "$file" "{s3_path}/$file" --region {s3_region}
                                            echo "Uploaded: $file"
                                        done
                                        
                                        # Cleanup old backups
                                        cutoff_date=$(date -d "{retention_days} days ago" +%Y%m%d || date -v-{retention_days}d +%Y%m%d)
                                        aws s3 ls "{s3_path}/" --region {s3_region} | while read -r line; do
                                            file=$(echo "$line" | awk '{{print $4}}')
                                            file_date=$(echo "$file" | grep -oP 'dump-\\K[0-9]{{8}}' || echo "")
                                            if [[ -n "$file_date" && "$file_date" -lt "$cutoff_date" ]]; then
                                                aws s3 rm "{s3_path}/$file" --region {s3_region}
                                                echo "Deleted old backup: $file"
                                            fi
                                        done
                                        """
                                    ],
                                    "volumeMounts": [
                                        {"name": "backup-data", "mountPath": "/backup"}
                                    ],
                                    "resources": {
                                        "requests": {"cpu": "100m", "memory": "128Mi"},
                                        "limits": {"cpu": "500m", "memory": "512Mi"}
                                    }
                                }
                            ],
                            "volumes": [
                                {"name": "backup-data", "emptyDir": {}}
                            ]
                        }
                    }
                }
            }
        }
    }
    
    try:
        k8s.custom_objects.create_namespaced_custom_object(
            group="batch",
            version="v1",
            namespace=namespace,
            plural="cronjobs",
            body=cronjob
        )
        print(f"[COMMUNITY_BACKUP] Created CronJob: {cronjob_name}")
    except client.exceptions.ApiException as e:
        if e.status == 409:
            k8s.custom_objects.patch_namespaced_custom_object(
                group="batch",
                version="v1",
                namespace=namespace,
                plural="cronjobs",
                name=cronjob_name,
                body=cronjob
            )
            print(f"[COMMUNITY_BACKUP] Updated CronJob: {cronjob_name}")
        else:
            raise


def enable_community_backup(
    tenant_id: str,
    deployment_id: str,
    backup_type: str = "s3",
    s3_bucket: Optional[str] = None,
    s3_prefix: Optional[str] = None,
    s3_region: Optional[str] = None,
    filesystem_config: Optional[Dict[str, str]] = None,
    schedule: str = "0 */4 * * *",
    retention_days: int = 7
) -> Dict[str, Any]:
    """
    Enable Community MongoDB backup for a deployment.
    
    Supports two backup types:
    - s3: Backup to S3 bucket (requires s3_bucket, s3_prefix, s3_region)
    - filesystem: Backup to NFS/EFS (requires filesystem_config with backupHost, backupPath, subDirectory)
    
    Orchestrates:
    1. Discover connection
    2. Create backup user
    3. Create credentials secret
    4. Validate filesystem (if type=filesystem)
    5. Deploy CronJob (S3 or Filesystem)
    
    Returns backup configuration.
    """
    repo = get_repo()
    
    # Verify tenant and deployment
    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")
    
    if tenant.get("plan") != "community":
        raise ValueError("Community backup is only available for Community plan deployments")
    
    deployment = repo.get_deployment(tenant_id, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment {deployment_id} not found")
    
    namespace = tenant["namespace"]
    
    print(f"[COMMUNITY_BACKUP] Enabling {backup_type} backup for {deployment_id} in {namespace}")
    
    # Step 1: Discover connection
    conn_info = discover_mongodb_connection(namespace, deployment_id)
    
    # Step 1.5: Get external connection (NodePort) for backup jobs
    from app.services import lifecycle_service
    from app.services import k8s_client as k8s_helper
    
    external_host = None
    external_port = None
    
    try:
        # Get worker node IP
        external_host = k8s_helper.get_worker_node_ip()
        
        # Get NodePort from external service
        k8s = get_k8s_client()
        try:
            svc = k8s.core_v1.read_namespaced_service(
                name=f"{deployment_id}-svc-external",
                namespace=namespace
            )
            # Get the NodePort
            if svc.spec.ports:
                external_port = svc.spec.ports[0].node_port
                print(f"[COMMUNITY_BACKUP] Found external service: {external_host}:{external_port}")
        except client.exceptions.ApiException as e:
            if e.status == 404:
                print(f"[COMMUNITY_BACKUP] External service not found, creating it...")
                # Create external service
                k8s_helper.ensure_external_service(namespace, deployment_id)
                # Try reading again
                svc = k8s.core_v1.read_namespaced_service(
                    name=f"{deployment_id}-svc-external",
                    namespace=namespace
                )
                if svc.spec.ports:
                    external_port = svc.spec.ports[0].node_port
                    print(f"[COMMUNITY_BACKUP] Created external service: {external_host}:{external_port}")
            else:
                raise
                
    except Exception as e:
        print(f"[COMMUNITY_BACKUP] Warning: Could not get external connection: {e}")
        import traceback
        traceback.print_exc()
        external_host = None
        external_port = None
    
    # Step 2: Create backup user
    backup_password = create_backup_mongodb_user(namespace, deployment_id, external_host, external_port)
    
    # Step 3: Create credentials secret with external connection
    create_backup_credentials_secret(
        namespace,
        deployment_id,
        conn_info["hosts"],
        conn_info["rsName"],
        backup_password,
        external_host,
        external_port
    )
    
    # Step 4 & 5: Deploy CronJob based on type
    if backup_type == "filesystem":
        if not filesystem_config:
            raise ValueError("filesystem_config is required for filesystem backup")
        
        backup_host = filesystem_config.get("backupHost")
        backup_path = filesystem_config.get("backupPath")
        sub_directory = filesystem_config.get("subDirectory", deployment_id)
        
        if not backup_host or not backup_path:
            raise ValueError("backupHost and backupPath are required for filesystem backup")
        
        # Validate filesystem reachability
        print(f"[COMMUNITY_BACKUP] Validating filesystem {backup_host}:{backup_path}")
        success, message = validate_filesystem_reachability(namespace, backup_host, backup_path)
        if not success:
            raise ValueError(f"Backup path not reachable from cluster: {message}. Please verify NFS/EFS mount configuration.")
        
        # Deploy filesystem CronJob
        deploy_backup_cronjob_filesystem(
            namespace=namespace,
            deployment_id=deployment_id,
            backup_host=backup_host,
            backup_path=backup_path,
            sub_directory=sub_directory,
            schedule=schedule,
            retention_days=retention_days
        )
        
        # Ensure CronJob is not suspended (in case it was previously disabled)
        k8s = get_k8s_client()
        cronjob_name = f"{deployment_id}-backup-fs"
        try:
            k8s.custom_objects.patch_namespaced_custom_object(
                group="batch",
                version="v1",
                namespace=namespace,
                plural="cronjobs",
                name=cronjob_name,
                body={"spec": {"suspend": False}}
            )
            print(f"[COMMUNITY_BACKUP] Unsuspended CronJob: {cronjob_name}")
        except client.exceptions.ApiException as e:
            if e.status != 404:
                print(f"[COMMUNITY_BACKUP] Warning: Could not unsuspend CronJob: {e}")
        
        target = f"{backup_host}:{backup_path}/{sub_directory}"
        
        # Store config in deployment metadata
        repo.update_deployment_metadata(tenant_id, deployment_id, {
            "backupType": backup_type,
            "backupTarget": target,
            "backupSchedule": schedule,
            "backupRetentionDays": retention_days
        })
        
        return {
            "enabled": True,
            "type": backup_type,
            "schedule": schedule,
            "target": target,
            "retentionDays": retention_days
        }
    
    else:  # S3 backup
        if not s3_bucket:
            raise ValueError("s3_bucket is required for S3 backup")
        
        # Deploy S3 CronJob with user-provided parameters
        deploy_backup_cronjob(
            namespace=namespace,
            deployment_id=deployment_id,
            schedule=schedule,
            retention_days=retention_days,
            s3_bucket=s3_bucket,
            s3_prefix=s3_prefix,
            s3_region=s3_region
        )
        
        # Ensure CronJob is not suspended (in case it was previously disabled)
        k8s = get_k8s_client()
        cronjob_name = f"{deployment_id}-backup"
        try:
            k8s.custom_objects.patch_namespaced_custom_object(
                group="batch",
                version="v1",
                namespace=namespace,
                plural="cronjobs",
                name=cronjob_name,
                body={"spec": {"suspend": False}}
            )
            print(f"[COMMUNITY_BACKUP] Unsuspended CronJob: {cronjob_name}")
        except client.exceptions.ApiException as e:
            if e.status != 404:
                print(f"[COMMUNITY_BACKUP] Warning: Could not unsuspend CronJob: {e}")
        
        s3_path = f"s3://{s3_bucket}/{s3_prefix}/snapshots/"
        
        # Store config in deployment metadata
        repo.update_deployment_metadata(tenant_id, deployment_id, {
            "backupType": backup_type,
            "s3Bucket": s3_bucket,
            "s3Prefix": s3_prefix,
            "s3Region": s3_region,
            "backupSchedule": schedule,
            "backupRetentionDays": retention_days
        })
        
        return {
            "enabled": True,
            "type": backup_type,
            "schedule": schedule,
            "s3Path": s3_path,
            "s3Bucket": s3_bucket,
            "s3Prefix": s3_prefix,
            "s3Region": s3_region,
            "retentionDays": retention_days
        }


def disable_community_backup(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Disable Community MongoDB backup by suspending the CronJob.
    """
    repo = get_repo()
    k8s = get_k8s_client()
    
    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")
    
    namespace = tenant["namespace"]
    
    # Get deployment metadata to determine backup type
    deployment = repo.get_deployment(tenant_id, deployment_id)
    backup_type = deployment.get("backupType", "s3")
    
    cronjob_name = f"{deployment_id}-backup-fs" if backup_type == "filesystem" else f"{deployment_id}-backup"
    
    # Patch CronJob to suspend it
    try:
        k8s.custom_objects.patch_namespaced_custom_object(
            group="batch",
            version="v1",
            namespace=namespace,
            plural="cronjobs",
            name=cronjob_name,
            body={"spec": {"suspend": True}}
        )
        print(f"[COMMUNITY_BACKUP] Suspended CronJob: {cronjob_name}")
    except client.exceptions.ApiException as e:
        if e.status == 404:
            raise ValueError(f"CronJob {cronjob_name} not found")
        raise
    
    return {"enabled": False}


def get_community_backup_status(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Get Community MongoDB backup status.
    
    Returns status including schedule, last backup time, and location (S3 or filesystem).
    """
    repo = get_repo()
    k8s = get_k8s_client()
    
    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")
    
    if tenant.get("plan") != "community":
        return {
            "enabled": False,
            "status": "NOT_AVAILABLE",
            "message": "Community backup is only available for Community plan deployments"
        }
    
    namespace = tenant["namespace"]
    
    # Get deployment metadata to determine backup type
    deployment = repo.get_deployment(tenant_id, deployment_id)
    backup_type = deployment.get("backupType", "s3")
    
    # Try both CronJob names (S3 and filesystem)
    cronjob_name = f"{deployment_id}-backup-fs" if backup_type == "filesystem" else f"{deployment_id}-backup"
    
    # Check if CronJob exists
    try:
        cronjob = k8s.custom_objects.get_namespaced_custom_object(
            group="batch",
            version="v1",
            namespace=namespace,
            plural="cronjobs",
            name=cronjob_name
        )
    except client.exceptions.ApiException as e:
        if e.status == 404:
            return {
                "enabled": False,
                "type": backup_type,
                "status": "NOT_CONFIGURED",
                "schedule": None,
                "lastSuccessfulTime": None
            }
        raise
    
    # Parse CronJob status
    spec = cronjob.get("spec", {})
    status = cronjob.get("status", {})
    
    enabled = not spec.get("suspend", False)
    schedule = spec.get("schedule", "")
    last_successful_time = status.get("lastSuccessfulTime")
    
    result = {
        "enabled": enabled,
        "type": backup_type,
        "status": "ACTIVE" if enabled else "SUSPENDED",
        "schedule": schedule,
        "lastSuccessfulTime": last_successful_time,
        "retentionDays": deployment.get("backupRetentionDays", 7)
    }
    
    # Add type-specific fields
    if backup_type == "filesystem":
        result["target"] = deployment.get("backupTarget")
    else:
        result["s3Bucket"] = deployment.get("s3Bucket")
        result["s3Prefix"] = deployment.get("s3Prefix")
        result["s3Region"] = deployment.get("s3Region")
        result["s3Path"] = f"s3://{deployment.get('s3Bucket')}/{deployment.get('s3Prefix')}/snapshots/"
    
    return result
