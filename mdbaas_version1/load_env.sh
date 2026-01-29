#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE_INPUT="${1:-}"
if [[ -n "$ENV_FILE_INPUT" ]]; then
  if [[ "$ENV_FILE_INPUT" = /* ]]; then
    ENV_FILE="$ENV_FILE_INPUT"
  else
    ENV_FILE="$ROOT_DIR/$ENV_FILE_INPUT"
  fi
else
  ENV_FILE="$ROOT_DIR/.env"
endif

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[load_env] ERROR: Environment file '$ENV_FILE' not found." >&2
  echo "Create it (or copy from version control) and rerun: source ./load_env.sh" >&2
  exit 1
fi

echo "[load_env] Loading environment from: $ENV_FILE"
set -a
source "$ENV_FILE"
set +a

required_vars=(
  OPS_MANAGER_URL
  OPS_MANAGER_HOST
  OPS_MANAGER_PUBLIC_KEY
  OPS_MANAGER_PRIVATE_KEY
  OPS_MANAGER_API_VERSION
  OPS_MANAGER_ORG_ID
  OPS_MANAGER_PROJECT_ID
  OPS_MANAGER_AGENT_API_KEY
  SSH_USER
  SSH_KEY_PATH
  OS_TYPE
  OS_VERSION
  MONGODB_VERSION
  MONGODB_PORT
  MONGODB_DATA_PATH
  MONGODB_LOG_PATH
  REPLICA_SET_NAME
  VM1_IP
  VM1_HOSTNAME
  VM1_OPS_MANAGER_HOSTNAME
  VM1_PRIORITY
  VM1_MEMBER_ID
  VM2_IP
  VM2_HOSTNAME
  VM2_OPS_MANAGER_HOSTNAME
  VM2_PRIORITY
  VM2_MEMBER_ID
  VM3_IP
  VM3_HOSTNAME
  VM3_OPS_MANAGER_HOSTNAME
  VM3_PRIORITY
  VM3_MEMBER_ID
  STANDALONE_HOSTNAME
  STANDALONE_MONGODB_PORT
  STANDALONE_MONGODB_DATA_PATH
  STANDALONE_MONGODB_LOG_PATH
)

missing_vars=()
for var in "${required_vars[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    missing_vars+=("$var")
  fi
done

if [[ ${#missing_vars[@]} -gt 0 ]]; then
  echo "[load_env] ERROR: Missing required variables. Update $ENV_FILE and rerun:" >&2
  printf '  - %s\n' "${missing_vars[@]}" >&2
  exit 1
fi

echo "[load_env] Environment ready. Run playbooks with:"
echo "  source ./load_env.sh && ansible-playbook <playbook>.yml"
