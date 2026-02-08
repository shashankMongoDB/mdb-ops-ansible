#!/bin/bash

# Test script to verify multiple deployments per tenant work correctly

BASE_URL="http://localhost:8001"
TENANT_ID="t-test-multi"

echo "=========================================="
echo "Multi-Deployment Test"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. Create tenant
echo -e "${YELLOW}1. Creating tenant: $TENANT_ID${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/tenants" \
  -H "Content-Type: application/json" \
  -d "{
    \"tenantId\": \"$TENANT_ID\",
    \"displayName\": \"Multi-Deployment Test Tenant\"
  }")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "409" ]; then
    echo -e "${GREEN}✓ Tenant created or already exists${NC}"
    echo "$BODY" | jq '.'
else
    echo -e "${RED}✗ Failed to create tenant (HTTP $HTTP_CODE)${NC}"
    echo "$BODY"
    exit 1
fi
echo ""
sleep 2

# 2. Create first deployment
echo -e "${YELLOW}2. Creating first deployment: rs-orders${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/tenants/$TENANT_ID/deployments" \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentId": "rs-orders",
    "type": "ReplicaSet",
    "mongoVersion": "8.0.3",
    "members": 3,
    "displayName": "Orders Database",
    "environment": "prod"
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "201" ]; then
    echo -e "${GREEN}✓ First deployment created successfully${NC}"
    echo "$BODY" | jq '.'
else
    echo -e "${RED}✗ Failed to create first deployment (HTTP $HTTP_CODE)${NC}"
    echo "$BODY"
    exit 1
fi
echo ""
sleep 2

# 3. Create second deployment
echo -e "${YELLOW}3. Creating second deployment: rs-customers${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/tenants/$TENANT_ID/deployments" \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentId": "rs-customers",
    "type": "ReplicaSet",
    "mongoVersion": "8.0.3",
    "members": 3,
    "displayName": "Customers Database",
    "environment": "prod"
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "201" ]; then
    echo -e "${GREEN}✓ Second deployment created successfully${NC}"
    echo "$BODY" | jq '.'
else
    echo -e "${RED}✗ Failed to create second deployment (HTTP $HTTP_CODE)${NC}"
    echo "$BODY"
    echo ""
    echo "This is the regression! Second deployment should work."
    exit 1
fi
echo ""
sleep 2

# 4. Create third deployment
echo -e "${YELLOW}4. Creating third deployment: rs-analytics${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/tenants/$TENANT_ID/deployments" \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentId": "rs-analytics",
    "type": "ReplicaSet",
    "mongoVersion": "8.0.3",
    "members": 5,
    "displayName": "Analytics Database",
    "environment": "staging"
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "201" ]; then
    echo -e "${GREEN}✓ Third deployment created successfully${NC}"
    echo "$BODY" | jq '.'
else
    echo -e "${RED}✗ Failed to create third deployment (HTTP $HTTP_CODE)${NC}"
    echo "$BODY"
    exit 1
fi
echo ""
sleep 2

# 5. List all deployments
echo -e "${YELLOW}5. Listing all deployments for tenant${NC}"
RESPONSE=$(curl -s -X GET "$BASE_URL/tenants/$TENANT_ID/deployments")
echo "$RESPONSE" | jq '.'

DEPLOYMENT_COUNT=$(echo "$RESPONSE" | jq '. | length')
echo ""
echo "Total deployments: $DEPLOYMENT_COUNT"

if [ "$DEPLOYMENT_COUNT" -ge 3 ]; then
    echo -e "${GREEN}✓ Multiple deployments per tenant working correctly!${NC}"
else
    echo -e "${RED}✗ Expected at least 3 deployments, got $DEPLOYMENT_COUNT${NC}"
    exit 1
fi
echo ""

# 6. Verify in Kubernetes
echo -e "${YELLOW}6. Verifying MongoDB CRs in Kubernetes${NC}"
NAMESPACE="mdb-${TENANT_ID}"
echo "Namespace: $NAMESPACE"
echo ""

echo "MongoDB CRs:"
kubectl get mongodb -n "$NAMESPACE" 2>/dev/null || echo "  (namespace not found or no CRs)"
echo ""

echo "Pods:"
kubectl get pods -n "$NAMESPACE" 2>/dev/null || echo "  (no pods yet)"
echo ""

echo "=========================================="
echo -e "${GREEN}Test Complete!${NC}"
echo "=========================================="
echo ""
echo "Summary:"
echo "  ✓ Tenant created"
echo "  ✓ Multiple deployments created for same tenant"
echo "  ✓ All deployments listed correctly"
echo ""
echo "Check Kubernetes for resources:"
echo "  kubectl get mongodb -n $NAMESPACE"
echo "  kubectl get pods -n $NAMESPACE"
echo "  kubectl get statefulset -n $NAMESPACE"
