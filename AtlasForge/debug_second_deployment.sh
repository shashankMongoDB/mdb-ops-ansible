#!/bin/bash

# Debug script to understand why second deployment fails

BASE_URL="http://localhost:8001"
TENANT_ID="t-debug-test"

echo "=========================================="
echo "Debug: Second Deployment Failure"
echo "=========================================="
echo ""

# 1. Create fresh tenant
echo "1. Creating fresh tenant: $TENANT_ID"
curl -s -X POST "$BASE_URL/tenants" \
  -H "Content-Type: application/json" \
  -d "{
    \"tenantId\": \"$TENANT_ID\",
    \"displayName\": \"Debug Test Tenant\"
  }" | jq '.'
echo ""
sleep 2

# 2. Create FIRST deployment
echo "2. Creating FIRST deployment: rs-first"
FIRST_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/tenants/$TENANT_ID/deployments" \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentId": "rs-first",
    "type": "ReplicaSet",
    "mongoVersion": "8.0.3",
    "members": 3,
    "displayName": "First Database",
    "environment": "prod"
  }')

FIRST_HTTP=$(echo "$FIRST_RESPONSE" | tail -n1)
FIRST_BODY=$(echo "$FIRST_RESPONSE" | sed '$d')

echo "HTTP Code: $FIRST_HTTP"
echo "Response:"
echo "$FIRST_BODY" | jq '.'
echo ""

if [ "$FIRST_HTTP" != "201" ]; then
    echo "❌ FIRST deployment failed! HTTP $FIRST_HTTP"
    exit 1
fi

echo "✅ First deployment created"
echo ""
sleep 3

# 3. Check MongoDB in control plane DB
echo "3. Checking control-plane MongoDB database..."
echo "Documents in deployments collection for $TENANT_ID:"
echo ""

# 4. Check Kubernetes
echo "4. Checking Kubernetes resources..."
NAMESPACE="mdb-${TENANT_ID}"
echo "Namespace: $NAMESPACE"
kubectl get mongodb -n "$NAMESPACE" 2>/dev/null
echo ""

# 5. Create SECOND deployment
echo "5. Creating SECOND deployment: rs-second"
SECOND_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/tenants/$TENANT_ID/deployments" \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentId": "rs-second",
    "type": "ReplicaSet",
    "mongoVersion": "8.0.3",
    "members": 3,
    "displayName": "Second Database",
    "environment": "prod"
  }')

SECOND_HTTP=$(echo "$SECOND_RESPONSE" | tail -n1)
SECOND_BODY=$(echo "$SECOND_RESPONSE" | sed '$d')

echo "HTTP Code: $SECOND_HTTP"
echo "Response:"
echo "$SECOND_BODY" | jq '.'
echo ""

if [ "$SECOND_HTTP" != "201" ]; then
    echo "❌ SECOND deployment FAILED! HTTP $SECOND_HTTP"
    echo "This is the regression!"
    echo ""
    echo "Error details:"
    echo "$SECOND_BODY"
else
    echo "✅ Second deployment created successfully"
fi
echo ""
sleep 3

# 6. List all deployments
echo "6. Listing all deployments via API..."
curl -s "$BASE_URL/tenants/$TENANT_ID/deployments" | jq '.'
echo ""

# 7. Check Kubernetes again
echo "7. Final Kubernetes check..."
kubectl get mongodb -n "$NAMESPACE" 2>/dev/null
echo ""
kubectl get pods -n "$NAMESPACE" 2>/dev/null
echo ""

echo "=========================================="
echo "Debug Complete"
echo "=========================================="
echo ""
echo "Check service logs for detailed error messages:"
echo "  tail -f <your-service-log>"
echo ""
echo "The logs should show:"
echo "  - INFO: Creating deployment - tenantId: $TENANT_ID, deploymentId: rs-second"
echo "  - ERROR: (if any)"
