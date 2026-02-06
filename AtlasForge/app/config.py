import os
from typing import Optional

# MongoDB for control-plane metadata
MCP_MONGODB_URI: str = os.getenv(
    "MCP_MONGODB_URI",
    "mongodb://shashank:password@ec2-34-213-34-101.us-west-2.compute.amazonaws.com:27017/?authSource=admin"
)
MCP_DB_NAME: str = os.getenv("MCP_DB_NAME", "mdb_control_plane")

# Kubernetes access (running outside cluster)
MCP_KUBECONFIG_PATH: Optional[str] = os.getenv("MCP_KUBECONFIG_PATH", "/home/ubuntu/.kube/config")

# Namespace convention
MCP_NAMESPACE_PREFIX: str = os.getenv("MCP_NAMESPACE_PREFIX", "mdb-")

# Ops Manager (for wiring only; no direct API calls in v1)
MCP_OPS_MANAGER_URL: str = os.getenv("MCP_OPS_MANAGER_URL", "http://ec2-35-88-225-248.us-west-2.compute.amazonaws.com:8080")
MCP_OPS_MANAGER_ORG: str = os.getenv("MCP_OPS_MANAGER_ORG", "69666befd5b6737b862a34b5")

# ONE global programmatic key created manually in Ops Manager (Org Owner)
MCP_OM_GLOBAL_PUBLIC_KEY: str = os.getenv("MCP_OM_GLOBAL_PUBLIC_KEY", "yqhrwzfm")
MCP_OM_GLOBAL_PRIVATE_KEY: str = os.getenv("MCP_OM_GLOBAL_PRIVATE_KEY", "99ad8914-3721-4249-83eb-d6d4c30b6ae5")

# Optional logging/config
MCP_LOG_LEVEL: str = os.getenv("MCP_LOG_LEVEL", "INFO")
MCP_SERVICE_PORT: int = int(os.getenv("MCP_SERVICE_PORT", "8001"))
