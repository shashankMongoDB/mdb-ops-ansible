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


_k8s_instance: Optional[K8sClient] = None


def get_k8s_client() -> K8sClient:
    global _k8s_instance
    if _k8s_instance is None:
        _k8s_instance = K8sClient()
    return _k8s_instance
