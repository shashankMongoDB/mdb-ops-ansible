import secrets
import string
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from urllib.parse import quote_plus
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


def _build_s3_client(region: Optional[str]):
    if not BOTO3_AVAILABLE:
        raise ValueError("boto3 is not installed on the backend. Install boto3 to validate S3 buckets.")

    boto_kwargs = {"region_name": region or "us-east-1"}
    if config.COMMUNITY_BACKUP_S3_ENDPOINT_URL:
        boto_kwargs["endpoint_url"] = config.COMMUNITY_BACKUP_S3_ENDPOINT_URL
    if config.COMMUNITY_BACKUP_S3_NO_VERIFY_SSL:
        boto_kwargs["verify"] = False
    return boto3.client("s3", **boto_kwargs)


def validate_s3_bucket_access(s3_bucket: str, s3_region: Optional[str], test_prefix: str) -> None:
    """Validate bucket exists and is accessible (head + put/delete probe)."""
    s3_client = _build_s3_client(s3_region)

    try:
        s3_client.head_bucket(Bucket=s3_bucket)
    except ClientError as e:
        code = (e.response.get("Error") or {}).get("Code", "Unknown")
        raise ValueError(f"S3 bucket '{s3_bucket}' is not accessible or does not exist (head_bucket failed: {code})")

    probe_key = f"{test_prefix.strip('/')}/.mdbaas-write-check-{int(time.time())}".strip("/")
    try:
        s3_client.put_object(Bucket=s3_bucket, Key=probe_key, Body=b"mdbaas-check")
        s3_client.delete_object(Bucket=s3_bucket, Key=probe_key)
    except ClientError as e:
        code = (e.response.get("Error") or {}).get("Code", "Unknown")
        raise ValueError(
            f"S3 bucket '{s3_bucket}' is reachable but write/delete validation failed at prefix '{test_prefix}' ({code}). "
            "Ensure IAM permissions include s3:PutObject and s3:DeleteObject for this prefix."
        )


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
    
    if not external_host or not external_port:
        raise ValueError("External primary host:port is required to create backup user")

    # Use one pod only as an exec runner; mongosh connects to external primary endpoint.
    pods = k8s.core_v1.list_namespaced_pod(namespace=namespace, label_selector=f"app={deployment_id}-svc")
    if not pods.items:
        raise ValueError(f"No pods found for deployment {deployment_id}")
    exec_pod = next((p.metadata.name for p in pods.items if p.metadata and p.metadata.name), None)
    if not exec_pod:
        raise ValueError(f"No valid pod names found for deployment {deployment_id}")
    
    # Get admin credentials from MongoDB Community secret
    admin_secret_name = f"{deployment_id}-admin-admin"
    try:
        admin_secret = k8s.core_v1.read_namespaced_secret(admin_secret_name, namespace)
        admin_password = admin_secret.data.get("password")
        if admin_password:
            import base64
            admin_password = base64.b64decode(admin_password).decode('utf-8')
        else:
            raise ValueError("Admin password not found")
    except client.exceptions.ApiException as e:
        if e.status == 404:
            # Try alternative name
            admin_secret_name = f"{deployment_id}-admin"
            try:
                admin_secret = k8s.core_v1.read_namespaced_secret(admin_secret_name, namespace)
                admin_password = admin_secret.data.get("password")
                if admin_password:
                    import base64
                    admin_password = base64.b64decode(admin_password).decode('utf-8')
                else:
                    raise ValueError("Admin password not found")
            except:
                raise ValueError(f"Could not find admin credentials. Tried: {deployment_id}-admin-admin, {deployment_id}-admin")
        else:
            raise
    
    print(f"[COMMUNITY_BACKUP] Found admin credentials in secret: {admin_secret_name}")
    
    # Create/update backup user via non-interactive mongosh eval
    from kubernetes.stream import stream

    js_eval = (
        "db = db.getSiblingDB('admin');"
        "try {"
        f"db.createUser({{user:'backupuser',pwd:'{backup_password}',roles:[{{role:'backup',db:'admin'}},{{role:'clusterMonitor',db:'admin'}},{{role:'readAnyDatabase',db:'admin'}}]}});"
        "print('BACKUP_USER_CREATED');"
        "} catch(e) {"
        "if (e.code === 51003) {"
        f"db.updateUser('backupuser', {{pwd:'{backup_password}',roles:[{{role:'backup',db:'admin'}},{{role:'clusterMonitor',db:'admin'}},{{role:'readAnyDatabase',db:'admin'}}]}});"
        "print('BACKUP_USER_UPDATED');"
        "} else {"
        "print('ERROR: ' + e.message);"
        "throw e;"
        "}"
        "}"
    )

    admin_password_encoded = quote_plus(admin_password)
    primary_uri = f"mongodb://admin:{admin_password_encoded}@{external_host}:{external_port}/admin?authSource=admin&directConnection=true"

    command = [
        'env',
        'HOME=/tmp',
        'mongosh',
        '--quiet',
        '--norc',
        primary_uri,
        '--eval',
        js_eval
    ]

    try:
        resp = stream(
            k8s.core_v1.connect_get_namespaced_pod_exec,
            exec_pod,
            namespace,
            container='mongod',
            command=command,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False
        )
        print(f"[COMMUNITY_BACKUP] MongoDB user creation response via external primary {external_host}:{external_port}: {resp}")
        if 'BACKUP_USER_CREATED' not in resp and 'BACKUP_USER_UPDATED' not in resp:
            raise ValueError(f"Failed to create backup user via external primary {external_host}:{external_port}: {resp}")
    except Exception as e:
        raise ValueError(f"Failed to create backup MongoDB user via external primary {external_host}:{external_port}: {e}")
    
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
    
    if not external_host or not external_port:
        raise ValueError("External primary NodePort connection is required for backups")

    mongodb_uri = f"mongodb://backupuser:{password}@{external_host}:{external_port}/?authSource=admin&directConnection=true"
    print(f"[COMMUNITY_BACKUP] ✅ Using EXTERNAL PRIMARY connection: {external_host}:{external_port}")
    
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
    
    # Build aws-cli flags for custom S3 endpoint (MinIO or other S3-compatible)
    s3_endpoint_url = config.COMMUNITY_BACKUP_S3_ENDPOINT_URL or ""
    s3_no_verify_ssl = config.COMMUNITY_BACKUP_S3_NO_VERIFY_SSL
    aws_endpoint_flags = ""
    if s3_endpoint_url:
        aws_endpoint_flags = f" --endpoint-url {s3_endpoint_url}"
        if s3_no_verify_ssl:
            aws_endpoint_flags += " --no-verify-ssl"

    # Create AWS/S3 credentials secret in this namespace (if credentials are configured)
    if config.AWS_ACCESS_KEY_ID and config.AWS_SECRET_ACCESS_KEY:
        aws_secret_name = "aws-backup-credentials"
        secret_data = {
            "AWS_ACCESS_KEY_ID": config.AWS_ACCESS_KEY_ID,
            "AWS_SECRET_ACCESS_KEY": config.AWS_SECRET_ACCESS_KEY,
            "AWS_DEFAULT_REGION": config.AWS_DEFAULT_REGION
        }
        if s3_endpoint_url:
            secret_data["S3_ENDPOINT_URL"] = s3_endpoint_url
        aws_secret = client.V1Secret(
            api_version="v1",
            kind="Secret",
            metadata=client.V1ObjectMeta(
                name=aws_secret_name,
                namespace=namespace
            ),
            type="Opaque",
            string_data=secret_data
        )

        try:
            k8s.core_v1.create_namespaced_secret(namespace, aws_secret)
            print(f"[COMMUNITY_BACKUP] Created AWS/S3 credentials secret in namespace: {namespace}")
        except client.exceptions.ApiException as e:
            if e.status == 409:
                k8s.core_v1.patch_namespaced_secret(aws_secret_name, namespace, aws_secret)
                print(f"[COMMUNITY_BACKUP] Updated AWS/S3 credentials secret in namespace: {namespace}")
            else:
                raise
    else:
        print(f"[COMMUNITY_BACKUP] No AWS/S3 credentials configured in environment, will rely on IRSA or existing secrets")
    
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
    snapshots_prefix = _resolve_snapshots_prefix({"s3Prefix": s3_prefix}, s3_bucket)
    # S3 path format: s3://bucket/<snapshots_prefix>/
    # Files will be named: dump-YYYYMMDD-HHMMSS.tar.gz
    s3_path = f"s3://{s3_bucket}/{snapshots_prefix}"
    
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
                                        set -euo pipefail
                                        timestamp=$(date +%Y%m%d-%H%M%S)
                                        dump_path="/backup/dump-$timestamp"
                                        mongodump --uri="$MONGODB_URI" --out="$dump_path" --gzip
                                        dump_files=$(find "$dump_path" -type f | wc -l | tr -d ' ')
                                        if [ "$dump_files" -eq 0 ]; then
                                          echo "ERROR: mongodump completed but produced no files"
                                          exit 1
                                        fi
                                        dump_size_bytes=$(du -sk "$dump_path" | awk '{{print $1}}')
                                        if [ "${{dump_size_bytes:-0}}" -lt 50 ]; then
                                          echo "ERROR: dump size too small (${{dump_size_bytes}}KB), refusing to upload"
                                          exit 1
                                        fi
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
                                    "env": [
                                        {
                                            "name": "AWS_ACCESS_KEY_ID",
                                            "valueFrom": {
                                                "secretKeyRef": {
                                                    "name": "aws-backup-credentials",
                                                    "key": "AWS_ACCESS_KEY_ID",
                                                    "optional": True
                                                }
                                            }
                                        },
                                        {
                                            "name": "AWS_SECRET_ACCESS_KEY",
                                            "valueFrom": {
                                                "secretKeyRef": {
                                                    "name": "aws-backup-credentials",
                                                    "key": "AWS_SECRET_ACCESS_KEY",
                                                    "optional": True
                                                }
                                            }
                                        },
                                        {
                                            "name": "AWS_DEFAULT_REGION",
                                            "valueFrom": {
                                                "secretKeyRef": {
                                                    "name": "aws-backup-credentials",
                                                    "key": "AWS_DEFAULT_REGION",
                                                    "optional": True
                                                }
                                            }
                                        }
                                    ],
                                    "command": ["/bin/bash", "-c"],
                                    "args": [
                                        f"""
                                        cd /backup
                                        for file in dump-*.tar.gz; do
                                            aws s3 cp "$file" "{s3_path}/$file" --region {s3_region}{aws_endpoint_flags}
                                            echo "Uploaded: $file"
                                        done

                                        # Cleanup old backups
                                        cutoff_date=$(date -d "{retention_days} days ago" +%Y%m%d || date -v-{retention_days}d +%Y%m%d)
                                        aws s3 ls "{s3_path}/" --region {s3_region}{aws_endpoint_flags} | while read -r line; do
                                            file=$(echo "$line" | awk '{{print $4}}')
                                            file_date=$(echo "$file" | grep -oP 'dump-\\K[0-9]{{8}}' || echo "")
                                            if [[ -n "$file_date" && "$file_date" -lt "$cutoff_date" ]]; then
                                                aws s3 rm "{s3_path}/$file" --region {s3_region}{aws_endpoint_flags}
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
    # Use lifecycle service to get the connection info
    external_host = None
    external_port = None
    
    print(f"[COMMUNITY_BACKUP] ========== GETTING EXTERNAL CONNECTION ==========")
    
    try:
        from app.services import lifecycle_service
        
        print(f"[COMMUNITY_BACKUP] Getting connection info from lifecycle service...")
        connection_info = lifecycle_service.get_connection_info(tenant_id, deployment_id)
        
        # Prefer role-specific PRIMARY endpoint to avoid random pod routing
        external_uri = (
            connection_info.get("externalPrimaryUri")
            or connection_info.get("externalUri", "")
        )
        print(f"[COMMUNITY_BACKUP] External URI from lifecycle: {external_uri}")
        
        if external_uri and "://" in external_uri:
            # Parse: mongodb://host:port/...
            # or mongodb://user:pass@host:port/...
            uri_after_protocol = external_uri.split("://")[1]
            
            # Remove database and query params if present
            if "/" in uri_after_protocol:
                host_port_part = uri_after_protocol.split("/")[0]
            else:
                host_port_part = uri_after_protocol
            
            # Remove user:pass@ if present
            if "@" in host_port_part:
                host_port_part = host_port_part.split("@")[1]
            
            # Parse host:port
            if ":" in host_port_part:
                external_host, port_str = host_port_part.split(":")
                external_port = int(port_str)
                print(f"[COMMUNITY_BACKUP] ✅ Parsed external connection: {external_host}:{external_port}")
            else:
                print(f"[COMMUNITY_BACKUP] ⚠️  No port in external URI, using default 27017")
                external_host = host_port_part
                external_port = 27017
        else:
            print(f"[COMMUNITY_BACKUP] ⚠️  External URI not available")

        # Hard fallback: resolve/create PRIMARY NodePort directly when lifecycle response is empty
        if not external_host or not external_port:
            k8s = get_k8s_client()
            worker_node_ip = k8s.get_worker_node_ip()
            pods = k8s.core_v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=f"app={deployment_id}-svc"
            )
            pod_names = [p.metadata.name for p in pods.items if p.metadata and p.metadata.name]
            primary_pod = pod_names[0] if pod_names else None

            from kubernetes.stream import stream
            import json
            for pod_name in pod_names:
                try:
                    resp = stream(
                        k8s.core_v1.connect_get_namespaced_pod_exec,
                        pod_name,
                        namespace,
                        container='mongod',
                        command=['/bin/bash', '-c', "mongosh --quiet --norc --eval 'JSON.stringify(db.hello())'"],
                        stderr=True,
                        stdin=False,
                        stdout=True,
                        tty=False
                    )
                    payload = None
                    for line in str(resp).splitlines()[::-1]:
                        line = line.strip()
                        if line.startswith('{') and line.endswith('}'):
                            payload = line
                            break
                    if payload and json.loads(payload).get("isWritablePrimary"):
                        primary_pod = pod_name
                        break
                except Exception:
                    continue

            if primary_pod:
                _, node_port = k8s.ensure_external_service_for_pod(namespace, deployment_id, primary_pod, "primary")
                external_host = worker_node_ip
                external_port = node_port
                print(f"[COMMUNITY_BACKUP] ✅ Resolved PRIMARY NodePort fallback: {external_host}:{external_port}")
            
    except Exception as e:
        print(f"[COMMUNITY_BACKUP] ❌ ERROR getting external connection: {e}")
        import traceback
        traceback.print_exc()
        external_host = None
        external_port = None
    
    print(f"[COMMUNITY_BACKUP] Final external connection: {external_host}:{external_port}")
    print(f"[COMMUNITY_BACKUP] ========== END EXTERNAL CONNECTION ==========")
    
    if not external_host or not external_port:
        raise ValueError("External primary endpoint is unavailable. Please wait for deployment readiness and retry.")
    
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
            "backupEnabled": True,  # Mark backup as enabled
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

        # Tenant-isolated default prefix: <namespace>/<deployment>
        effective_s3_prefix = (s3_prefix or f"{namespace}/{deployment_id}").strip("/")

        # Preflight validation: bucket exists + credentials can write/delete under tenant prefix
        validate_s3_bucket_access(
            s3_bucket=s3_bucket,
            s3_region=s3_region or "us-east-1",
            test_prefix=effective_s3_prefix
        )
        
        # Deploy S3 CronJob with user-provided parameters
        deploy_backup_cronjob(
            namespace=namespace,
            deployment_id=deployment_id,
            schedule=schedule,
            retention_days=retention_days,
            s3_bucket=s3_bucket,
            s3_prefix=effective_s3_prefix,
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
        
        snapshots_prefix = _resolve_snapshots_prefix({"s3Prefix": effective_s3_prefix}, s3_bucket)
        s3_path = f"s3://{s3_bucket}/{snapshots_prefix}"
        
        # Store config in deployment metadata
        repo.update_deployment_metadata(tenant_id, deployment_id, {
            "backupEnabled": True,  # Mark backup as enabled
            "backupType": backup_type,
            "s3Bucket": s3_bucket,
            "s3Prefix": effective_s3_prefix,
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
            "s3Prefix": effective_s3_prefix,
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
    
    # Update deployment metadata to mark backup as disabled
    repo.update_deployment_metadata(tenant_id, deployment_id, {
        "backupEnabled": False
    })
    
    return {"enabled": False}


def list_community_backup_snapshots(tenant_id: str, deployment_id: str) -> List[Dict[str, Any]]:
    """
    List backup snapshots from S3.
    
    Returns list of snapshots with metadata.
    """
    repo = get_repo()
    
    # Get deployment metadata to get S3 config
    deployment = repo.get_deployment(tenant_id, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment {deployment_id} not found")
    
    backup_type = deployment.get("backupType", "s3")
    
    if backup_type != "s3":
        return []  # Only S3 backups have snapshot listing
    
    s3_bucket = deployment.get("s3Bucket")
    s3_prefix = deployment.get("s3Prefix")
    s3_path = deployment.get("s3Path")
    s3_region = deployment.get("s3Region", "us-east-1")
    
    if not s3_bucket or (not s3_prefix and not s3_path):
        return []
    
    try:
        import boto3
        from botocore.exceptions import ClientError

        boto_kwargs = {"region_name": s3_region}
        if config.COMMUNITY_BACKUP_S3_ENDPOINT_URL:
            boto_kwargs["endpoint_url"] = config.COMMUNITY_BACKUP_S3_ENDPOINT_URL
        if config.COMMUNITY_BACKUP_S3_NO_VERIFY_SSL:
            boto_kwargs["verify"] = False
        s3_client = boto3.client('s3', **boto_kwargs)
        
        # List objects in snapshot directory. Try multiple compatible prefixes.
        resolved = _resolve_snapshots_prefix(deployment, s3_bucket).strip("/")
        raw_prefix = (s3_prefix or "").strip("/")
        candidates = [p for p in [
            resolved,
            raw_prefix,
            f"{raw_prefix}/snapshots" if raw_prefix else None,
            f"{raw_prefix}/snapshots/snapshots" if raw_prefix else None,
        ] if p]

        seen = set()
        snapshots = []
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)

            response = s3_client.list_objects_v2(
                Bucket=s3_bucket,
                Prefix=candidate + "/"
            )

            if 'Contents' not in response:
                continue
        
            for obj in response['Contents']:
                key = obj['Key']
                
                # Only include .tar.gz files
                if key.endswith('.tar.gz'):
                    filename = key.split('/')[-1]
                    
                    # Parse timestamp from filename: dump-YYYYMMDD-HHMMSS.tar.gz
                    try:
                        timestamp_str = filename.replace('dump-', '').replace('.tar.gz', '')
                        date_part = timestamp_str.split('-')[0]  # YYYYMMDD
                        time_part = timestamp_str.split('-')[1] if '-' in timestamp_str else '000000'  # HHMMSS
                        
                        # Format: YYYY-MM-DD HH:MM:SS
                        formatted_time = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]} {time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
                    except:
                        formatted_time = "Unknown"
                    
                    snapshots.append({
                        'filename': filename,
                        'size': obj['Size'],
                        'sizeFormatted': format_bytes(obj['Size']),
                        'lastModified': obj['LastModified'].isoformat(),
                        'timestamp': formatted_time,
                        's3Key': key,
                        's3Uri': f"s3://{s3_bucket}/{key}"
                    })

            if snapshots:
                break
        
        if not snapshots:
            # Fallback for legacy/mismatched prefixes: scan bucket and include dump archives.
            response_all = s3_client.list_objects_v2(Bucket=s3_bucket)
            if 'Contents' in response_all:
                for obj in response_all['Contents']:
                    key = obj['Key']
                    if key.endswith('.tar.gz') and '/dump-' in key:
                        filename = key.split('/')[-1]
                        snapshots.append({
                            'filename': filename,
                            'size': obj['Size'],
                            'sizeFormatted': format_bytes(obj['Size']),
                            'lastModified': obj['LastModified'].isoformat(),
                            'timestamp': filename.replace('dump-', '').replace('.tar.gz', ''),
                            's3Key': key,
                            's3Uri': f"s3://{s3_bucket}/{key}"
                        })

        # Sort by lastModified descending (newest first)
        snapshots.sort(key=lambda x: x['lastModified'], reverse=True)
        
        return snapshots
        
    except Exception as e:
        print(f"[COMMUNITY_BACKUP] Error listing snapshots: {e}")
        return []


def format_bytes(size_bytes: int) -> str:
    """Format bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def _resolve_snapshots_prefix(deployment: Dict[str, Any], s3_bucket: Optional[str] = None) -> str:
    """Return S3 key prefix that points to snapshot directory (without leading slash)."""
    s3_path = (deployment.get("s3Path") or "").strip()
    if s3_path.startswith("s3://"):
        without_scheme = s3_path.replace("s3://", "", 1)
        bucket_part, _, key_part = without_scheme.partition("/")
        if (not s3_bucket or bucket_part == s3_bucket) and key_part:
            return key_part.strip("/")

    s3_prefix = (deployment.get("s3Prefix") or "").strip("/")
    if s3_prefix.endswith("/snapshots") or s3_prefix.endswith("snapshots"):
        return s3_prefix
    return f"{s3_prefix}/snapshots" if s3_prefix else "snapshots"


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
        "retentionDays": deployment.get("backupRetentionDays", 7),
        "defaultS3Prefix": f"{namespace}/{deployment_id}"
    }

    restore_state = get_restore_state(tenant_id, deployment_id)
    if enabled and restore_state:
        result["restore"] = restore_state
    
    # Add type-specific fields
    if backup_type == "filesystem":
        result["target"] = deployment.get("backupTarget")
        result["snapshots"] = []  # Filesystem snapshots not listed via S3
    else:
        result["s3Bucket"] = deployment.get("s3Bucket")
        result["s3Prefix"] = deployment.get("s3Prefix")
        result["s3Region"] = deployment.get("s3Region")
        snapshots_prefix = _resolve_snapshots_prefix(deployment, deployment.get("s3Bucket"))
        result["s3Path"] = f"s3://{deployment.get('s3Bucket')}/{snapshots_prefix}"
        
        # List snapshots from S3
        try:
            result["snapshots"] = list_community_backup_snapshots(tenant_id, deployment_id)
        except Exception as e:
            print(f"[COMMUNITY_BACKUP] Warning: Could not list snapshots: {e}")
            result["snapshots"] = []
    
    return result


def get_restore_state(tenant_id: str, deployment_id: str) -> Optional[Dict[str, Any]]:
    """
    Return current restore state from metadata and live K8s job status (if available).
    """
    repo = get_repo()
    deployment = repo.get_deployment(tenant_id, deployment_id)
    if not deployment:
        return None

    last_job = deployment.get("lastRestoreJob")
    if not last_job:
        return None

    status = deployment.get("lastRestoreStatus", "UNKNOWN")
    state: Dict[str, Any] = {
        "jobName": last_job,
        "status": status,
        "snapshot": deployment.get("lastRestoreSnapshot"),
        "startedAt": deployment.get("lastRestoreStartedAt") or deployment.get("lastRestoreTime"),
        "completedAt": deployment.get("lastRestoreCompletedAt"),
        "error": deployment.get("lastRestoreError")
    }

    if status in {"RUNNING", "PENDING", "UNKNOWN"}:
        try:
            job_status = get_restore_job_status(tenant_id, deployment_id, last_job)
            state["status"] = job_status.get("status", status)
            state["active"] = job_status.get("active", 0)
            state["succeeded"] = job_status.get("succeeded", 0)
            state["failed"] = job_status.get("failed", 0)

            if job_status.get("status") == "COMPLETED":
                repo.update_deployment_metadata(
                    tenant_id=tenant_id,
                    deployment_id=deployment_id,
                    metadata={
                        "lastRestoreStatus": "COMPLETED",
                        "lastRestoreCompletedAt": datetime.now(timezone.utc).isoformat(),
                        "lastRestoreError": None
                    }
                )
                state["completedAt"] = datetime.now(timezone.utc).isoformat()
            elif job_status.get("status") == "FAILED":
                repo.update_deployment_metadata(
                    tenant_id=tenant_id,
                    deployment_id=deployment_id,
                    metadata={
                        "lastRestoreStatus": "FAILED",
                        "lastRestoreCompletedAt": datetime.now(timezone.utc).isoformat(),
                        "lastRestoreError": "Restore job failed"
                    }
                )
                state["error"] = "Restore job failed"
                state["completedAt"] = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            # If we cannot verify an in-progress job, mark it failed to avoid permanent lock.
            repo.update_deployment_metadata(
                tenant_id=tenant_id,
                deployment_id=deployment_id,
                metadata={
                    "lastRestoreStatus": "FAILED",
                    "lastRestoreCompletedAt": datetime.now(timezone.utc).isoformat(),
                    "lastRestoreError": f"Could not read restore job status: {str(e)}"
                }
            )
            state["status"] = "FAILED"
            state["error"] = f"Could not read restore job status: {str(e)}"

    return state


def is_restore_in_progress(tenant_id: str, deployment_id: str) -> bool:
    state = get_restore_state(tenant_id, deployment_id)
    if not state:
        return False
    return state.get("status") in {"RUNNING", "PENDING"}


def restore_community_backup(
    tenant_id: str,
    deployment_id: str,
    snapshot_filename: str,
    drop_existing: bool = True
) -> Dict[str, Any]:
    """
    Restore a Community MongoDB backup from snapshot.
    
    Creates a Kubernetes Job that:
    1. Downloads backup from S3/Filesystem
    2. Runs mongorestore to target deployment
    3. Optionally drops existing collections (--drop flag)
    
    Args:
        tenant_id: Tenant identifier
        deployment_id: Deployment identifier
        snapshot_filename: Snapshot file to restore (e.g., dump-20260215-120000.tar.gz)
        drop_existing: If True, drop existing collections before restore
    
    Returns:
        Dict with job name and status
    """
    repo = get_repo()
    k8s = get_k8s_client()
    
    # Get tenant
    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")
    
    if tenant.get("plan") != "community":
        raise ValueError("Restore is only available for Community plan deployments")
    
    namespace = tenant["namespace"]
    
    # Get deployment metadata
    deployment = repo.get_deployment(tenant_id, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment {deployment_id} not found")
    
    backup_type = deployment.get("backupType", "s3")
    if backup_type != "s3":
        raise ValueError("Restore is currently supported only for S3 backups")

    if is_restore_in_progress(tenant_id, deployment_id):
        current = get_restore_state(tenant_id, deployment_id) or {}
        job_name = current.get("jobName", "unknown")
        job_status = current.get("status", "RUNNING")
        raise ValueError(
            f"A restore job is already in progress for this deployment (job: {job_name}, status: {job_status}). "
            f"Cancel it first via: POST /tenants/{tenant_id}/deployments/{deployment_id}/community-backup/restore/{job_name}/cancel"
        )
    
    # Get external connection info (same as backup uses)
    from app.services import lifecycle_service
    
    try:
        connection_info = lifecycle_service.get_connection_info(tenant_id, deployment_id)
        external_uri = (
            connection_info.get("externalPrimaryUri")
            or connection_info.get("externalUri", "")
        )
        
        if not external_uri:
            raise ValueError("External connection URI not available")
        
        # Remove replicaSet parameter if present (we connect to single node for restore)
        if "?" in external_uri:
            base_uri = external_uri.split("?")[0]
        else:
            base_uri = external_uri
        
        # Get first host only for direct connection
        if "," in base_uri:
            # Extract just the first host
            parts = base_uri.replace("mongodb://", "").split(",")
            first_host = parts[0]
            base_uri = f"mongodb://{first_host}"
    except Exception as e:
        raise ValueError(f"Could not get external connection info: {e}")
    
    # Get backup credentials from secret
    backup_creds_secret_name = f"{deployment_id}-backup-credentials"
    stored_mongodb_uri = k8s.get_secret_data(namespace, backup_creds_secret_name, "MONGODB_URI")
    if not stored_mongodb_uri:
        raise ValueError(f"Backup credentials secret not found or invalid ({backup_creds_secret_name}). Is backup enabled?")

    stored_base = stored_mongodb_uri.split("?", 1)[0]
    if "@" not in stored_base:
        raise ValueError("Backup credentials URI does not contain auth info")

    auth_part = stored_base.replace("mongodb://", "").split("@", 1)[0]
    target_host = base_uri.replace("mongodb://", "").split("/", 1)[0]
    mongodb_uri = f"mongodb://{auth_part}@{target_host}/admin"
    
    # Ensure /admin database
    mongodb_uri = mongodb_uri.split("?", 1)[0]
    host_and_path = mongodb_uri.split("@", 1)[1] if "@" in mongodb_uri else mongodb_uri.replace("mongodb://", "")
    if "/" not in host_and_path:
        mongodb_uri = f"{mongodb_uri}/admin"
    elif not mongodb_uri.endswith("/admin"):
        mongodb_uri = mongodb_uri.rsplit("/", 1)[0] + "/admin"
    
    # Generate unique job name
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    job_name = f"{deployment_id}-restore-{timestamp}"
    
    # Build restore command based on backup type
    if backup_type == "s3":
        s3_bucket = deployment.get("s3Bucket")
        s3_region = deployment.get("s3Region", "us-east-1")
        snapshots_prefix = _resolve_snapshots_prefix(deployment, s3_bucket)
        raw_prefix = (deployment.get("s3Prefix") or "").strip("/")
        s3_key_candidates = [
            f"{snapshots_prefix}/{snapshot_filename}",
            f"{raw_prefix}/{snapshot_filename}" if raw_prefix else None,
            f"{raw_prefix}/snapshots/{snapshot_filename}" if raw_prefix else None,
            f"{raw_prefix}/snapshots/snapshots/{snapshot_filename}" if raw_prefix else None,
        ]
        s3_key_candidates = [k for k in s3_key_candidates if k]
        s3_key = s3_key_candidates[0]
        
        restore_command = [
            "/bin/sh",
            "-c",
            f"""
            set -e
            echo "[RESTORE] Starting restore from S3: s3://{s3_bucket}/{s3_key}"
            
            # Download from S3
            echo "[RESTORE] Downloading backup..."
            FOUND_KEY=""
            for KEY in {' '.join([f'"{k}"' for k in s3_key_candidates])}; do
              if aws s3 ls s3://{s3_bucket}/$KEY --region {s3_region} >/dev/null 2>&1; then
                FOUND_KEY="$KEY"
                break
              fi
            done

            if [ -z "$FOUND_KEY" ]; then
              echo "[RESTORE] Direct key lookup failed. Trying recursive bucket search for filename..."
              FOUND_KEY=$(aws s3 ls s3://{s3_bucket} --recursive --region {s3_region} | awk '$4 ~ /{snapshot_filename}$/ {{print $4; exit}}')
            fi

            if [ -z "$FOUND_KEY" ]; then
              echo "[RESTORE] ERROR: Snapshot not found in S3. Tried keys: {' | '.join(s3_key_candidates)}"
              exit 1
            fi

            echo "[RESTORE] Using key: $FOUND_KEY"
            aws s3 cp s3://{s3_bucket}/$FOUND_KEY /tmp/{snapshot_filename} --region {s3_region}
            
            # Extract
            echo "[RESTORE] Extracting backup..."
            cd /tmp
            tar -xzf {snapshot_filename}
            
            # Find dump directory
            DUMP_DIR=$(find /tmp -type d -name "dump-*" | head -n 1)
            if [ -z "$DUMP_DIR" ]; then
                DUMP_DIR="/tmp/dump"
            fi
            
            echo "[RESTORE] Found dump directory: $DUMP_DIR"
            
            # Restore to MongoDB
            echo "[RESTORE] Running mongorestore..."
            mongorestore \\
                --uri="{mongodb_uri}" \\
                {'--drop' if drop_existing else ''} \\
                --dir="$DUMP_DIR"
            
            echo "[RESTORE] Restore completed successfully!"
            """
        ]
        
        # Container for S3 restore (uses AWS CLI + mongodump image)
        container = client.V1Container(
            name="restore",
            image=config.COMMUNITY_BACKUP_MONGODUMP_IMAGE,
            command=restore_command,
            env=[
                client.V1EnvVar(name="AWS_ACCESS_KEY_ID", value_from=client.V1EnvVarSource(
                    secret_key_ref=client.V1SecretKeySelector(name="aws-backup-credentials", key="AWS_ACCESS_KEY_ID", optional=True)
                )),
                client.V1EnvVar(name="AWS_SECRET_ACCESS_KEY", value_from=client.V1EnvVarSource(
                    secret_key_ref=client.V1SecretKeySelector(name="aws-backup-credentials", key="AWS_SECRET_ACCESS_KEY", optional=True)
                )),
                client.V1EnvVar(name="AWS_DEFAULT_REGION", value_from=client.V1EnvVarSource(
                    secret_key_ref=client.V1SecretKeySelector(name="aws-backup-credentials", key="AWS_DEFAULT_REGION", optional=True)
                ))
            ],
            resources=client.V1ResourceRequirements(
                requests={"cpu": "500m", "memory": "512Mi"},
                limits={"cpu": "2", "memory": "2Gi"}
            )
        )
    else:
        # Filesystem restore
        backup_host = deployment.get("backupHost")
        backup_path = deployment.get("backupPath")
        sub_directory = deployment.get("backupSubDirectory", deployment_id)
        
        restore_command = [
            "/bin/sh",
            "-c",
            f"""
            set -e
            echo "[RESTORE] Starting restore from filesystem: {backup_host}:{backup_path}/{sub_directory}"
            
            # Restore directly from mounted filesystem
            BACKUP_FILE="/backup/{snapshot_filename}"
            
            if [ ! -f "$BACKUP_FILE" ]; then
                echo "[RESTORE] ERROR: Backup file not found: $BACKUP_FILE"
                exit 1
            fi
            
            echo "[RESTORE] Found backup file: $BACKUP_FILE"
            echo "[RESTORE] Running mongorestore..."
            
            mongorestore \\
                --uri="{mongodb_uri}" \\
                {'--drop' if drop_existing else ''} \\
                --gzip \\
                --archive="$BACKUP_FILE"
            
            echo "[RESTORE] Restore completed successfully!"
            """
        ]
        
        container = client.V1Container(
            name="restore",
            image=config.COMMUNITY_BACKUP_MONGODUMP_IMAGE,
            command=restore_command,
            volume_mounts=[
                client.V1VolumeMount(
                    name="backup-volume",
                    mount_path="/backup"
                )
            ],
            resources=client.V1ResourceRequirements(
                requests={"cpu": "500m", "memory": "512Mi"},
                limits={"cpu": "2", "memory": "2Gi"}
            )
        )
    
    # Create Job
    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(
            name=job_name,
            namespace=namespace,
            labels={
                "app": deployment_id,
                "component": "restore",
                "managed-by": "mdbaas-control-plane"
            }
        ),
        spec=client.V1JobSpec(
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={
                        "app": deployment_id,
                        "component": "restore"
                    }
                ),
                spec=client.V1PodSpec(
                    restart_policy="Never",
                    service_account_name=f"{deployment_id}-backup",
                    containers=[container],
                    volumes=[
                        client.V1Volume(
                            name="backup-volume",
                            nfs=client.V1NFSVolumeSource(
                                server=backup_host,
                                path=f"{backup_path}/{sub_directory}"
                            )
                        )
                    ] if backup_type == "filesystem" else []
                )
            ),
            backoff_limit=2,
            ttl_seconds_after_finished=86400  # Clean up after 24 hours
        )
    )
    
    # Create the Job
    try:
        k8s.batch_v1.create_namespaced_job(namespace, job)
        print(f"[RESTORE] Created restore job: {job_name}")
    except client.exceptions.ApiException as e:
        raise ValueError(f"Failed to create restore job: {e}")
    
    # Store restore metadata
    repo.update_deployment_metadata(
        tenant_id=tenant_id,
        deployment_id=deployment_id,
        metadata={
            "lastRestoreJob": job_name,
            "lastRestoreSnapshot": snapshot_filename,
            "lastRestoreTime": datetime.now(timezone.utc).isoformat(),
            "lastRestoreDropExisting": drop_existing,
            "lastRestoreStatus": "RUNNING",
            "lastRestoreStartedAt": datetime.now(timezone.utc).isoformat(),
            "lastRestoreCompletedAt": None,
            "lastRestoreError": None
        }
    )
    
    return {
        "message": "Restore job created successfully",
        "jobName": job_name,
        "namespace": namespace,
        "snapshot": snapshot_filename,
        "dropExisting": drop_existing,
        "status": "RUNNING",
        "checkStatusCommand": f"kubectl logs -f job/{job_name} -n {namespace}"
    }


def get_restore_job_status(tenant_id: str, deployment_id: str, job_name: str) -> Dict[str, Any]:
    """
    Get status of a restore job.
    
    Returns job status, logs, and completion info.
    """
    repo = get_repo()
    k8s = get_k8s_client()
    
    # Get tenant
    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")
    
    namespace = tenant["namespace"]
    
    # Get job status
    try:
        job = k8s.batch_v1.read_namespaced_job(job_name, namespace)
    except client.exceptions.ApiException as e:
        if e.status == 404:
            raise ValueError(f"Restore job {job_name} not found")
        raise
    
    # Parse job status
    status = job.status
    
    succeeded = status.succeeded or 0
    failed = status.failed or 0
    active = status.active or 0
    
    if succeeded > 0:
        job_status = "COMPLETED"
    elif failed > 0:
        job_status = "FAILED"
    elif active > 0:
        job_status = "RUNNING"
    else:
        job_status = "PENDING"
    
    # Get pod logs
    try:
        pods = k8s.core_v1.list_namespaced_pod(
            namespace=namespace,
            label_selector=f"job-name={job_name}"
        )
        
        logs = ""
        if pods.items:
            pod_name = pods.items[0].metadata.name
            try:
                logs = k8s.core_v1.read_namespaced_pod_log(pod_name, namespace, tail_lines=100)
            except:
                logs = "Logs not available yet"
        else:
            logs = "No pods found for job"
    except:
        logs = "Could not retrieve logs"
    
    result = {
        "jobName": job_name,
        "namespace": namespace,
        "status": job_status,
        "succeeded": succeeded,
        "failed": failed,
        "active": active,
        "startTime": status.start_time.isoformat() if status.start_time else None,
        "completionTime": status.completion_time.isoformat() if status.completion_time else None,
        "logs": logs
    }

    if job_status in {"COMPLETED", "FAILED"}:
        restore_error = None if job_status == "COMPLETED" else (
            f"Restore job failed. Check logs for details. Last logs: {logs[-500:]}"
        )
        updates = {
            "lastRestoreStatus": job_status,
            "lastRestoreCompletedAt": datetime.now(timezone.utc).isoformat(),
            "lastRestoreError": restore_error
        }
        repo.update_deployment_metadata(
            tenant_id=tenant_id,
            deployment_id=deployment_id,
            metadata=updates
        )

    return result


def cancel_restore_job(tenant_id: str, deployment_id: str, job_name: str) -> Dict[str, Any]:
    """Cancel (delete) an active restore job and clear restore lock state."""
    repo = get_repo()
    k8s = get_k8s_client()

    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    namespace = tenant["namespace"]

    try:
        k8s.batch_v1.delete_namespaced_job(
            name=job_name,
            namespace=namespace,
            propagation_policy="Foreground"
        )
    except client.exceptions.ApiException as e:
        if e.status != 404:
            raise ValueError(f"Failed to cancel restore job: {e}")

    repo.update_deployment_metadata(
        tenant_id=tenant_id,
        deployment_id=deployment_id,
        metadata={
            "lastRestoreStatus": "CANCELLED",
            "lastRestoreCompletedAt": datetime.now(timezone.utc).isoformat(),
            "lastRestoreError": "Restore job was cancelled by user"
        }
    )

    return {
        "message": "Restore job cancelled",
        "jobName": job_name,
        "status": "CANCELLED"
    }
