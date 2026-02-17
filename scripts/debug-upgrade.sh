#!/bin/bash

#
# Upgrade Troubleshooting Debug Script
#
# Usage:
#   ./scripts/debug-upgrade.sh <tenant-id> <deployment-id>
#
# Example:
#   ./scripts/debug-upgrade.sh test-tenant rs-orders
#

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

TENANT_ID="${1:-}"
DEPLOYMENT_ID="${2:-}"

if [[ -z "$TENANT_ID" ]] || [[ -z "$DEPLOYMENT_ID" ]]; then
    echo -e "${RED}Usage: $0 <tenant-id> <deployment-id>${NC}"
    echo "Example: $0 test-tenant rs-orders"
    exit 1
fi

NAMESPACE="mdb-${TENANT_ID}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8001}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Upgrade Troubleshooting Debug Report${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Tenant ID: $TENANT_ID"
echo "Deployment ID: $DEPLOYMENT_ID"
echo "Namespace: $NAMESPACE"
echo "Backend URL: $BACKEND_URL"
echo ""

# ========================================
# 1. Backend Health Check
# ========================================
echo -e "${BLUE}[1/10] Checking Backend Health...${NC}"
if curl -sf "${BACKEND_URL}/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend is reachable${NC}"
else
    echo -e "${RED}❌ Backend is NOT reachable at ${BACKEND_URL}${NC}"
    echo "   Please check if backend is running:"
    echo "   - Local: ps aux | grep uvicorn"
    echo "   - K8s: kubectl get pods -n mdbaas-system -l app=mdbaas-backend"
    exit 1
fi
echo ""

# ========================================
# 2. CORS Check
# ========================================
echo -e "${BLUE}[2/10] Checking CORS Configuration...${NC}"
CORS_HEADER=$(curl -s -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS "${BACKEND_URL}/health" \
     -i 2>/dev/null | grep -i "access-control-allow-origin" || echo "")

if [[ -n "$CORS_HEADER" ]]; then
    echo -e "${GREEN}✅ CORS is enabled${NC}"
    echo "   $CORS_HEADER"
else
    echo -e "${YELLOW}⚠️  CORS headers not found${NC}"
    echo "   This might cause Network Error in UI"
fi
echo ""

# ========================================
# 3. Tenant Check
# ========================================
echo -e "${BLUE}[3/10] Checking Tenant...${NC}"
if curl -sf "${BACKEND_URL}/tenants/${TENANT_ID}" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Tenant exists${NC}"
    TENANT_PLAN=$(curl -s "${BACKEND_URL}/tenants/${TENANT_ID}" | grep -o '"plan":"[^"]*"' | cut -d'"' -f4)
    echo "   Plan: $TENANT_PLAN"
else
    echo -e "${RED}❌ Tenant not found${NC}"
    exit 1
fi
echo ""

# ========================================
# 4. Deployment Check
# ========================================
echo -e "${BLUE}[4/10] Checking Deployment...${NC}"
if curl -sf "${BACKEND_URL}/tenants/${TENANT_ID}/deployments/${DEPLOYMENT_ID}" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Deployment exists${NC}"
    DEPLOYMENT_VERSION=$(curl -s "${BACKEND_URL}/tenants/${TENANT_ID}/deployments/${DEPLOYMENT_ID}" | grep -o '"mongoVersion":"[^"]*"' | cut -d'"' -f4)
    echo "   Version in DB: $DEPLOYMENT_VERSION"
else
    echo -e "${RED}❌ Deployment not found${NC}"
    exit 1
fi
echo ""

# ========================================
# 5. Namespace Check
# ========================================
echo -e "${BLUE}[5/10] Checking Namespace...${NC}"
if kubectl get namespace "$NAMESPACE" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Namespace exists${NC}"
else
    echo -e "${RED}❌ Namespace not found${NC}"
    exit 1
fi
echo ""

# ========================================
# 6. MongoDB CR Check
# ========================================
echo -e "${BLUE}[6/10] Checking MongoDB CR...${NC}"

# Try enterprise first
if kubectl get mongodb "$DEPLOYMENT_ID" -n "$NAMESPACE" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ MongoDB CR exists (Enterprise)${NC}"
    CR_VERSION=$(kubectl get mongodb "$DEPLOYMENT_ID" -n "$NAMESPACE" -o jsonpath='{.spec.version}' 2>/dev/null || echo "unknown")
    CR_STATUS=$(kubectl get mongodb "$DEPLOYMENT_ID" -n "$NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null || echo "unknown")
    echo "   CR Version: $CR_VERSION"
    echo "   CR Status: $CR_STATUS"
    
    if [[ "$CR_VERSION" != "$DEPLOYMENT_VERSION" ]]; then
        echo -e "${YELLOW}   ⚠️  CR version ($CR_VERSION) differs from DB version ($DEPLOYMENT_VERSION)${NC}"
    fi
# Try community
elif kubectl get mongodbcommunity "$DEPLOYMENT_ID" -n "$NAMESPACE" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ MongoDB CR exists (Community)${NC}"
    CR_VERSION=$(kubectl get mongodbcommunity "$DEPLOYMENT_ID" -n "$NAMESPACE" -o jsonpath='{.spec.version}' 2>/dev/null || echo "unknown")
    CR_STATUS=$(kubectl get mongodbcommunity "$DEPLOYMENT_ID" -n "$NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null || echo "unknown")
    echo "   CR Version: $CR_VERSION"
    echo "   CR Status: $CR_STATUS"
    
    if [[ "$CR_VERSION" != "$DEPLOYMENT_VERSION" ]]; then
        echo -e "${YELLOW}   ⚠️  CR version ($CR_VERSION) differs from DB version ($DEPLOYMENT_VERSION)${NC}"
    fi
else
    echo -e "${RED}❌ MongoDB CR not found${NC}"
    echo "   Tried both 'mongodb' and 'mongodbcommunity' resources"
    exit 1
fi
echo ""

# ========================================
# 7. Operator Check
# ========================================
echo -e "${BLUE}[7/10] Checking Operator...${NC}"
OPERATOR_PODS=$(kubectl get pods -n mongodb-operator --no-headers 2>/dev/null | wc -l || echo "0")
if [[ "$OPERATOR_PODS" -gt 0 ]]; then
    echo -e "${GREEN}✅ Operator pods found: $OPERATOR_PODS${NC}"
    kubectl get pods -n mongodb-operator --no-headers | while read -r line; do
        POD_NAME=$(echo "$line" | awk '{print $1}')
        POD_STATUS=$(echo "$line" | awk '{print $3}')
        echo "   $POD_NAME: $POD_STATUS"
    done
else
    echo -e "${RED}❌ No operator pods found${NC}"
    echo "   Operator might not be installed or running"
fi
echo ""

# ========================================
# 8. StatefulSet Check
# ========================================
echo -e "${BLUE}[8/10] Checking StatefulSet...${NC}"
if kubectl get statefulset "$DEPLOYMENT_ID" -n "$NAMESPACE" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ StatefulSet exists${NC}"
    
    # Get image version
    IMAGE=$(kubectl get statefulset "$DEPLOYMENT_ID" -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null || echo "unknown")
    echo "   Image: $IMAGE"
    
    # Get replicas
    REPLICAS=$(kubectl get statefulset "$DEPLOYMENT_ID" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "unknown")
    READY=$(kubectl get statefulset "$DEPLOYMENT_ID" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
    echo "   Replicas: $READY/$REPLICAS ready"
else
    echo -e "${YELLOW}⚠️  StatefulSet not found${NC}"
    echo "   Deployment might be starting or in an error state"
fi
echo ""

# ========================================
# 9. Pod Check
# ========================================
echo -e "${BLUE}[9/10] Checking Pods...${NC}"
PODS=$(kubectl get pods -n "$NAMESPACE" -l "app=${DEPLOYMENT_ID}-svc" --no-headers 2>/dev/null || echo "")
if [[ -n "$PODS" ]]; then
    echo -e "${GREEN}✅ Pods found${NC}"
    echo "$PODS" | while read -r line; do
        POD_NAME=$(echo "$line" | awk '{print $1}')
        POD_STATUS=$(echo "$line" | awk '{print $3}')
        POD_READY=$(echo "$line" | awk '{print $2}')
        
        # Get MongoDB version from pod
        POD_VERSION=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -- mongosh --quiet --eval "db.version()" 2>/dev/null || echo "unknown")
        
        echo "   $POD_NAME: $POD_STATUS ($POD_READY ready) - MongoDB $POD_VERSION"
    done
else
    echo -e "${YELLOW}⚠️  No pods found${NC}"
fi
echo ""

# ========================================
# 10. Node Resources Check
# ========================================
echo -e "${BLUE}[10/10] Checking Node Resources...${NC}"
if command -v kubectl &> /dev/null && kubectl top nodes &> /dev/null; then
    echo -e "${GREEN}✅ Node metrics available${NC}"
    kubectl top nodes
    echo ""
    
    # Check if any node is over 80% CPU
    HIGH_CPU=$(kubectl top nodes --no-headers | awk '{gsub("%","",$3); if($3>80) print $1}')
    if [[ -n "$HIGH_CPU" ]]; then
        echo -e "${YELLOW}⚠️  Warning: High CPU usage detected on nodes:${NC}"
        echo "$HIGH_CPU"
        echo "   Consider adding more worker nodes or increasing node size"
    fi
else
    echo -e "${YELLOW}⚠️  Node metrics not available (metrics-server might not be installed)${NC}"
fi
echo ""

# ========================================
# Summary
# ========================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Summary & Recommendations${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check version mismatch
if [[ -n "${CR_VERSION:-}" ]] && [[ "$CR_VERSION" != "$DEPLOYMENT_VERSION" ]]; then
    echo -e "${YELLOW}⚠️  Version Mismatch Detected!${NC}"
    echo "   Database says: $DEPLOYMENT_VERSION"
    echo "   CR says: $CR_VERSION"
    echo ""
    echo "   This means either:"
    echo "   1. Upgrade is in progress (versions will converge soon)"
    echo "   2. Backend failed to patch CR (check RBAC permissions)"
    echo ""
    echo "   To manually patch CR:"
    echo "   kubectl patch mongodb $DEPLOYMENT_ID -n $NAMESPACE --type=merge -p '{\"spec\":{\"version\":\"$DEPLOYMENT_VERSION\"}}'"
    echo ""
fi

# Check if upgrade is in progress
if [[ -n "$PODS" ]]; then
    UNIQUE_VERSIONS=$(echo "$PODS" | while read -r line; do
        POD_NAME=$(echo "$line" | awk '{print $1}')
        kubectl exec "$POD_NAME" -n "$NAMESPACE" -- mongosh --quiet --eval "db.version()" 2>/dev/null || echo "unknown"
    done | sort -u | wc -l)
    
    if [[ "$UNIQUE_VERSIONS" -gt 1 ]]; then
        echo -e "${YELLOW}⏳ Upgrade In Progress!${NC}"
        echo "   Multiple MongoDB versions detected across replicas"
        echo "   This is normal during a rolling upgrade"
        echo ""
    fi
fi

# Connection info test
echo -e "${BLUE}Testing Connection Info API...${NC}"
if curl -sf "${BACKEND_URL}/tenants/${TENANT_ID}/deployments/${DEPLOYMENT_ID}/connection-info" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Connection info API works${NC}"
else
    echo -e "${RED}❌ Connection info API failed${NC}"
    echo "   This is why UI shows 'Upgrade monitoring failed: Network Error'"
    echo ""
    echo "   Possible causes:"
    echo "   1. Deployment is shutdown"
    echo "   2. No external service exists"
    echo "   3. Backend can't reach MongoDB"
fi
echo ""

echo -e "${GREEN}Debug report complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Review the warnings/errors above"
echo "2. Check operator logs: kubectl logs -n mongodb-operator deployment/mongodb-enterprise-operator --tail=50"
echo "3. Check backend logs: kubectl logs -n mdbaas-system deployment/mdbaas-backend --tail=50"
echo "4. Check pod events: kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | tail -20"
