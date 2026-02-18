import time
from typing import Optional, Dict, Any, List
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream
from app import config


class K8sClient:
    def __init__(self):
        if config.MCP_KUBECONFIG_PATH:
            k8s_config.load_kube_config(config_file=config.MCP_KUBECONFIG_PATH)
        else:
            k8s_config.load_kube_config()
        
        self.core_v1 = client.CoreV1Api()
        self.custom_objects = client.CustomObjectsApi()
        self.apps_v1 = client.AppsV1Api()
        self.batch_v1 = client.BatchV1Api()

    def _fresh_core_v1(self) -> client.CoreV1Api:
        """
        Return a fresh CoreV1Api instance.
        Avoids issues where stream() exec mutates the shared API client's transport.
        """
        return client.CoreV1Api()

    def exec_in_pod(
        self,
        pod_name: str,
        namespace: str,
        command: List[str],
        container: Optional[str] = None,
    ) -> str:
        """Execute command in pod using a fresh CoreV1Api to avoid stream transport side-effects."""
        core_v1 = self._fresh_core_v1()
        kwargs: Dict[str, Any] = {
            "command": command,
            "stderr": True,
            "stdin": False,
            "stdout": True,
            "tty": False,
        }
        if container:
            kwargs["container"] = container

        return stream(
            core_v1.connect_get_namespaced_pod_exec,
            pod_name,
            namespace,
            **kwargs,
        )

    def ensure_namespace(self, name: str, labels: Optional[Dict[str, str]] = None) -> None:
        try:
            self.core_v1.read_namespace(name=name)
        except ApiException as e:
            if e.status == 404:
                ns = client.V1Namespace(
                    metadata=client.V1ObjectMeta(
                        name=name,
                        labels=labels or {}
                    )
                )
                self.core_v1.create_namespace(body=ns)
            else:
                raise

    def ensure_configmap(self, namespace: str, name: str, data: Dict[str, str]) -> None:
        try:
            self.core_v1.read_namespaced_config_map(name=name, namespace=namespace)
        except ApiException as e:
            if e.status == 404:
                cm = client.V1ConfigMap(
                    metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                    data=data
                )
                self.core_v1.create_namespaced_config_map(namespace=namespace, body=cm)
            else:
                raise

    def ensure_secret(self, namespace: str, name: str, string_data: Dict[str, str]) -> None:
        try:
            self.core_v1.read_namespaced_secret(name=name, namespace=namespace)
        except ApiException as e:
            if e.status == 404:
                secret = client.V1Secret(
                    metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                    string_data=string_data,
                    type="Opaque"
                )
                self.core_v1.create_namespaced_secret(namespace=namespace, body=secret)
            else:
                raise

    def get_configmap(self, namespace: str, name: str) -> Optional[Dict[str, str]]:
        """Read a ConfigMap's data. Returns the data dict or None if not found."""
        try:
            cm = self.core_v1.read_namespaced_config_map(name=name, namespace=namespace)
            return cm.data or {}
        except ApiException as e:
            if e.status == 404:
                return None
            raise

    def create_combined_ca_configmap(self, target_namespace: str, source_namespace: str,
                                     source_configmap: str = "om-ca",
                                     target_configmap: str = "om-ca-combined") -> None:
        """
        Create a combined CA configmap in the target namespace.

        Reads the custom OM CA from source_namespace/source_configmap (key 'ca-pem'),
        combines it with system root CAs, and creates a new configmap in target_namespace
        with two keys:
          - 'ca-pem': the custom OM CA only
          - 'mms-ca.crt': combined bundle (custom CA + system root CAs)

        This ensures the MCK automation agent can trust both the Ops Manager TLS cert
        AND public HTTPS endpoints like fastdl.mongodb.org for MongoDB binary downloads.
        """
        source_data = self.get_configmap(source_namespace, source_configmap)
        if source_data is None or "ca-pem" not in source_data:
            raise ValueError(
                f"ConfigMap '{source_configmap}' in namespace '{source_namespace}' "
                f"not found or missing 'ca-pem' key"
            )

        om_ca = source_data["ca-pem"]

        # Build combined CA bundle: custom OM CA + system root CAs
        combined_parts = [om_ca.strip()]
        system_ca_paths = [
            "/etc/ssl/certs/ca-certificates.crt",
            "/etc/pki/tls/certs/ca-bundle.crt",
            "/etc/ssl/ca-bundle.pem",
        ]
        for ca_path in system_ca_paths:
            try:
                with open(ca_path, "r") as f:
                    combined_parts.append(f.read().strip())
                break
            except FileNotFoundError:
                continue

        combined_bundle = "\n".join(combined_parts) + "\n"

        self.ensure_configmap(
            namespace=target_namespace,
            name=target_configmap,
            data={
                "ca-pem": om_ca,
                "mms-ca.crt": combined_bundle,
            }
        )

    def ensure_service_account(self, namespace: str, name: str) -> None:
        """
        Create a ServiceAccount if it does not exist.
        If it already exists, do nothing (no error).
        
        MCK expects this ServiceAccount for MongoDB StatefulSet pods.
        Without it, pods fail with 'serviceaccount ... not found' and deployments never become Ready.
        """
        try:
            self.core_v1.read_namespaced_service_account(name=name, namespace=namespace)
        except ApiException as e:
            if e.status == 404:
                service_account = client.V1ServiceAccount(
                    metadata=client.V1ObjectMeta(name=name, namespace=namespace)
                )
                self.core_v1.create_namespaced_service_account(namespace=namespace, body=service_account)
            else:
                raise

    def ensure_role(self, namespace: str, name: str, rules: list) -> None:
        """
        Create a Role if it does not exist.
        If it already exists, do nothing (no error).
        
        Used for community tenant RBAC setup.
        """
        rbac_v1 = client.RbacAuthorizationV1Api(self.core_v1.api_client)
        
        try:
            rbac_v1.read_namespaced_role(name=name, namespace=namespace)
        except ApiException as e:
            if e.status == 404:
                role = client.V1Role(
                    metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                    rules=rules
                )
                rbac_v1.create_namespaced_role(namespace=namespace, body=role)
            else:
                raise

    def ensure_role_binding(self, namespace: str, name: str, role_name: str, service_account_name: str) -> None:
        """
        Create a RoleBinding if it does not exist.
        If it already exists, do nothing (no error).
        
        Binds a ServiceAccount to a Role in the same namespace.
        Used for community tenant RBAC setup.
        """
        rbac_v1 = client.RbacAuthorizationV1Api(self.core_v1.api_client)
        
        try:
            rbac_v1.read_namespaced_role_binding(name=name, namespace=namespace)
        except ApiException as e:
            if e.status == 404:
                role_binding = client.V1RoleBinding(
                    metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                    role_ref=client.V1RoleRef(
                        api_group="rbac.authorization.k8s.io",
                        kind="Role",
                        name=role_name
                    ),
                    subjects=[
                        client.RbacV1Subject(
                            kind="ServiceAccount",
                            name=service_account_name,
                            namespace=namespace
                        )
                    ]
                )
                rbac_v1.create_namespaced_role_binding(namespace=namespace, body=role_binding)
            else:
                raise

    def ensure_external_service(self, namespace: str, deployment_id: str) -> tuple[str, int]:
        """
        Ensure external NodePort service exists for a MongoDB deployment.
        
        Creates a NodePort service for external access (VPC clients).
        Returns (service_name, node_port).
        
        Args:
            namespace: Kubernetes namespace
            deployment_id: MongoDB deployment ID
            
        Returns:
            Tuple of (service_name, node_port)
        """
        service_name = f"{deployment_id}-external"
        
        # Check if service already exists
        try:
            existing_svc = self.core_v1.read_namespaced_service(service_name, namespace)
            # Service exists - get the NodePort
            for port in existing_svc.spec.ports:
                if port.name == "mongodb":
                    return (service_name, port.node_port)
        except client.exceptions.ApiException as e:
            if e.status != 404:
                raise
        
        # Create NodePort service
        service = client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=client.V1ObjectMeta(
                name=service_name,
                namespace=namespace,
                labels={
                    "app": deployment_id,
                    "mdb.example.com/external": "true"
                }
            ),
            spec=client.V1ServiceSpec(
                type="NodePort",
                selector={
                    "app": f"{deployment_id}-svc"
                },
                ports=[
                    client.V1ServicePort(
                        name="mongodb",
                        port=27017,
                        target_port=27017,
                        protocol="TCP"
                        # nodePort auto-assigned by K8s
                    )
                ]
            )
        )
        
        created_svc = self.core_v1.create_namespaced_service(namespace, service)
        
        # Get the assigned NodePort
        node_port = None
        for port in created_svc.spec.ports:
            if port.name == "mongodb":
                node_port = port.node_port
                break
        
        return (service_name, node_port)

    def ensure_external_service_for_pod(self, namespace: str, deployment_id: str, pod_name: str, role: str) -> tuple[str, int]:
        """
        Ensure a NodePort service exists targeting a specific pod (via pod-name selector).
        Returns (service_name, node_port).
        """
        service_name = f"{deployment_id}-{role}-external"
        selector = {
            "statefulset.kubernetes.io/pod-name": pod_name
        }

        try:
            existing_svc = self.core_v1.read_namespaced_service(service_name, namespace)
            existing_selector = existing_svc.spec.selector or {}

            # If selector drifted (e.g. new primary), patch it and keep same NodePort.
            if existing_selector != selector:
                patch = {
                    "spec": {
                        "selector": selector
                    }
                }
                self.core_v1.patch_namespaced_service(service_name, namespace, patch)
                existing_svc = self.core_v1.read_namespaced_service(service_name, namespace)

            for port in existing_svc.spec.ports:
                if port.name == "mongodb":
                    return (service_name, port.node_port)
        except client.exceptions.ApiException as e:
            if e.status != 404:
                raise

        service = client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=client.V1ObjectMeta(
                name=service_name,
                namespace=namespace,
                labels={
                    "app": deployment_id,
                    "mdb.example.com/external": "true",
                    "mdb.example.com/role": role
                }
            ),
            spec=client.V1ServiceSpec(
                type="NodePort",
                selector=selector,
                ports=[
                    client.V1ServicePort(
                        name="mongodb",
                        port=27017,
                        target_port=27017,
                        protocol="TCP"
                    )
                ]
            )
        )

        created_svc = self.core_v1.create_namespaced_service(namespace, service)

        node_port = None
        for port in created_svc.spec.ports:
            if port.name == "mongodb":
                node_port = port.node_port
                break

        return (service_name, node_port)

    def get_worker_node_ip(self) -> str:
        """
        Get the InternalIP of the first worker node.
        
        Returns:
            Node IP address as string
        """
        nodes = self.core_v1.list_node()
        
        for node in nodes.items:
            # Skip control-plane nodes
            if "node-role.kubernetes.io/control-plane" in node.metadata.labels:
                continue
            if "node-role.kubernetes.io/master" in node.metadata.labels:
                continue
            
            # Get InternalIP
            for addr in node.status.addresses:
                if addr.type == "InternalIP":
                    return addr.address
        
        # Fallback: return first node's internal IP
        if nodes.items:
            for addr in nodes.items[0].status.addresses:
                if addr.type == "InternalIP":
                    return addr.address
        
        raise ValueError("No worker nodes found in cluster")

    def ensure_service_account(self, namespace: str, name: str) -> None:
        """
        Create a ServiceAccount if it does not exist.
        If it already exists, do nothing (no error).
        
        MCK expects this ServiceAccount for MongoDB StatefulSet pods.
        Without it, pods fail with 'serviceaccount ... not found' and deployments never become Ready.
        """
        try:
            self.core_v1.read_namespaced_service_account(name=name, namespace=namespace)
        except ApiException as e:
            if e.status == 404:
                service_account = client.V1ServiceAccount(
                    metadata=client.V1ObjectMeta(name=name, namespace=namespace)
                )
                self.core_v1.create_namespaced_service_account(namespace=namespace, body=service_account)
            else:
                raise

    def ensure_role(self, namespace: str, name: str, rules: list) -> None:
        """
        Create a Role if it does not exist.
        If it already exists, do nothing (no error).
        
        Used for community tenant RBAC setup.
        """
        rbac_v1 = client.RbacAuthorizationV1Api(self.core_v1.api_client)
        
        try:
            rbac_v1.read_namespaced_role(name=name, namespace=namespace)
        except ApiException as e:
            if e.status == 404:
                role = client.V1Role(
                    metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                    rules=rules
                )
                rbac_v1.create_namespaced_role(namespace=namespace, body=role)
            else:
                raise

    def ensure_role_binding(self, namespace: str, name: str, role_name: str, service_account_name: str) -> None:
        """
        Create a RoleBinding if it does not exist.
        If it already exists, do nothing (no error).
        
        Binds a ServiceAccount to a Role in the same namespace.
        Used for community tenant RBAC setup.
        """
        rbac_v1 = client.RbacAuthorizationV1Api(self.core_v1.api_client)
        
        try:
            rbac_v1.read_namespaced_role_binding(name=name, namespace=namespace)
        except ApiException as e:
            if e.status == 404:
                role_binding = client.V1RoleBinding(
                    metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                    role_ref=client.V1RoleRef(
                        api_group="rbac.authorization.k8s.io",
                        kind="Role",
                        name=role_name
                    ),
                    subjects=[
                        client.RbacV1Subject(
                            kind="ServiceAccount",
                            name=service_account_name,
                            namespace=namespace
                        )
                    ]
                )
                rbac_v1.create_namespaced_role_binding(namespace=namespace, body=role_binding)
            else:
                raise

    # ========== Enterprise MongoDB CRs (mongodb.com) ==========
    
    def create_mongodb_enterprise_cr(self, namespace: str, body: Dict[str, Any]) -> None:
        """Create an enterprise MongoDB CR (mongodb.com/v1)"""
        self.custom_objects.create_namespaced_custom_object(
            group="mongodb.com",
            version="v1",
            namespace=namespace,
            plural="mongodb",
            body=body
        )

    def get_mongodb_enterprise_cr(self, namespace: str, name: str) -> Optional[Dict[str, Any]]:
        """Get an enterprise MongoDB CR (mongodb.com/v1)"""
        try:
            return self.custom_objects.get_namespaced_custom_object(
                group="mongodb.com",
                version="v1",
                namespace=namespace,
                plural="mongodb",
                name=name
            )
        except ApiException as e:
            if e.status == 404:
                return None
            raise

    def list_mongodb_enterprise_crs(self, namespace: str) -> list[Dict[str, Any]]:
        """List all enterprise MongoDB CRs in a namespace"""
        try:
            result = self.custom_objects.list_namespaced_custom_object(
                group="mongodb.com",
                version="v1",
                namespace=namespace,
                plural="mongodb"
            )
            return result.get("items", [])
        except ApiException as e:
            if e.status == 404:
                return []
            raise

    def delete_mongodb_enterprise_cr(self, namespace: str, name: str) -> bool:
        """Delete an enterprise MongoDB CR"""
        try:
            self.custom_objects.delete_namespaced_custom_object(
                group="mongodb.com",
                version="v1",
                namespace=namespace,
                plural="mongodb",
                name=name
            )
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise

    def patch_mongodb_enterprise_cr(self, namespace: str, name: str, patch: Dict[str, Any]) -> None:
        """Patch an enterprise MongoDB CR"""
        try:
            self.custom_objects.patch_namespaced_custom_object(
                group="mongodb.com",
                version="v1",
                namespace=namespace,
                plural="mongodb",
                name=name,
                body=patch
            )
        except ApiException as e:
            if e.status == 404:
                raise ValueError(f"MongoDB CR {name} not found in namespace {namespace}")
            elif e.status == 403:
                raise ValueError(f"Permission denied: Cannot patch MongoDB CR {name} in namespace {namespace}. Check RBAC permissions.")
            else:
                raise ValueError(f"Failed to patch MongoDB CR {name}: {e.reason}")

    # ========== Community MongoDB CRs (mongodbcommunity.mongodb.com) ==========
    
    def create_mongodb_community_cr(self, namespace: str, body: Dict[str, Any]) -> None:
        """Create a community MongoDB CR (mongodbcommunity.mongodb.com/v1)"""
        self.custom_objects.create_namespaced_custom_object(
            group="mongodbcommunity.mongodb.com",
            version="v1",
            namespace=namespace,
            plural="mongodbcommunity",
            body=body
        )

    def get_mongodb_community_cr(self, namespace: str, name: str) -> Optional[Dict[str, Any]]:
        """Get a community MongoDB CR (mongodbcommunity.mongodb.com/v1)"""
        try:
            return self.custom_objects.get_namespaced_custom_object(
                group="mongodbcommunity.mongodb.com",
                version="v1",
                namespace=namespace,
                plural="mongodbcommunity",
                name=name
            )
        except ApiException as e:
            if e.status == 404:
                return None
            raise

    def list_mongodb_community_crs(self, namespace: str) -> list[Dict[str, Any]]:
        """List all community MongoDB CRs in a namespace"""
        try:
            result = self.custom_objects.list_namespaced_custom_object(
                group="mongodbcommunity.mongodb.com",
                version="v1",
                namespace=namespace,
                plural="mongodbcommunity"
            )
            return result.get("items", [])
        except ApiException as e:
            if e.status == 404:
                return []
            raise

    def delete_mongodb_community_cr(self, namespace: str, name: str) -> bool:
        """Delete a community MongoDB CR"""
        try:
            self.custom_objects.delete_namespaced_custom_object(
                group="mongodbcommunity.mongodb.com",
                version="v1",
                namespace=namespace,
                plural="mongodbcommunity",
                name=name
            )
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise

    def patch_mongodb_community_cr(self, namespace: str, name: str, patch: Dict[str, Any]) -> None:
        """Patch a community MongoDB CR"""
        try:
            self.custom_objects.patch_namespaced_custom_object(
                group="mongodbcommunity.mongodb.com",
                version="v1",
                namespace=namespace,
                plural="mongodbcommunity",
                name=name,
                body=patch
            )
        except ApiException as e:
            if e.status == 404:
                raise ValueError(f"MongoDBCommunity CR {name} not found in namespace {namespace}")
            elif e.status == 403:
                raise ValueError(f"Permission denied: Cannot patch MongoDBCommunity CR {name} in namespace {namespace}. Check RBAC permissions.")
            else:
                raise ValueError(f"Failed to patch MongoDBCommunity CR {name}: {e.reason}")

    # ========== Legacy methods for backward compatibility ==========
    
    def create_mongodb_cr(self, namespace: str, body: Dict[str, Any]) -> None:
        """Legacy method - calls enterprise version"""
        self.create_mongodb_enterprise_cr(namespace, body)

    def get_mongodb_cr(self, namespace: str, name: str) -> Optional[Dict[str, Any]]:
        """Legacy method - calls enterprise version"""
        return self.get_mongodb_enterprise_cr(namespace, name)

    def list_mongodb_crs(self, namespace: str) -> list[Dict[str, Any]]:
        """Legacy method - calls enterprise version"""
        return self.list_mongodb_enterprise_crs(namespace)

    def delete_mongodb_cr(self, namespace: str, name: str) -> bool:
        """Legacy method - calls enterprise version"""
        return self.delete_mongodb_enterprise_cr(namespace, name)

    def delete_namespace(self, name: str) -> bool:
        """
        Delete a namespace. Returns True if deleted, False if not found.
        """
        try:
            self.core_v1.delete_namespace(name=name)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise

    def patch_mongodb_cr(self, namespace: str, name: str, patch: Dict[str, Any]) -> None:
        """Legacy method - calls enterprise version"""
        self.patch_mongodb_enterprise_cr(namespace, name, patch)

    def ensure_metrics_service(self, namespace: str, deployment_id: str, selector_labels: Dict[str, str]) -> None:
        """
        Create or update a LoadBalancer Service for Prometheus metrics.
        Service name: <deployment_id>-metrics
        Exposes port 9216 for MongoDB exporter.
        """
        service_name = f"{deployment_id}-metrics"
        
        service = client.V1Service(
            metadata=client.V1ObjectMeta(
                name=service_name,
                namespace=namespace,
                labels={"app": deployment_id, "metrics": "prometheus"}
            ),
            spec=client.V1ServiceSpec(
                type="LoadBalancer",
                selector=selector_labels,
                ports=[
                    client.V1ServicePort(
                        name="metrics",
                        port=9216,
                        target_port=9216,
                        protocol="TCP"
                    )
                ]
            )
        )
        
        try:
            self.core_v1.read_namespaced_service(name=service_name, namespace=namespace)
            self.core_v1.patch_namespaced_service(name=service_name, namespace=namespace, body=service)
        except ApiException as e:
            if e.status == 404:
                self.core_v1.create_namespaced_service(namespace=namespace, body=service)
            else:
                raise

    def delete_service(self, namespace: str, name: str) -> bool:
        """
        Delete a Service. Returns True if deleted, False if not found.
        """
        try:
            self.core_v1.delete_namespaced_service(name=name, namespace=namespace)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise

    def get_service(self, namespace: str, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a Service. Returns service info or None if not found.
        """
        try:
            svc = self.core_v1.read_namespaced_service(name=name, namespace=namespace)
            return {
                "name": svc.metadata.name,
                "namespace": svc.metadata.namespace,
                "type": svc.spec.type,
                "clusterIP": svc.spec.cluster_ip,
                "externalIPs": svc.status.load_balancer.ingress if svc.status.load_balancer.ingress else [],
                "ports": [{"port": p.port, "nodePort": p.node_port, "targetPort": str(p.target_port)} for p in svc.spec.ports]
            }
        except ApiException as e:
            if e.status == 404:
                return None
            raise

    def get_statefulset(self, namespace: str, name: str) -> Optional[Any]:
        """
        Get a StatefulSet. Returns StatefulSet object or None if not found.
        """
        try:
            return self.apps_v1.read_namespaced_stateful_set(name=name, namespace=namespace)
        except ApiException as e:
            if e.status == 404:
                return None
            raise

    def patch_statefulset_replicas(self, namespace: str, name: str, replicas: int) -> None:
        """
        Patch a StatefulSet to set the desired replica count.
        """
        body = {"spec": {"replicas": replicas}}
        self.apps_v1.patch_namespaced_stateful_set(name=name, namespace=namespace, body=body)

    def list_pods_for_statefulset(self, namespace: str, statefulset_name: str) -> List[Any]:
        """
        List all pods for a StatefulSet, sorted by ordinal.
        """
        try:
            label_selector = f"app={statefulset_name}-svc"
            pods = self.core_v1.list_namespaced_pod(namespace=namespace, label_selector=label_selector)
            
            sorted_pods = sorted(pods.items, key=lambda p: int(p.metadata.name.split('-')[-1]))
            return sorted_pods
        except ApiException:
            return []

    def delete_pod(self, namespace: str, name: str, grace_period: int = None) -> bool:
        """
        Delete a pod. Returns True if deleted, False if not found.
        
        Args:
            namespace: K8s namespace
            name: Pod name
            grace_period: Grace period in seconds. 0 for immediate deletion.
        """
        try:
            if grace_period is not None:
                body = client.V1DeleteOptions(grace_period_seconds=grace_period)
                self.core_v1.delete_namespaced_pod(name=name, namespace=namespace, body=body)
            else:
                self.core_v1.delete_namespaced_pod(name=name, namespace=namespace)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise

    def wait_for_pod_ready(self, namespace: str, name: str, timeout: int = 300) -> bool:
        """
        Wait for a pod to be Ready. Returns True if ready, False if timeout.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                pod = self.core_v1.read_namespaced_pod(name=name, namespace=namespace)
                
                if pod.status.phase == "Running":
                    if pod.status.container_statuses:
                        all_ready = all(cs.ready for cs in pod.status.container_statuses)
                        if all_ready:
                            return True
                
                time.sleep(5)
            except ApiException as e:
                if e.status == 404:
                    time.sleep(5)
                    continue
                raise
        
        return False

    def list_worker_node_ips(self) -> List[str]:
        """
        List all worker node IPs (excluding control-plane nodes).
        Returns list of InternalIP addresses from worker nodes.
        """
        try:
            nodes = self.core_v1.list_node()
            worker_ips = []
            
            for node in nodes.items:
                # Check if node has control-plane taint
                is_control_plane = False
                if node.spec.taints:
                    for taint in node.spec.taints:
                        if taint.key in ["node-role.kubernetes.io/control-plane", 
                                        "node-role.kubernetes.io/master"]:
                            is_control_plane = True
                            break
                
                # Skip control-plane nodes
                if is_control_plane:
                    continue
                
                # Get InternalIP from node addresses
                if node.status and node.status.addresses:
                    for addr in node.status.addresses:
                        if addr.type == "InternalIP":
                            worker_ips.append(addr.address)
                            break
            
            return worker_ips
        except ApiException as e:
            raise RuntimeError(f"Failed to list worker nodes: {e}")

    def get_secret_data(self, namespace: str, name: str, key: str = "password") -> Optional[str]:
        """
        Read a secret and return decoded value for a specific key.
        Returns None if secret or key not found.
        """
        import base64
        
        try:
            secret = self._fresh_core_v1().read_namespaced_secret(name=name, namespace=namespace)
            if secret.data and key in secret.data:
                # Decode base64 data
                return base64.b64decode(secret.data[key]).decode('utf-8')
            return None
        except ApiException as e:
            if e.status == 404:
                return None
            raise

    def update_secret_data(self, namespace: str, name: str, key: str, value: str) -> None:
        """
        Update a specific key in an existing secret.
        Creates the key if it doesn't exist, updates if it does.
        """
        import base64
        
        try:
            core_v1 = self._fresh_core_v1()
            secret = core_v1.read_namespaced_secret(name=name, namespace=namespace)
            
            # Encode the new value
            encoded_value = base64.b64encode(value.encode('utf-8')).decode('utf-8')
            
            # Update the secret data
            if secret.data is None:
                secret.data = {}
            secret.data[key] = encoded_value
            
            # Patch the secret
            core_v1.replace_namespaced_secret(name=name, namespace=namespace, body=secret)
        except ApiException as e:
            if e.status == 404:
                raise ValueError(f"Secret {name} not found in namespace {namespace}")
            raise


_k8s_instance: Optional[K8sClient] = None


def get_k8s_client() -> K8sClient:
    global _k8s_instance
    if _k8s_instance is None:
        _k8s_instance = K8sClient()
    return _k8s_instance
