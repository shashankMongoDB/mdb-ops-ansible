#!/bin/bash
# Get current automation config from Ops Manager to see the structure

set -e

# Load environment
source ../load_env.sh

echo "Getting current automation config from Ops Manager..."
echo ""

curl -u "$OPS_MANAGER_PUBLIC_KEY:$OPS_MANAGER_PRIVATE_KEY" \
  --digest \
  -s \
  "$OPS_MANAGER_URL/api/public/v1.0/groups/$OPS_MANAGER_PROJECT_ID/automationConfig" \
  | python3 -m json.tool > current_automation_config.json

echo "✅ Saved to: current_automation_config.json"
echo ""
echo "Current config structure:"
python3 -c "
import json
with open('current_automation_config.json') as f:
    config = json.load(f)
    print('Top-level keys:', list(config.keys()))
    print('')
    if 'auth' in config:
        print('auth section:', config['auth'])
    if 'authSchemaVersion' in config:
        print('authSchemaVersion:', config['authSchemaVersion'])
    print('')
    print('version:', config.get('version'))
    print('processes count:', len(config.get('processes', [])))
    print('replicaSets count:', len(config.get('replicaSets', [])))
"

echo ""
echo "Full config saved in current_automation_config.json"
echo "Review it to see the exact structure Ops Manager expects"
