#!/bin/bash
# Test Ops Manager API Access
# This script helps diagnose 403 Forbidden errors

set -e

echo "=========================================="
echo "Ops Manager API Access Diagnostic"
echo "=========================================="
echo ""

# Load environment
if [ -f "../.env" ]; then
    source ../.env
    echo "✅ Loaded .env file"
else
    echo "❌ .env file not found"
    exit 1
fi

echo ""
echo "Configuration:"
echo "  Ops Manager: $OPS_MANAGER_URL"
echo "  Public Key: $OPS_MANAGER_PUBLIC_KEY"
echo "  Project ID: $OPS_MANAGER_PROJECT_ID"
echo ""

# Get control node IP
CONTROL_IP=$(hostname -I | awk '{print $1}')
echo "Control Node IP: $CONTROL_IP"
echo ""

echo "=========================================="
echo "Test 1: Check Ops Manager Reachability"
echo "=========================================="
if curl -s -o /dev/null -w "%{http_code}" "$OPS_MANAGER_URL" | grep -q "200\|301\|302"; then
    echo "✅ Ops Manager is reachable"
else
    echo "❌ Cannot reach Ops Manager"
    exit 1
fi
echo ""

echo "=========================================="
echo "Test 2: Test API Authentication"
echo "=========================================="
echo "Endpoint: GET /api/public/v1.0/groups/$OPS_MANAGER_PROJECT_ID"
echo ""

RESPONSE=$(curl -u "$OPS_MANAGER_PUBLIC_KEY:$OPS_MANAGER_PRIVATE_KEY" \
  --digest \
  -s -w "\nHTTP_CODE:%{http_code}" \
  "$OPS_MANAGER_URL/api/public/v1.0/groups/$OPS_MANAGER_PROJECT_ID")

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE")

echo "HTTP Status: $HTTP_CODE"
echo ""

if [ "$HTTP_CODE" == "200" ]; then
    echo "✅ API Authentication SUCCESSFUL"
    echo ""
    echo "Project Details:"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
elif [ "$HTTP_CODE" == "403" ]; then
    echo "❌ 403 FORBIDDEN - Access Denied"
    echo ""
    echo "Response:"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    echo ""
    echo "Possible Issues:"
    echo "  1. IP $CONTROL_IP not in API access list"
    echo "  2. API key doesn't have required permissions"
    echo "  3. API key is an Agent key (not Programmatic key)"
    echo ""
    echo "Fix:"
    echo "  1. Go to Ops Manager UI"
    echo "  2. Admin → Settings → Security → Global API Access List"
    echo "  3. Add IP: $CONTROL_IP/32 or CIDR: 172.31.0.0/16"
    echo "  4. Save and wait 30 seconds"
elif [ "$HTTP_CODE" == "401" ]; then
    echo "❌ 401 UNAUTHORIZED - Invalid Credentials"
    echo ""
    echo "Check:"
    echo "  - OPS_MANAGER_PUBLIC_KEY=$OPS_MANAGER_PUBLIC_KEY"
    echo "  - OPS_MANAGER_PRIVATE_KEY in .env file"
else
    echo "❌ Unexpected HTTP Code: $HTTP_CODE"
    echo ""
    echo "Response:"
    echo "$BODY"
fi

echo ""

if [ "$HTTP_CODE" != "200" ]; then
    exit 1
fi

echo "=========================================="
echo "Test 3: Check API Key Type"
echo "=========================================="
echo "Checking if this is a Programmatic API key..."
echo ""

# Try to get user info (only works with programmatic keys)
USER_RESPONSE=$(curl -u "$OPS_MANAGER_PUBLIC_KEY:$OPS_MANAGER_PRIVATE_KEY" \
  --digest \
  -s -w "\nHTTP_CODE:%{http_code}" \
  "$OPS_MANAGER_URL/api/public/v1.0/user" 2>/dev/null)

USER_HTTP_CODE=$(echo "$USER_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)

if [ "$USER_HTTP_CODE" == "200" ]; then
    echo "✅ This is a Programmatic API Key"
elif [ "$USER_HTTP_CODE" == "403" ]; then
    echo "⚠️  This might be an Agent API Key (limited permissions)"
    echo ""
    echo "Agent API Keys can only:"
    echo "  - Be used by automation agents"
    echo "  - NOT make general API calls"
    echo ""
    echo "You need a Programmatic API Key for automation."
else
    echo "⚠️  Unable to determine key type (HTTP $USER_HTTP_CODE)"
fi

echo ""

echo "=========================================="
echo "Test 4: Check Automation Config Access"
echo "=========================================="
echo "Endpoint: GET /api/public/v1.0/groups/$OPS_MANAGER_PROJECT_ID/automationConfig"
echo ""

AUTO_RESPONSE=$(curl -u "$OPS_MANAGER_PUBLIC_KEY:$OPS_MANAGER_PRIVATE_KEY" \
  --digest \
  -s -w "\nHTTP_CODE:%{http_code}" \
  "$OPS_MANAGER_URL/api/public/v1.0/groups/$OPS_MANAGER_PROJECT_ID/automationConfig")

AUTO_HTTP_CODE=$(echo "$AUTO_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)

echo "HTTP Status: $AUTO_HTTP_CODE"
echo ""

if [ "$AUTO_HTTP_CODE" == "200" ]; then
    echo "✅ Can read automation config"
    AUTO_BODY=$(echo "$AUTO_RESPONSE" | grep -v "HTTP_CODE")
    VERSION=$(echo "$AUTO_BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('version', 'unknown'))" 2>/dev/null || echo "unknown")
    echo "Current config version: $VERSION"
elif [ "$AUTO_HTTP_CODE" == "403" ]; then
    echo "❌ 403 FORBIDDEN - Cannot read automation config"
    echo ""
    echo "This endpoint requires:"
    echo "  1. IP whitelisting (already checked)"
    echo "  2. Project-level permissions"
    echo ""
    echo "Check:"
    echo "  - Is this API key added to the project?"
    echo "  - Does it have 'Project Automation Admin' role?"
else
    echo "❌ HTTP $AUTO_HTTP_CODE"
fi

echo ""

echo "=========================================="
echo "Summary"
echo "=========================================="
if [ "$HTTP_CODE" == "200" ] && [ "$AUTO_HTTP_CODE" == "200" ]; then
    echo "✅ ALL TESTS PASSED"
    echo ""
    echo "API access is working correctly!"
    echo "You can now run the deployment playbook:"
    echo "  ansible-playbook -i inventory_simple.yml 2_deploy_replica_set_secure.yml"
else
    echo "❌ SOME TESTS FAILED"
    echo ""
    echo "Issues found:"
    if [ "$HTTP_CODE" != "200" ]; then
        echo "  - Cannot access project API ($HTTP_CODE)"
    fi
    if [ "$AUTO_HTTP_CODE" != "200" ]; then
        echo "  - Cannot access automation config ($AUTO_HTTP_CODE)"
    fi
    echo ""
    echo "Next steps:"
    echo "  1. Verify IP $CONTROL_IP is in global access list"
    echo "  2. Verify API key has project permissions"
    echo "  3. Verify using Programmatic API key (not Agent key)"
fi

echo "=========================================="
