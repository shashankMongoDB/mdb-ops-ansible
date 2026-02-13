import secrets
import string
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from kubernetes import client

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


def create_backup_mongodb_user(namespace: str, deployment_id: str) -> str:
    """
    Create a MongoDB backup user via MongoDBUser CRD.
    
    Returns the generated password.
    """
    k8s = get_k8s_client()
    
    # Generate password
    backup_password = generate_password(24)
    
    secret_name = f"{deployment_id}-backupuser-password"
    user_name = f"backupuser-{deployment_id}"
    
    # Create password secret
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
            # Already exists, update it
            k8s.core_v1.patch_namespaced_secret(secret_name, namespace, secret)
            print(f"[COMMUNITY_BACKUP] Updated existing secret: {secret_name}")
        else:
            raise
    
    # Create MongoDBUser CRD
    mongodb_user_cr = {
        "apiVersion": "mongodb.com/v1",
        "kind": "MongoDBUser",
        "metadata": {
            "name": user_name,
            "namespace": namespace,
            "labels": {
                "app": "community-mongodb-backup",
                "deployment": deployment_id
            }
        },
        "spec": {
            "username": "backupuser",
            "db": "admin",
            "mongodbResourceRef": {
                "name": deployment_id
            },
            "passwordSecretKeyRef": {
                "name": secret_name,
                "key": "password"
            },
            "roles": [
                {"name": "backup", "db": "admin"},
                {"name": "clusterMonitor", "db": "admin"},
                {"name": "readAnyDatabase", "db": "admin"}
            ]
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
        print(f"[COMMUNITY_BACKUP] Created MongoDBUser: {user_name}")
    except client.exceptions.ApiException as e:
        if e.status == 409:
            # Already exists, patch it
            k8s.custom_objects.patch_namespaced_custom_object(
                group="mongodb.com",
                version="v1",
                namespace=namespace,
                plural="mongodbusers",
                name=user_name,
                body=mongodb_user_cr
            )
            print(f"[COMMUNITY_BACKUP] Updated existing MongoDBUser: {user_name}")
        else:
            raise
    
    # Wait for MongoDBUser to be reconciled
    print(f"[COMMUNITY_BACKUP] Waiting for MongoDBUser to be reconciled...")
    max_retries = 30
    for retry in range(max_retries):
        try:
            user_obj = k8s.custom_objects.get_namespaced_custom_object(
                group="mongodb.com",
                version="v1",
                namespace=namespace,
                plural="mongodbusers",
                name=user_name
            )
            phase = user_obj.get("status", {}).get("phase", "")
            if phase == "Updated":
                print(f"[COMMUNITY_BACKUP] MongoDBUser reconciled (phase: {phase})")
                break
        except client.exceptions.ApiException:
            pass
        
        if retry < max_retries - 1:
            time.sleep(5)
    
    return backup_password


def create_backup_credentials_secret(
    namespace: str,
    deployment_id: str,
    mongodb_hosts: str,
    rs_name: str,
    password: str
) -> None:
    """
    Create Secret with MongoDB connection URI for backup.
    """
    k8s = get_k8s_client()
    
    # Build MongoDB URI
    mongodb_uri = f"mongodb://backupuser:{password}@{mongodb_hosts}/?replicaSet={rs_name}&authSource=admin&tls=true&tlsInsecure=true"
    
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


def deploy_backup_cronjob(namespace: str, deployment_id: str) -> None:
    """
    Deploy backup CronJob and supporting resources.
    """
    k8s = get_k8s_client()
    
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
    s3_path = f"s3://{config.COMMUNITY_BACKUP_S3_BUCKET}/{config.COMMUNITY_BACKUP_S3_PREFIX}/{deployment_id}/snapshots"
    
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
            "schedule": config.COMMUNITY_BACKUP_SCHEDULE,
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
                                            aws s3 cp "$file" "{s3_path}/$file" --region {config.COMMUNITY_BACKUP_S3_REGION}
                                            echo "Uploaded: $file"
                                        done
                                        
                                        # Cleanup old backups
                                        cutoff_date=$(date -d "{config.COMMUNITY_BACKUP_RETENTION_DAYS} days ago" +%Y%m%d || date -v-{config.COMMUNITY_BACKUP_RETENTION_DAYS}d +%Y%m%d)
                                        aws s3 ls "{s3_path}/" --region {config.COMMUNITY_BACKUP_S3_REGION} | while read -r line; do
                                            file=$(echo "$line" | awk '{{print $4}}')
                                            file_date=$(echo "$file" | grep -oP 'dump-\\K[0-9]{{8}}' || echo "")
                                            if [[ -n "$file_date" && "$file_date" -lt "$cutoff_date" ]]; then
                                                aws s3 rm "{s3_path}/$file" --region {config.COMMUNITY_BACKUP_S3_REGION}
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


def enable_community_backup(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Enable Community MongoDB backup for a deployment.
    
    Orchestrates:
    1. Discover connection
    2. Create backup user
    3. Create credentials secret
    4. Deploy CronJob
    
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
    
    print(f"[COMMUNITY_BACKUP] Enabling backup for {deployment_id} in {namespace}")
    
    # Step 1: Discover connection
    conn_info = discover_mongodb_connection(namespace, deployment_id)
    
    # Step 2: Create backup user
    backup_password = create_backup_mongodb_user(namespace, deployment_id)
    
    # Step 3: Create credentials secret
    create_backup_credentials_secret(
        namespace,
        deployment_id,
        conn_info["hosts"],
        conn_info["rsName"],
        backup_password
    )
    
    # Step 4: Deploy CronJob
    deploy_backup_cronjob(namespace, deployment_id)
    
    s3_path = f"s3://{config.COMMUNITY_BACKUP_S3_BUCKET}/{config.COMMUNITY_BACKUP_S3_PREFIX}/{deployment_id}/snapshots/"
    
    return {
        "enabled": True,
        "schedule": config.COMMUNITY_BACKUP_SCHEDULE,
        "s3Path": s3_path,
        "retentionDays": config.COMMUNITY_BACKUP_RETENTION_DAYS
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
    cronjob_name = f"{deployment_id}-backup"
    
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
    
    Returns status including schedule, last backup time, S3 path.
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
    cronjob_name = f"{deployment_id}-backup"
    
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
                "status": "NOT_CONFIGURED",
                "schedule": None,
                "lastSuccessfulTime": None,
                "s3Path": None
            }
        raise
    
    # Parse CronJob status
    spec = cronjob.get("spec", {})
    status = cronjob.get("status", {})
    
    enabled = not spec.get("suspend", False)
    schedule = spec.get("schedule", "")
    last_successful_time = status.get("lastSuccessfulTime")
    
    s3_path = f"s3://{config.COMMUNITY_BACKUP_S3_BUCKET}/{config.COMMUNITY_BACKUP_S3_PREFIX}/{deployment_id}/snapshots/"
    
    return {
        "enabled": enabled,
        "status": "ACTIVE" if enabled else "SUSPENDED",
        "schedule": schedule,
        "lastSuccessfulTime": last_successful_time,
        "s3Path": s3_path,
        "retentionDays": config.COMMUNITY_BACKUP_RETENTION_DAYS
    }
