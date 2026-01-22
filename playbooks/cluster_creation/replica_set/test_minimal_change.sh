#!/bin/bash
# Test with MINIMAL change to current config
set -e

cd ~/mdbaas-repo/mdb-ops-ansible/playbooks/cluster_creation/replica_set/
source ../load_env.sh

echo "=========================================="
echo "Test: Minimal Config Change"
echo "=========================================="
echo ""

# Get current config
echo "Getting current config..."
curl -u "$OPS_MANAGER_PUBLIC_KEY:$OPS_MANAGER_PRIVATE_KEY" --digest \
  "$OPS_MANAGER_URL/api/public/v1.0/groups/$OPS_MANAGER_PROJECT_ID/automationConfig" \
  > current_config_test.json

echo "Current version: $(cat current_config_test.json | python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])')"
echo ""

# Test 1: Send back EXACTLY what we got (should work)
echo "Test 1: Send back exact same config (no changes)..."
curl -u "$OPS_MANAGER_PUBLIC_KEY:$OPS_MANAGER_PRIVATE_KEY" --digest \
  -X PUT \
  -H "Content-Type: application/json" \
  -d @current_config_test.json \
  "$OPS_MANAGER_URL/api/public/v1.0/groups/$OPS_MANAGER_PROJECT_ID/automationConfig" \
  -w "\nHTTP_CODE:%{http_code}\n" \
  2>&1 | tail -5

echo ""
echo "If Test 1 succeeded (200), the API works."
echo "If Test 1 failed, there's a different issue."
echo ""

# Test 2: Add ONE simple process
echo "Test 2: Add ONE mongod process..."
python3 << 'EOF'
import json

with open('current_config_test.json') as f:
    config = json.load(f)

# Add ONE simple process
config['processes'] = [{
    "name": "mongodb-01",
    "hostname": "172.31.16.76",
    "processType": "mongod",
    "version": "8.0.17-ent",
    "args2_6": {
        "net": {"port": 27017},
        "storage": {"dbPath": "/data/db"},
        "systemLog": {
            "destination": "file",
            "path": "/var/log/mongodb/mongod.log"
        }
    }
}]

with open('config_with_one_process.json', 'w') as f:
    json.dump(config, f, indent=2)

print("Created config_with_one_process.json")
EOF

curl -u "$OPS_MANAGER_PUBLIC_KEY:$OPS_MANAGER_PRIVATE_KEY" --digest \
  -X PUT \
  -H "Content-Type: application/json" \
  -d @config_with_one_process.json \
  "$OPS_MANAGER_URL/api/public/v1.0/groups/$OPS_MANAGER_PROJECT_ID/automationConfig" \
  -w "\nHTTP_CODE:%{http_code}\n" \
  2>&1 | tail -10

echo ""
echo "=========================================="
echo "Check the HTTP codes above:"
echo "  200 = Success"
echo "  400 = Bad Request (check error message)"
echo "=========================================="
