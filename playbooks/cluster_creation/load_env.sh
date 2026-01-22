#!/bin/bash

# Environment Loader for MongoDB Deployment
# Loads variables from .env file and exports them

ENV_FILE="${1:-.env}"

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: Environment file '$ENV_FILE' not found!"
    echo ""
    echo "Please create it from the template:"
    echo "  cp .env.example $ENV_FILE"
    echo "  vi $ENV_FILE  # Update with your values"
    exit 1
fi

echo "📦 Loading environment from: $ENV_FILE"
echo ""

# Export all variables from .env file
# Ignore comments and empty lines
set -a
source "$ENV_FILE"
set +a

# Validate required variables
REQUIRED_VARS=(
    "OPS_MANAGER_URL"
    "OPS_MANAGER_PUBLIC_KEY"
    "OPS_MANAGER_PRIVATE_KEY"
    "OPS_MANAGER_PROJECT_ID"
    "OPS_MANAGER_AGENT_API_KEY"
    "VM1_IP"
    "VM2_IP"
    "VM3_IP"
)

MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo "❌ Error: Missing required environment variables:"
    printf '  - %s\n' "${MISSING_VARS[@]}"
    exit 1
fi

echo "✅ Environment loaded successfully!"
echo ""
echo "Key variables:"
echo "  OPS_MANAGER_URL: $OPS_MANAGER_URL"
echo "  PROJECT_ID: $OPS_MANAGER_PROJECT_ID"
echo "  VMs: $VM1_IP, $VM2_IP, $VM3_IP"
echo "  REPLICA_SET: $REPLICA_SET_NAME"
echo "  AUTH: $ENABLE_AUTHENTICATION"
echo ""

# Export a flag to indicate environment is loaded
export ENV_LOADED=true
