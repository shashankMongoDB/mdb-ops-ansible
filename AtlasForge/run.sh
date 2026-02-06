#!/bin/bash

export MCP_MONGODB_URI="mongodb://shashank:password@ec2-34-213-34-101.us-west-2.compute.amazonaws.com:27017/?authSource=admin"
export MCP_DB_NAME="mdb_control_plane"
export MCP_KUBECONFIG_PATH="/home/ubuntu/.kube/config"
export MCP_NAMESPACE_PREFIX="mdb-"
export MCP_OPS_MANAGER_URL="http://ec2-35-88-225-248.us-west-2.compute.amazonaws.com:8080"
export MCP_OPS_MANAGER_ORG="69666befd5b6737b862a34b5"
export MCP_OM_GLOBAL_PUBLIC_KEY="yqhrwzfm"
export MCP_OM_GLOBAL_PRIVATE_KEY="99ad8914-3721-4249-83eb-d6d4c30b6ae5"
export MCP_LOG_LEVEL="INFO"
export MCP_SERVICE_PORT="8001"

uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
