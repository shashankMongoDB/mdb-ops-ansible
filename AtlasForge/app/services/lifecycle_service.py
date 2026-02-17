from typing import Dict, Any
import logging
import re
from app.services.mongo_repo import get_repo
from app.services.k8s_client import get_k8s_client
from app.services import monitoring_service
from app.services import deployments_community_service
from app.services import backup_service

logger = logging.getLogger(__name__)


def _normalize_version(version: str) -> str:
    if not version:
        return ""
    normalized = str(version).strip()
    # Remove image digest suffix if present
    if "@" in normalized:
        normalized = normalized.split("@", 1)[0]
    # Normalize enterprise suffix for comparisons
    normalized = normalized.replace("-ent", "")
    # Extract semantic version if image tags include distro/build suffixes (e.g. 8.0.7-ubi8)
    match = re.search(r"(\d+\.\d+\.\d+)", normalized)
    if match:
        normalized = match.group(1)
    return normalized


def get_connection_info(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Get connection information for a MongoDB deployment.
    
    Automatically creates NodePort service for external access.
    Returns both internal (K8s) and external (VPC) connection URIs.
    
    Supports both enterprise and community deployments.
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
    
    # Check if deployment is shutdown
    deployment_status = deployment.get("status", "running")
    if deployment_status == "shutdown":
        return {
            "namespace": namespace,
            "deploymentId": deployment_id,
            "replicaSet": deployment_id,  # Use deployment_id as default
            "status": "shutdown",
            "message": "Deployment is currently shutdown. Start the deployment to get connection info.",
            "internalUri": "",  # Empty string instead of None
            "externalHostPort": None,
            "externalUri": None
        }

    # Get CR based on plan to read replica set name
    if plan == "community":
        cr = k8s.get_mongodb_community_cr(namespace, deployment_id)
    else:
        cr = k8s.get_mongodb_enterprise_cr(namespace, deployment_id)
    
    if not cr:
        # Check if it's shutdown (CR was deleted)
        if deployment_status == "shutdown":
            return {
                "namespace": namespace,
                "deploymentId": deployment_id,
                "replicaSet": deployment_id,  # Use deployment_id as default
                "status": "shutdown",
                "message": "Deployment is currently shutdown. Start the deployment to restore connection.",
                "internalUri": "",  # Empty string instead of None
                "externalHostPort": None,
                "externalUri": None
            }
        raise ValueError(f"MongoDB CR {deployment_id} not found in namespace {namespace}")

    # Get replica set name from CR
    replica_set_name = deployment_id  # Default
    if plan == "community":
        # MongoDBCommunity CR
        replica_set_name = cr.get("spec", {}).get("replicaSet", deployment_id)
    else:
        # MongoDB Enterprise CR
        replica_set_name = cr.get("metadata", {}).get("name", deployment_id)

    # Internal service (ClusterIP)
    internal_service = f"{deployment_id}-svc"
    internal_host_port = f"{internal_service}.{namespace}.svc.cluster.local:27017"
    internal_uri = f"mongodb://{internal_host_port}"
    
    # Get target state from DB (what user requested)
    target_version = deployment.get("lastRequestedSpec", {}).get("mongoVersion", "") or deployment.get("mongoVersion", "") or ""
    target_replicas = (
        deployment.get("lastRequestedSpec", {}).get("members")
        or deployment.get("lastRequestedSpec", {}).get("replicas")
        or deployment.get("members")
        or 3
    )
    
    # Get actual state from CR (what Kubernetes has)
    try:
        if plan == "community":
            cr_version = cr.get("spec", {}).get("version", "") or ""
            cr_replicas = cr.get("spec", {}).get("members", 3) or 3
            # Get CR status
            cr_status = cr.get("status", {})
            cr_phase = cr_status.get("phase", "Unknown")
            cr_message = cr_status.get("message", "")
            cr_actual_version = cr_status.get("version", cr_version)  # Version from status
        else:
            cr_version = cr.get("spec", {}).get("version", "") or ""
            cr_replicas = cr.get("spec", {}).get("members", 3) or 3
            cr_status = cr.get("status", {})
            cr_phase = cr_status.get("phase", "Unknown")
            cr_message = cr_status.get("message", "")
            cr_actual_version = cr_status.get("mongoDbVersion", cr_version)  # Enterprise uses different field
    except Exception as e:
        logger.warning(f"Error reading CR spec: {e}")
        cr_version = target_version
        cr_replicas = target_replicas
        cr_phase = "Unknown"
        cr_message = ""
        cr_actual_version = cr_version
    
    # Get pod/replica status
    try:
        # Get pods for the StatefulSet
        pods = k8s.list_pods_for_statefulset(namespace, deployment_id)
    except Exception as e:
        logger.warning(f"Failed to get pods for {namespace}/{deployment_id}: {e}")
        pods = []
    
    replicas = []
    ready_count = 0
    
    for pod in pods:
        try:
            pod_name = pod.metadata.name if pod.metadata else "unknown"
            pod_phase = pod.status.phase if pod.status and pod.status.phase else "Unknown"
            is_ready = False
            
            # Check if pod is ready
            if pod.status and hasattr(pod.status, 'conditions') and pod.status.conditions:
                for condition in pod.status.conditions:
                    if hasattr(condition, 'type') and condition.type == "Ready" and \
                       hasattr(condition, 'status') and condition.status == "True":
                        is_ready = True
                        ready_count += 1
                        break
            
            # Get MongoDB version from pod (from image or container)
            mongo_version = cr_version or "unknown"  # Default to CR version
            if pod.spec and hasattr(pod.spec, 'containers') and pod.spec.containers:
                for container in pod.spec.containers:
                    if hasattr(container, 'image') and container.image and "mongo" in container.image.lower():
                        # Extract version from image tag
                        image_parts = container.image.split(":")
                        if len(image_parts) > 1:
                            mongo_version = image_parts[1]
                        break
            
            replicas.append({
                "name": pod_name,
                "version": mongo_version,
                "status": pod_phase,
                "ready": is_ready
            })
        except Exception as e:
            logger.warning(f"Error processing pod in {namespace}/{deployment_id}: {e}")
            continue
    
    # Use target replicas from CR spec as source of truth
    total_replicas = cr_replicas or target_replicas or len(replicas)
    actual_pod_count = len(replicas)
    
    # Detect operation type and calculate progress
    operation = "running"
    progress = 100
    operation_message = "All replicas running"
    
    try:
        # Check CR phase first - only force failed state
        if cr_phase == "Failed":
            operation = "failed"
            progress = 0
            operation_message = cr_message or f"CR Phase: {cr_phase}"
        
        # Detect upgrade signal from CR/pods
        else:
            normalized_cr_version = _normalize_version(cr_version)
            normalized_cr_actual_version = _normalize_version(cr_actual_version)
            normalized_versions = [
                _normalize_version(r["version"])
                for r in replicas
                if r["version"] and r["version"] != "unknown"
            ]
            normalized_target_version = _normalize_version(target_version)
            unique_versions = set([v for v in normalized_versions if v])
            upgrade_signal = False
            target_version_signal = False
            fully_converged = (
                actual_pod_count == total_replicas
                and ready_count == total_replicas
                and (
                    not unique_versions
                    or (
                        normalized_cr_version
                        and unique_versions == {normalized_cr_version}
                        and (not normalized_target_version or normalized_target_version == normalized_cr_version)
                    )
                )
            )

            if normalized_cr_version and normalized_cr_actual_version and normalized_cr_version != normalized_cr_actual_version:
                upgrade_signal = True
                operation_message = f"Operator upgrading from {cr_actual_version} to {cr_version}"
            elif len(unique_versions) > 1:
                upgrade_signal = True
                operation_message = f"Upgrading pods from {min(unique_versions)} to {max(unique_versions)}"
            elif normalized_cr_version and unique_versions and any(v != normalized_cr_version for v in unique_versions):
                upgrade_signal = True
                operation_message = f"Reconciling pod versions to {cr_version}"

            if normalized_target_version:
                if normalized_cr_version and normalized_target_version != normalized_cr_version:
                    target_version_signal = True
                elif normalized_cr_actual_version and normalized_target_version != normalized_cr_actual_version:
                    target_version_signal = True
                elif unique_versions and any(v != normalized_target_version for v in unique_versions):
                    target_version_signal = True

            if target_version_signal:
                upgrade_signal = True

            if upgrade_signal and not fully_converged:
                operation = "upgrading"
                version_goal = normalized_target_version or normalized_cr_version
                upgraded_count = sum(
                    1 for r in replicas
                    if r["ready"] and version_goal and _normalize_version(r["version"]) == version_goal
                )
                progress = int((upgraded_count / total_replicas) * 100) if total_replicas > 0 else 0
                display_version = target_version or cr_version or "target"
                operation_message = (
                    f"Upgrading version in progress: {upgraded_count}/{total_replicas} replicas on {display_version}. "
                    f"Existing connections remain available."
                )

            # Check for scaling (actual pod count vs target)
            elif actual_pod_count != total_replicas:
                operation = "scaling"
                if actual_pod_count < total_replicas:
                    # Scaling up - base progress on actual pods created
                    progress = int((actual_pod_count / total_replicas) * 100) if total_replicas > 0 else 0
                    operation_message = f"Scaling up in progress: {ready_count}/{total_replicas} replicas ready. Existing connections remain available."
                else:
                    # Scaling down
                    progress = int((total_replicas / actual_pod_count) * 100) if actual_pod_count > 0 else 100
                    operation_message = "Scaling down in progress. Existing connections remain available."
            
            # Check for stabilizing (not all replicas ready yet)
            elif ready_count < total_replicas:
                operation = "stabilizing"
                progress = int((ready_count / total_replicas) * 100) if total_replicas > 0 else 0
                operation_message = f"Stabilizing after scaling: {ready_count}/{total_replicas} replicas ready. Existing connections remain available."

            # If fully converged, always report running (clears stale upgrade/scaling labels)
            if fully_converged:
                operation = "running"
                progress = 100
                operation_message = "All replicas running"
    except Exception as e:
        logger.warning(f"Error detecting operation status: {e}")
        # Keep defaults: running, 100%, "All replicas running"
    
    # Ensure external NodePort service exists
    try:
        external_service_name, node_port = k8s.ensure_external_service(namespace, deployment_id)
        worker_node_ip = k8s.get_worker_node_ip()
        
        external_host_port = f"{worker_node_ip}:{node_port}"
        external_uri = f"mongodb://{external_host_port}"
        
        return {
            "namespace": namespace,
            "deploymentId": deployment_id,
            "replicaSet": replica_set_name,
            "internalUri": internal_uri,
            "externalHostPort": external_host_port,
            "externalUri": external_uri,
            "operation": operation,
            "progress": progress,
            "operationMessage": operation_message,
            "targetVersion": target_version,
            "targetReplicas": total_replicas,
            "currentVersion": cr_version,
            "currentReplicas": cr_replicas,
            "readyReplicas": ready_count,
            "totalReplicas": total_replicas,
            "replicas": replicas,
            "crPhase": cr_phase,
            "crMessage": cr_message,
            "crActualVersion": cr_actual_version
        }
        
    except Exception as e:
        # Fallback if external service creation fails
        return {
            "namespace": namespace,
            "deploymentId": deployment_id,
            "replicaSet": replica_set_name,
            "internalUri": internal_uri,
            "externalHostPort": None,
            "externalUri": None,
            "operation": operation,
            "progress": progress,
            "operationMessage": operation_message,
            "targetVersion": target_version,
            "targetReplicas": total_replicas,
            "currentVersion": cr_version,
            "currentReplicas": cr_replicas,
            "readyReplicas": ready_count,
            "totalReplicas": total_replicas,
            "replicas": replicas,
            "crPhase": cr_phase,
            "crMessage": cr_message,
            "crActualVersion": cr_actual_version,
            "error": f"Failed to create external service: {str(e)}"
        }


def sync_deployment_state(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Sync deployment state in control plane DB with actual Kubernetes CR.
    
    Fixes state drift by reading actual CR and updating DB to match.
    Returns the synced state and any changes detected.
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

    # Get actual CR
    if plan == "community":
        cr = k8s.get_mongodb_community_cr(namespace, deployment_id)
        if not cr:
            raise ValueError(f"MongoDBCommunity CR {deployment_id} not found in namespace {namespace}")
        
        actual_version = cr.get("spec", {}).get("version", "unknown")
        actual_replicas = cr.get("spec", {}).get("members", 3)
    else:
        cr = k8s.get_mongodb_enterprise_cr(namespace, deployment_id)
        if not cr:
            raise ValueError(f"MongoDB CR {deployment_id} not found in namespace {namespace}")
        
        actual_version = cr.get("spec", {}).get("version", "unknown")
        actual_replicas = cr.get("spec", {}).get("members", 3)

    # Get current DB state
    db_version = deployment.get("lastRequestedSpec", {}).get("mongoVersion", "unknown")
    db_replicas = deployment.get("lastRequestedSpec", {}).get("replicas", 3)

    # Detect drift
    changes = []
    if actual_version != db_version:
        changes.append(f"version: {db_version} → {actual_version}")
    if actual_replicas != db_replicas:
        changes.append(f"replicas: {db_replicas} → {actual_replicas}")

    # Update DB to match CR
    if changes:
        repo.update_deployment(tenant_id, deployment_id, {
            "lastRequestedSpec.mongoVersion": actual_version,
            "lastRequestedSpec.replicas": actual_replicas
        })

    return {
        "tenantId": tenant_id,
        "deploymentId": deployment_id,
        "synced": True,
        "driftDetected": len(changes) > 0,
        "changes": changes,
        "currentState": {
            "version": actual_version,
            "replicas": actual_replicas
        }
    }


def update_backup_setting(tenant_id: str, deployment_id: str, enabled: bool) -> Dict[str, Any]:
    """
    Enable or disable backup for a MongoDB deployment by patching the CR.
    Only supported for enterprise deployments with Ops Manager.
    """
    repo = get_repo()
    k8s = get_k8s_client()

    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    # Check plan - backup only supported for enterprise
    plan = tenant.get("plan", "enterprise")
    if plan == "community":
        raise ValueError("Backup is not supported for community deployments")

    deployment = repo.get_deployment(tenant_id, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment {deployment_id} not found for tenant {tenant_id}")

    namespace = tenant["namespace"]

    cr = k8s.get_mongodb_cr(namespace, deployment_id)
    if not cr:
        raise ValueError(f"MongoDB CR {deployment_id} not found in namespace {namespace}")

    if enabled:
        patch = {
            "spec": {
                "backup": {
                    "mode": "enabled"
                }
            }
        }
    else:
        patch = {
            "spec": {
                "backup": None
            }
        }

    k8s.patch_mongodb_cr(namespace, deployment_id, patch)

    repo.update_deployment(tenant_id, deployment_id, {
        "lastRequestedSpec.backupEnabled": enabled
    })

    # If enabling backup, ensure backup config + policy in Ops Manager
    if enabled:
        print(f"[LIFECYCLE] Backup enabled, ensuring OM config for {tenant_id}/{deployment_id}")
        try:
            backup_service.ensure_backup_config_and_policy(tenant_id, deployment_id)
        except Exception as e:
            # Don't fail the PATCH if OM is not ready - just log
            print(f"[LIFECYCLE] Could not ensure backup config (OM may not be ready): {str(e)}")

    return {
        "tenantId": tenant_id,
        "deploymentId": deployment_id,
        "backupEnabled": enabled
    }


def update_monitoring_setting(tenant_id: str, deployment_id: str, prometheus_enabled: bool) -> Dict[str, Any]:
    """
    Enable or disable monitoring (Prometheus) for a MongoDB deployment.
    Delegates to existing Prometheus integration.
    """
    if prometheus_enabled:
        result = monitoring_service.enable_prometheus_metrics(tenant_id, deployment_id)
    else:
        result = monitoring_service.disable_prometheus_metrics(tenant_id, deployment_id)

    repo = get_repo()
    repo.update_deployment(tenant_id, deployment_id, {
        "lastRequestedSpec.prometheusEnabled": prometheus_enabled
    })

    return {
        "tenantId": tenant_id,
        "deploymentId": deployment_id,
        "prometheusEnabled": prometheus_enabled
    }


def shutdown_deployment(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Shutdown a deployment by scaling the StatefulSet to 0 replicas.
    Stores the previous replica count for later restoration.
    Supports both enterprise and community deployments.
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
    
    # Route to community service if needed
    if plan == "community":
        result = deployments_community_service.shutdown_deployment_community(namespace, deployment_id)
        # Store shutdown info (CR spec) and mark as shutdown in DB
        repo.update_deployment(tenant_id, deployment_id, {
            "lastRequestedSpec.shutdownInfo": result.get("shutdownInfo", {}),
            "status": "shutdown"
        })
        return {
            "tenantId": tenant_id,
            "deploymentId": deployment_id,
            "action": "shutdown",
            "previousReplicas": result["previousReplicas"],
            "currentReplicas": 0
        }
    
    # Enterprise logic continues below

    cr = k8s.get_mongodb_cr(namespace, deployment_id)
    if not cr:
        raise ValueError(f"MongoDB CR {deployment_id} not found in namespace {namespace}")

    # Determine deployment type from CR
    deployment_type = deployment.get("type", "ReplicaSet")
    
    # Handle different deployment types
    if deployment_type == "ShardedCluster":
        # For ShardedCluster, the safest way to shutdown is to:
        # 1. Save the MongoDB CR spec
        # 2. Delete the MongoDB CR (this stops operator reconciliation)
        # 3. Scale down all StatefulSets
        # 4. Delete all pods
        
        # Get current CR spec
        spec = cr.get("spec", {})
        metadata = cr.get("metadata", {})
        
        # Store FULL CR for recreation on start
        # MongoDB Enterprise Operator uses 'shardCount' field, not 'shardPodSpec'
        shard_count = spec.get("shardCount", deployment.get("shardCount", 2))
        
        shutdown_info = {
            "cr_spec": spec,  # Full CR spec
            "cr_metadata_labels": metadata.get("labels", {}),
            "cr_metadata_annotations": metadata.get("annotations", {}),
            "shard_count": shard_count
        }
        
        print(f"[LIFECYCLE] Starting shutdown for ShardedCluster {deployment_id}")
        print(f"[LIFECYCLE] Shard count from CR: {shard_count}")
        print(f"[LIFECYCLE] mongodsPerShardCount: {spec.get('mongodsPerShardCount')}")
        print(f"[LIFECYCLE] mongosCount: {spec.get('mongosCount')}")
        print(f"[LIFECYCLE] configSrvCount: {spec.get('configSrvCount')}")
        
        # Step 1: Delete the MongoDB CR
        # This stops the operator from reconciling
        try:
            k8s.custom_objects.delete_namespaced_custom_object(
                group="mongodb.com",
                version="v1",
                namespace=namespace,
                plural="mongodb",
                name=deployment_id
            )
            print(f"[LIFECYCLE] Deleted MongoDB CR {deployment_id}")
        except Exception as e:
            print(f"[LIFECYCLE] Error deleting MongoDB CR: {e}")
            raise ValueError(f"Failed to delete MongoDB CR: {e}")
        
        # Step 2: Scale all StatefulSets to 0 and delete pods
        # Now that CR is gone, operator won't recreate pods
        import time
        time.sleep(2)  # Give operator time to process CR deletion
        
        for i in range(shard_count):
            shard_name = f"{deployment_id}-shard-{i}"
            try:
                # Get all pods first
                pods = k8s.core_v1.list_namespaced_pod(
                    namespace=namespace,
                    label_selector=f"app={shard_name}-svc"
                )
                
                print(f"[LIFECYCLE] Found {len(pods.items)} pods for {shard_name}")
                
                # Force delete all pods
                for pod in pods.items:
                    try:
                        k8s.delete_pod(namespace, pod.metadata.name, grace_period=0)
                        print(f"[LIFECYCLE] Force deleted pod {pod.metadata.name}")
                    except Exception as pod_e:
                        print(f"[LIFECYCLE] Could not delete pod {pod.metadata.name}: {pod_e}")
                
                # Scale StatefulSet to 0
                k8s.patch_statefulset_replicas(namespace, shard_name, 0)
                print(f"[LIFECYCLE] Scaled {shard_name} to 0")
            except Exception as e:
                print(f"[LIFECYCLE] Warning: Could not shutdown shard {shard_name}: {e}")
        
        # Shutdown config servers
        configsvr_name = f"{deployment_id}-configsvr"
        try:
            # Get all config server pods
            pods = k8s.core_v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=f"app={configsvr_name}-svc"
            )
            
            print(f"[LIFECYCLE] Found {len(pods.items)} pods for {configsvr_name}")
            
            # Force delete all pods
            for pod in pods.items:
                try:
                    k8s.delete_pod(namespace, pod.metadata.name, grace_period=0)
                    print(f"[LIFECYCLE] Force deleted pod {pod.metadata.name}")
                except Exception as pod_e:
                    print(f"[LIFECYCLE] Could not delete pod {pod.metadata.name}: {pod_e}")
            
            # Scale StatefulSet to 0
            k8s.patch_statefulset_replicas(namespace, configsvr_name, 0)
            print(f"[LIFECYCLE] Scaled {configsvr_name} to 0")
        except Exception as e:
            print(f"[LIFECYCLE] Warning: Could not shutdown config servers: {e}")
        
        # Shutdown mongos pods
        try:
            # Try multiple label selectors for mongos
            pods = k8s.core_v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=f"app.kubernetes.io/instance={deployment_id}"
            )
            
            # Filter to only mongos pods
            mongos_pods = [p for p in pods.items if 'mongos' in p.metadata.name]
            
            print(f"[LIFECYCLE] Found {len(mongos_pods)} mongos pods")
            
            # Force delete all mongos pods
            for pod in mongos_pods:
                try:
                    k8s.delete_pod(namespace, pod.metadata.name, grace_period=0)
                    print(f"[LIFECYCLE] Force deleted mongos pod {pod.metadata.name}")
                except Exception as pod_e:
                    print(f"[LIFECYCLE] Could not delete pod {pod.metadata.name}: {pod_e}")
        except Exception as e:
            print(f"[LIFECYCLE] Warning: Could not shutdown mongos: {e}")
        
        # Store shutdown info and mark as shutdown
        repo.update_deployment(tenant_id, deployment_id, {
            "lastRequestedSpec.shutdownInfo": shutdown_info,
            "status": "shutdown"
        })
        
        print(f"[LIFECYCLE] Shutdown complete for {deployment_id}")
        
        # Calculate total replicas from CR spec
        total_replicas = (shard_count * spec.get("mongodsPerShardCount", 3) + 
                         spec.get("mongosCount", 2) + 
                         spec.get("configSrvCount", 3))
        
        return {
            "tenantId": tenant_id,
            "deploymentId": deployment_id,
            "action": "shutdown",
            "previousReplicas": total_replicas,
            "currentReplicas": 0,
            "message": f"Shutdown complete - CR deleted, all pods terminated"
        }
    
    elif deployment_type == "Standalone":
        # Standalone uses Deployment, not StatefulSet
        deployment_name = f"{deployment_id}-db"
        try:
            deployment_obj = k8s.apps_v1.read_namespaced_deployment(deployment_name, namespace)
            previous_replicas = deployment_obj.spec.replicas
            k8s.apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body={"spec": {"replicas": 0}}
            )
        except Exception as e:
            # Try StatefulSet as fallback
            try:
                sts = k8s.get_statefulset(namespace, deployment_id)
                if sts:
                    previous_replicas = sts.spec.replicas
                    k8s.patch_statefulset_replicas(namespace, deployment_id, 0)
            except:
                raise ValueError(f"Could not find Deployment or StatefulSet for {deployment_id}")
        
        repo.update_deployment(tenant_id, deployment_id, {
            "lastRequestedSpec.membersBeforeShutdown": previous_replicas
        })
        
        return {
            "tenantId": tenant_id,
            "deploymentId": deployment_id,
            "action": "shutdown",
            "type": "Standalone",
            "previousReplicas": previous_replicas,
            "currentReplicas": 0
        }
    
    else:
        # ReplicaSet (default)
        # Use same strategy as ShardedCluster: delete CR and force delete pods
        spec = cr.get("spec", {})
        metadata = cr.get("metadata", {})
        previous_replicas = spec.get("members", 3)
        
        # Store full CR spec for recreation
        shutdown_info = {
            "cr_spec": spec,
            "cr_metadata_labels": metadata.get("labels", {}),
            "cr_metadata_annotations": metadata.get("annotations", {}),
            "previous_replicas": previous_replicas
        }
        
        print(f"[LIFECYCLE] Starting shutdown for ReplicaSet {deployment_id}")
        
        # Delete the MongoDB CR
        try:
            k8s.custom_objects.delete_namespaced_custom_object(
                group="mongodb.com",
                version="v1",
                namespace=namespace,
                plural="mongodb",
                name=deployment_id
            )
            print(f"[LIFECYCLE] Deleted MongoDB CR {deployment_id}")
        except Exception as e:
            print(f"[LIFECYCLE] Error deleting MongoDB CR: {e}")
            raise ValueError(f"Failed to delete MongoDB CR: {e}")
        
        # Wait for operator to process deletion
        import time
        time.sleep(2)
        
        # Delete all pods
        try:
            pods = k8s.core_v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=f"app={deployment_id}-svc"
            )
            
            print(f"[LIFECYCLE] Found {len(pods.items)} pods to delete")
            
            for pod in pods.items:
                try:
                    k8s.delete_pod(namespace, pod.metadata.name, grace_period=0)
                    print(f"[LIFECYCLE] Force deleted pod {pod.metadata.name}")
                except Exception as pod_e:
                    print(f"[LIFECYCLE] Could not delete pod {pod.metadata.name}: {pod_e}")
            
            # Scale StatefulSet to 0
            k8s.patch_statefulset_replicas(namespace, deployment_id, 0)
            print(f"[LIFECYCLE] Scaled StatefulSet {deployment_id} to 0")
        except Exception as e:
            print(f"[LIFECYCLE] Warning: Error during pod deletion: {e}")

        repo.update_deployment(tenant_id, deployment_id, {
            "lastRequestedSpec.shutdownInfo": shutdown_info,
            "status": "shutdown"
        })

        return {
            "tenantId": tenant_id,
            "deploymentId": deployment_id,
            "action": "shutdown",
            "previousReplicas": previous_replicas,
            "currentReplicas": 0
        }


def start_deployment(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Start a previously shutdown deployment by scaling the StatefulSet back up.
    Supports both enterprise and community deployments.
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
    
    # Get shutdown info (CR spec saved during shutdown)
    shutdown_info = deployment.get("lastRequestedSpec", {}).get("shutdownInfo", {})
    
    # Route to community service if needed
    if plan == "community":
        result = deployments_community_service.start_deployment_community(namespace, deployment_id, shutdown_info)
        
        # Clear shutdown info and mark as running
        repo.update_deployment(tenant_id, deployment_id, {
            "lastRequestedSpec.shutdownInfo": None,
            "status": "running"
        })
        
        return {
            "tenantId": tenant_id,
            "deploymentId": deployment_id,
            **result
        }
    
    # Enterprise logic continues below

    cr = k8s.get_mongodb_cr(namespace, deployment_id)
    if not cr:
        raise ValueError(f"MongoDB CR {deployment_id} not found in namespace {namespace}")

    # Determine deployment type
    deployment_type = deployment.get("type", "ReplicaSet")
    
    if deployment_type == "ShardedCluster":
        # Get stored shutdown info with CR spec
        shutdown_info = deployment.get("lastRequestedSpec", {}).get("shutdownInfo", {})
        
        if not shutdown_info or "cr_spec" not in shutdown_info:
            raise ValueError("No shutdown info found. Deployment may not have been properly shutdown.")
        
        cr_spec = shutdown_info.get("cr_spec")
        cr_labels = shutdown_info.get("cr_metadata_labels", {})
        cr_annotations = shutdown_info.get("cr_metadata_annotations", {})
        
        print(f"[LIFECYCLE] Starting ShardedCluster {deployment_id}")
        
        # Recreate the MongoDB CR
        # This will cause the operator to reconcile and create all resources
        mongodb_cr = {
            "apiVersion": "mongodb.com/v1",
            "kind": "MongoDB",
            "metadata": {
                "name": deployment_id,
                "namespace": namespace,
                "labels": cr_labels,
                "annotations": cr_annotations
            },
            "spec": cr_spec
        }
        
        try:
            k8s.custom_objects.create_namespaced_custom_object(
                group="mongodb.com",
                version="v1",
                namespace=namespace,
                plural="mongodb",
                body=mongodb_cr
            )
            print(f"[LIFECYCLE] Recreated MongoDB CR {deployment_id}")
        except Exception as e:
            print(f"[LIFECYCLE] Error recreating MongoDB CR: {e}")
            raise ValueError(f"Failed to recreate MongoDB CR: {e}")
        
        # Clear shutdown info and restore status
        repo.update_deployment(tenant_id, deployment_id, {
            "lastRequestedSpec.shutdownInfo": None,
            "status": "running"
        })
        
        return {
            "tenantId": tenant_id,
            "deploymentId": deployment_id,
            "action": "start",
            "replicas": "N/A",
            "message": "Started ShardedCluster - CR recreated, operator reconciling"
        }
    
    elif deployment_type == "Standalone":
        members_before_shutdown = deployment.get("lastRequestedSpec", {}).get("membersBeforeShutdown", 1)
        deployment_name = f"{deployment_id}-db"
        
        try:
            k8s.apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body={"spec": {"replicas": members_before_shutdown}}
            )
        except Exception as e:
            # Try StatefulSet as fallback
            try:
                k8s.patch_statefulset_replicas(namespace, deployment_id, members_before_shutdown)
            except:
                raise ValueError(f"Could not find Deployment or StatefulSet for {deployment_id}")
        
        repo.update_deployment(tenant_id, deployment_id, {
            "lastRequestedSpec.membersBeforeShutdown": None
        })
        
        return {
            "tenantId": tenant_id,
            "deploymentId": deployment_id,
            "action": "start",
            "type": "Standalone",
            "replicas": members_before_shutdown
        }
    
    else:
        # ReplicaSet (default)
        shutdown_info = deployment.get("lastRequestedSpec", {}).get("shutdownInfo", {})
        
        if not shutdown_info or "cr_spec" not in shutdown_info:
            raise ValueError("No shutdown info found. Deployment may not have been properly shutdown.")
        
        cr_spec = shutdown_info.get("cr_spec")
        cr_labels = shutdown_info.get("cr_metadata_labels", {})
        cr_annotations = shutdown_info.get("cr_metadata_annotations", {})
        previous_replicas = shutdown_info.get("previous_replicas", 3)
        
        print(f"[LIFECYCLE] Starting ReplicaSet {deployment_id}")
        
        # Recreate the MongoDB CR
        mongodb_cr = {
            "apiVersion": "mongodb.com/v1",
            "kind": "MongoDB",
            "metadata": {
                "name": deployment_id,
                "namespace": namespace,
                "labels": cr_labels,
                "annotations": cr_annotations
            },
            "spec": cr_spec
        }
        
        try:
            k8s.custom_objects.create_namespaced_custom_object(
                group="mongodb.com",
                version="v1",
                namespace=namespace,
                plural="mongodb",
                body=mongodb_cr
            )
            print(f"[LIFECYCLE] Recreated MongoDB CR {deployment_id}")
        except Exception as e:
            print(f"[LIFECYCLE] Error recreating MongoDB CR: {e}")
            raise ValueError(f"Failed to recreate MongoDB CR: {e}")

        repo.update_deployment(tenant_id, deployment_id, {
            "lastRequestedSpec.shutdownInfo": None,
            "status": "running"
        })

        return {
            "tenantId": tenant_id,
            "deploymentId": deployment_id,
            "action": "start",
            "replicas": previous_replicas
        }


def restart_deployment(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Restart a deployment by performing a rolling restart of all pods.
    Supports both enterprise and community deployments.
    """
    repo = get_repo()
    k8s = get_k8s_client()

    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")
    
    namespace = tenant["namespace"]
    plan = tenant.get("plan", "enterprise")
    
    # Route to community service if needed
    if plan == "community":
        result = deployments_community_service.restart_deployment_community(namespace, deployment_id)
        return {
            "tenantId": tenant_id,
            "deploymentId": deployment_id,
            **result
        }
    
    # Enterprise logic continues below

    deployment = repo.get_deployment(tenant_id, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment {deployment_id} not found for tenant {tenant_id}")

    namespace = tenant["namespace"]

    cr = k8s.get_mongodb_cr(namespace, deployment_id)
    if not cr:
        raise ValueError(f"MongoDB CR {deployment_id} not found in namespace {namespace}")

    deployment_type = deployment.get("type", "ReplicaSet")
    
    if deployment_type == "ShardedCluster":
        # Restart all components of sharded cluster
        shard_count = deployment.get("shardCount", 2)
        restarted = []
        
        # Restart shards
        for i in range(shard_count):
            shard_name = f"{deployment_id}-shard-{i}"
            try:
                pods = k8s.list_pods_for_statefulset(namespace, shard_name)
                for pod in pods:
                    k8s.delete_pod(namespace, pod.metadata.name)
                restarted.append(f"shard-{i}")
            except Exception as e:
                print(f"[LIFECYCLE] Warning: Could not restart shard {shard_name}: {e}")
        
        # Restart config servers
        configsvr_name = f"{deployment_id}-configsvr"
        try:
            pods = k8s.list_pods_for_statefulset(namespace, configsvr_name)
            for pod in pods:
                k8s.delete_pod(namespace, pod.metadata.name)
            restarted.append("configsvr")
        except Exception as e:
            print(f"[LIFECYCLE] Warning: Could not restart config servers: {e}")
        
        # Restart mongos pods (managed by operator, but we can delete pods)
        try:
            pods = k8s.core_v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=f"app.kubernetes.io/component=mongos,app.kubernetes.io/instance={deployment_id}"
            )
            for pod in pods.items:
                k8s.delete_pod(namespace, pod.metadata.name)
            if pods.items:
                restarted.append("mongos")
        except Exception as e:
            print(f"[LIFECYCLE] Warning: Could not restart mongos: {e}")
        
        return {
            "tenantId": tenant_id,
            "deploymentId": deployment_id,
            "action": "restart",
            "message": f"Restarted {len(restarted)} components: {', '.join(restarted)}"
        }
    
    elif deployment_type == "Standalone":
        # Standalone uses Deployment
        deployment_name = f"{deployment_id}-db"
        try:
            pods = k8s.core_v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=f"app={deployment_id}"
            )
            for pod in pods.items:
                k8s.delete_pod(namespace, pod.metadata.name)
        except Exception as e:
            # Try StatefulSet as fallback
            try:
                pods = k8s.list_pods_for_statefulset(namespace, deployment_id)
                for pod in pods:
                    k8s.delete_pod(namespace, pod.metadata.name)
            except:
                raise ValueError(f"Could not find pods for {deployment_id}")
        
        return {
            "tenantId": tenant_id,
            "deploymentId": deployment_id,
            "action": "restart",
            "message": "Standalone deployment restarted"
        }
    
    else:
        # ReplicaSet (default)
        statefulset_name = deployment_id
        sts = k8s.get_statefulset(namespace, statefulset_name)
        if not sts:
            raise ValueError(f"StatefulSet {statefulset_name} not found in namespace {namespace}")

        pods = k8s.list_pods_for_statefulset(namespace, statefulset_name)

        for pod in pods:
            pod_name = pod.metadata.name
            k8s.delete_pod(namespace, pod_name)
            # Don't wait for each pod, let K8s handle rolling restart

        return {
            "tenantId": tenant_id,
            "deploymentId": deployment_id,
            "action": "restart",
            "message": "Rolling restart initiated"
        }
