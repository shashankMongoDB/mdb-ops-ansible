#!/bin/bash
# Debug deployment status

set -e

cd ~/mdbaas-repo/mdb-ops-ansible/playbooks/cluster_creation/replica_set/
source ../load_env.sh

echo "=========================================="
echo "DEPLOYMENT DEBUG"
echo "=========================================="
echo ""

# 1. Get automation status
echo "1. Automation Status:"
curl -u "$OPS_MANAGER_PUBLIC_KEY:$OPS_MANAGER_PRIVATE_KEY" --digest -s \
  "$OPS_MANAGER_URL/api/public/v1.0/groups/$OPS_MANAGER_PROJECT_ID/automationStatus" \
  | python3 -m json.tool

echo ""
echo "=========================================="
echo ""

# 2. Get current automation config
echo "2. Current Automation Config (processes):"
curl -u "$OPS_MANAGER_PUBLIC_KEY:$OPS_MANAGER_PRIVATE_KEY" --digest -s \
  "$OPS_MANAGER_URL/api/public/v1.0/groups/$OPS_MANAGER_PROJECT_ID/automationConfig" \
  | python3 -c "
import json, sys
config = json.load(sys.stdin)
print('Processes:', len(config.get('processes', [])))
for p in config.get('processes', []):
    print(f\"  - {p.get('name')}: {p.get('hostname')} (disabled={p.get('disabled', 'N/A')}, manualMode={p.get('manualMode', 'N/A')})\")
print('')
print('Replica Sets:', len(config.get('replicaSets', [])))
for rs in config.get('replicaSets', []):
    print(f\"  - {rs.get('_id')}: {len(rs.get('members', []))} members\")
"

echo ""
echo "=========================================="
echo ""

# 3. Check on VMs
echo "3. Checking MongoDB processes on VMs:"
echo ""

for ip in 172.31.16.76 172.31.21.74 172.31.23.234; do
    echo "VM: $ip"
    ssh -i ../sp-k8s.pem -o StrictHostKeyChecking=no ubuntu@$ip "
        echo '  Agent status:'
        sudo systemctl status mongodb-mms-automation-agent --no-pager | head -3 || echo '    Not running'
        echo '  MongoDB process:'
        ps aux | grep mongod | grep -v grep || echo '    No mongod running'
        echo '  Data directory:'
        ls -la /data/db 2>/dev/null | head -5 || echo '    /data/db does not exist'
        echo '  Logs:'
        ls -la /var/log/mongodb-mms-automation/ 2>/dev/null | tail -5 || echo '    No automation logs'
    " 2>/dev/null || echo "  ❌ Cannot connect"
    echo ""
done

echo "=========================================="
echo "NEXT STEPS:"
echo "1. Check if processes are marked as 'disabled: true' → they won't start"
echo "2. Check agent logs: /var/log/mongodb-mms-automation/automation-agent.log"
echo "3. Check if /data/db exists and has correct permissions"
echo "=========================================="
