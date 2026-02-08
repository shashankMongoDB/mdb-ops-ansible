from typing import Optional, Dict, Any
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

    def create_mongodb_cr(self, namespace: str, body: Dict[str, Any]) -> None:
        self.custom_objects.create_namespaced_custom_object(
            group="mongodb.com",
            version="v1",
            namespace=namespace,
            plural="mongodb",
            body=body
        )

    def get_mongodb_cr(self, namespace: str, name: str) -> Optional[Dict[str, Any]]:
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

    def list_mongodb_crs(self, namespace: str) -> list[Dict[str, Any]]:
        """List all MongoDB CRs in a namespace."""
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

    def delete_mongodb_cr(self, namespace: str, name: str) -> bool:
        """
        Delete a MongoDB CR. Returns True if deleted, False if not found.
        """
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
        """
        Patch a MongoDB CR with the given patch data.
        """
        self.custom_objects.patch_namespaced_custom_object(
            group="mongodb.com",
            version="v1",
            namespace=namespace,
            plural="mongodb",
            name=name,
            body=patch
        )

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


_k8s_instance: Optional[K8sClient] = None


def get_k8s_client() -> K8sClient:
    global _k8s_instance
    if _k8s_instance is None:
        _k8s_instance = K8sClient()
    return _k8s_instance
