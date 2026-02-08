#!/bin/bash

# MongoDB Control Plane - API Test Script
# This script tests all API endpoints with sample data

BASE_URL="http://localhost:8001"

echo "=========================================="
echo "MongoDB Control Plane API Test Suite"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Health Check
echo -e "${YELLOW}1. Testing Health Check...${NC}"
curl -s -X GET "$BASE_URL/health" | jq '.'
echo -e "${GREEN}✓ Health check complete${NC}"
echo ""
sleep 1

# 2. Create First Tenant
echo -e "${YELLOW}2. Creating Tenant: t-acme${NC}"
curl -s -X POST "$BASE_URL/tenants" \
  -H "Content-Type: application/json" \
  -d '{
    "tenantId": "t-acme",
    "displayName": "Acme Corporation"
  }' | jq '.'
echo -e "${GREEN}✓ Tenant created${NC}"
echo ""
sleep 2

# 3. Create Second Tenant
echo -e "${YELLOW}3. Creating Tenant: t-globex${NC}"
curl -s -X POST "$BASE_URL/tenants" \
  -H "Content-Type: application/json" \
  -d '{
    "tenantId": "t-globex",
    "displayName": "Globex Industries"
  }' | jq '.'
echo -e "${GREEN}✓ Tenant created${NC}"
echo ""
sleep 2

# 4. Create First Deployment
echo -e "${YELLOW}4. Creating Deployment: rs-orders (for t-acme)${NC}"
curl -s -X POST "$BASE_URL/tenants/t-acme/deployments" \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentId": "rs-orders",
    "mongoVersion": "8.0.3",
    "members": 3,
    "displayName": "Orders Database",
    "environment": "prod"
  }' | jq '.'
echo -e "${GREEN}✓ Deployment created${NC}"
echo ""
sleep 2

# 5. Create Second Deployment
echo -e "${YELLOW}5. Creating Deployment: rs-customers (for t-acme)${NC}"
curl -s -X POST "$BASE_URL/tenants/t-acme/deployments" \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentId": "rs-customers",
    "mongoVersion": "8.0.3",
    "members": 3,
    "displayName": "Customers Database",
    "environment": "prod"
  }' | jq '.'
echo -e "${GREEN}✓ Deployment created${NC}"
echo ""
sleep 2

# 6. Create Third Deployment (different config)
echo -e "${YELLOW}6. Creating Deployment: rs-analytics (for t-acme, 5 members)${NC}"
curl -s -X POST "$BASE_URL/tenants/t-acme/deployments" \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentId": "rs-analytics",
    "mongoVersion": "7.0.14",
    "members": 5,
    "displayName": "Analytics Database",
    "environment": "staging"
  }' | jq '.'
echo -e "${GREEN}✓ Deployment created${NC}"
echo ""
sleep 2

# 7. List All Deployments for Tenant
echo -e "${YELLOW}7. Listing all deployments for t-acme${NC}"
curl -s -X GET "$BASE_URL/tenants/t-acme/deployments" | jq '.'
echo -e "${GREEN}✓ Deployments listed${NC}"
echo ""
sleep 1

# 8. Get Specific Deployment Details
echo -e "${YELLOW}8. Getting details for deployment: rs-orders${NC}"
curl -s -X GET "$BASE_URL/tenants/t-acme/deployments/rs-orders" | jq '.'
echo -e "${GREEN}✓ Deployment details retrieved${NC}"
echo ""
sleep 1

# 9. Test Error: Duplicate Tenant
echo -e "${YELLOW}9. Testing Error Case: Duplicate Tenant (should return 409)${NC}"
curl -s -X POST "$BASE_URL/tenants" \
  -H "Content-Type: application/json" \
  -d '{
    "tenantId": "t-acme",
    "displayName": "Acme Corp Duplicate"
  }' | jq '.'
echo -e "${RED}✓ Expected 409 error received${NC}"
echo ""
sleep 1

# 10. Test Error: Invalid Tenant ID
echo -e "${YELLOW}10. Testing Error Case: Invalid Tenant ID (should return 400)${NC}"
curl -s -X POST "$BASE_URL/tenants" \
  -H "Content-Type: application/json" \
  -d '{
    "tenantId": "T_ACME_INVALID!",
    "displayName": "Invalid Tenant"
  }' | jq '.'
echo -e "${RED}✓ Expected 400 error received${NC}"
echo ""
sleep 1

# 11. Test Error: Tenant Not Found
echo -e "${YELLOW}11. Testing Error Case: Tenant Not Found (should return 404)${NC}"
curl -s -X POST "$BASE_URL/tenants/t-nonexistent/deployments" \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentId": "rs-test",
    "mongoVersion": "8.0.3",
    "members": 3,
    "displayName": "Test DB",
    "environment": "dev"
  }' | jq '.'
echo -e "${RED}✓ Expected 404 error received${NC}"
echo ""
sleep 1

# 12. Test Error: Duplicate Deployment
echo -e "${YELLOW}12. Testing Error Case: Duplicate Deployment (should return 409)${NC}"
curl -s -X POST "$BASE_URL/tenants/t-acme/deployments" \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentId": "rs-orders",
    "mongoVersion": "8.0.3",
    "members": 3,
    "displayName": "Orders DB Duplicate",
    "environment": "prod"
  }' | jq '.'
echo -e "${RED}✓ Expected 409 error received${NC}"
echo ""

echo "=========================================="
echo -e "${GREEN}All API tests completed!${NC}"
echo "=========================================="
echo ""
echo "To verify in Kubernetes, run:"
echo "  kubectl get namespaces | grep mdb-"
echo "  kubectl get mongodb -n mdb-t-acme"
echo "  kubectl describe mongodb rs-orders -n mdb-t-acme"
echo ""
echo "To verify in MongoDB, run:"
echo "  mongosh \"\$MCP_MONGODB_URI\""
echo "  use mdb_control_plane"
echo "  db.tenants.find().pretty()"
echo "  db.deployments.find().pretty()"
