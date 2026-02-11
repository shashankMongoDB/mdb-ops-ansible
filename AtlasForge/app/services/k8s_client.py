import time
from typing import Optional, Dict, Any, List
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException
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
        self.custom_objects.patch_namespaced_custom_object(
            group="mongodb.com",
            version="v1",
            namespace=namespace,
            plural="mongodb",
            name=name,
            body=patch
        )

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
        self.custom_objects.patch_namespaced_custom_object(
            group="mongodbcommunity.mongodb.com",
            version="v1",
            namespace=namespace,
            plural="mongodbcommunity",
            name=name,
            body=patch
        )

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

    def delete_pod(self, namespace: str, name: str) -> bool:
        """
        Delete a pod. Returns True if deleted, False if not found.
        """
        try:
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
            secret = self.core_v1.read_namespaced_secret(name=name, namespace=namespace)
            if secret.data and key in secret.data:
                # Decode base64 data
                return base64.b64decode(secret.data[key]).decode('utf-8')
            return None
        except ApiException as e:
            if e.status == 404:
                return None
            raise


_k8s_instance: Optional[K8sClient] = None


def get_k8s_client() -> K8sClient:
    global _k8s_instance
    if _k8s_instance is None:
        _k8s_instance = K8sClient()
    return _k8s_instance
