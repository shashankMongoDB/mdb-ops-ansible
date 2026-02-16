from typing import Dict, Any
from app.services.mongo_repo import get_repo
from app.services.k8s_client import get_k8s_client
from app.services import monitoring_service
from app.services import deployments_community_service
from app.services import backup_service


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

    # Get CR based on plan to read replica set name
    if plan == "community":
        cr = k8s.get_mongodb_community_cr(namespace, deployment_id)
    else:
        cr = k8s.get_mongodb_enterprise_cr(namespace, deployment_id)
    
    if not cr:
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
            "externalUri": external_uri
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
            "error": f"Failed to create external service: {str(e)}"
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
        # Store shutdown info in DB
        repo.update_deployment(tenant_id, deployment_id, {
            "lastRequestedSpec.membersBeforeShutdown": result["previousReplicas"]
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

    # Determine deployment type from CR
    deployment_type = deployment.get("type", "ReplicaSet")
    
    # Handle different deployment types
    if deployment_type == "ShardedCluster":
        # ShardedCluster has multiple StatefulSets
        # Get shard configuration
        shard_count = deployment.get("shardCount", 2)
        
        shutdown_info = {}
        
        # Shutdown all shards
        for i in range(shard_count):
            shard_name = f"{deployment_id}-shard-{i}"
            try:
                sts = k8s.get_statefulset(namespace, shard_name)
                if sts:
                    previous_replicas = sts.spec.replicas
                    k8s.patch_statefulset_replicas(namespace, shard_name, 0)
                    shutdown_info[f"shard-{i}"] = previous_replicas
            except Exception as e:
                print(f"[LIFECYCLE] Warning: Could not shutdown shard {shard_name}: {e}")
        
        # Shutdown config servers
        configsvr_name = f"{deployment_id}-configsvr"
        try:
            sts = k8s.get_statefulset(namespace, configsvr_name)
            if sts:
                previous_replicas = sts.spec.replicas
                k8s.patch_statefulset_replicas(namespace, configsvr_name, 0)
                shutdown_info["configsvr"] = previous_replicas
        except Exception as e:
            print(f"[LIFECYCLE] Warning: Could not shutdown config servers: {e}")
        
        # Note: mongos is managed by the MongoDB CR, not a separate Deployment
        # The operator will handle scaling mongos when we scale the shards
        # We just store the expected mongos count from deployment metadata
        mongos_count = deployment.get("mongosCount", 2)
        shutdown_info["mongos"] = mongos_count
        
        # Store shutdown info
        repo.update_deployment(tenant_id, deployment_id, {
            "lastRequestedSpec.shutdownInfo": shutdown_info
        })
        
        # Calculate total pods shutdown
        total_previous = sum(shutdown_info.values())
        
        return {
            "tenantId": tenant_id,
            "deploymentId": deployment_id,
            "action": "shutdown",
            "previousReplicas": total_previous,
            "currentReplicas": 0,
            "message": f"Shutdown {len(shutdown_info)} components: {list(shutdown_info.keys())}"
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
        statefulset_name = deployment_id
        sts = k8s.get_statefulset(namespace, statefulset_name)
        if not sts:
            raise ValueError(f"StatefulSet {statefulset_name} not found in namespace {namespace}")

        previous_replicas = sts.spec.replicas

        k8s.patch_statefulset_replicas(namespace, statefulset_name, 0)

        repo.update_deployment(tenant_id, deployment_id, {
            "lastRequestedSpec.membersBeforeShutdown": previous_replicas
        })

        return {
            "tenantId": tenant_id,
            "deploymentId": deployment_id,
            "action": "shutdown",
            "type": "ReplicaSet",
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
    
    # Get target members from stored shutdown info
    members_before_shutdown = deployment.get("lastRequestedSpec", {}).get("membersBeforeShutdown", 3)
    
    # Route to community service if needed
    if plan == "community":
        result = deployments_community_service.start_deployment_community(namespace, deployment_id, members_before_shutdown)
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
        # Get stored shutdown info
        shutdown_info = deployment.get("lastRequestedSpec", {}).get("shutdownInfo", {})
        
        # Start all shards
        shard_count = deployment.get("shardCount", 2)
        for i in range(shard_count):
            shard_name = f"{deployment_id}-shard-{i}"
            desired_replicas = shutdown_info.get(f"shard-{i}", 3)
            try:
                k8s.patch_statefulset_replicas(namespace, shard_name, desired_replicas)
            except Exception as e:
                print(f"[LIFECYCLE] Warning: Could not start shard {shard_name}: {e}")
        
        # Start config servers
        configsvr_name = f"{deployment_id}-configsvr"
        desired_replicas = shutdown_info.get("configsvr", 3)
        try:
            k8s.patch_statefulset_replicas(namespace, configsvr_name, desired_replicas)
        except Exception as e:
            print(f"[LIFECYCLE] Warning: Could not start config servers: {e}")
        
        # Note: mongos is managed by the MongoDB CR, operator handles it automatically
        
        # Clear shutdown info
        repo.update_deployment(tenant_id, deployment_id, {
            "lastRequestedSpec.shutdownInfo": None
        })
        
        total_replicas = sum(shutdown_info.values())
        
        return {
            "tenantId": tenant_id,
            "deploymentId": deployment_id,
            "action": "start",
            "replicas": total_replicas,
            "message": f"Started {len(shutdown_info)} components"
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
        statefulset_name = deployment_id
        sts = k8s.get_statefulset(namespace, statefulset_name)
        if not sts:
            raise ValueError(f"StatefulSet {statefulset_name} not found in namespace {namespace}")

        members_before_shutdown = deployment.get("lastRequestedSpec", {}).get("membersBeforeShutdown")
        if members_before_shutdown:
            desired_replicas = members_before_shutdown
        else:
            desired_replicas = cr.get("spec", {}).get("members", 3)

        k8s.patch_statefulset_replicas(namespace, statefulset_name, desired_replicas)

        repo.update_deployment(tenant_id, deployment_id, {
            "lastRequestedSpec.membersBeforeShutdown": None
        })

        return {
            "tenantId": tenant_id,
            "deploymentId": deployment_id,
            "action": "start",
            "type": "ReplicaSet",
            "replicas": desired_replicas
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
