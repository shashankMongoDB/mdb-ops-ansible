#!/bin/bash

#
# Test Community MongoDB Upgrade
#
# Usage:
#   ./scripts/test-community-upgrade.sh <tenant-id> <deployment-id> <new-version>
#
# Example:
#   ./scripts/test-community-upgrade.sh t-comm monitoring-comm 7.0.15
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
NEW_VERSION="${3:-}"

if [[ -z "$TENANT_ID" ]] || [[ -z "$DEPLOYMENT_ID" ]] || [[ -z "$NEW_VERSION" ]]; then
    echo -e "${RED}Usage: $0 <tenant-id> <deployment-id> <new-version>${NC}"
    echo "Example: $0 t-comm monitoring-comm 7.0.15"
    exit 1
fi

NAMESPACE="mdb-${TENANT_ID}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8001}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Community MongoDB Upgrade Test${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Tenant ID: $TENANT_ID"
echo "Deployment ID: $DEPLOYMENT_ID"
echo "Namespace: $NAMESPACE"
echo "New Version: $NEW_VERSION"
echo "Backend URL: $BACKEND_URL"
echo ""

# ========================================
# 1. Get Current Version from CR
# ========================================
echo -e "${BLUE}[1/6] Checking Current Version in CR...${NC}"
CURRENT_VERSION=$(kubectl get mongodbcommunity "$DEPLOYMENT_ID" -n "$NAMESPACE" -o jsonpath='{.spec.version}' 2>/dev/null || echo "unknown")
if [[ "$CURRENT_VERSION" == "unknown" ]]; then
    echo -e "${RED}❌ MongoDBCommunity CR not found${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Current CR Version: $CURRENT_VERSION${NC}"
echo ""

# ========================================
# 2. Get Current Version from Pods
# ========================================
echo -e "${BLUE}[2/6] Checking Current Version in Pods...${NC}"
PODS=$(kubectl get pods -n "$NAMESPACE" -l "app=${DEPLOYMENT_ID}-svc" --no-headers 2>/dev/null || echo "")
if [[ -z "$PODS" ]]; then
    echo -e "${RED}❌ No pods found${NC}"
    exit 1
fi

echo "$PODS" | while read -r line; do
    POD_NAME=$(echo "$line" | awk '{print $1}')
    POD_VERSION=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -- mongosh --quiet --eval "db.version()" 2>/dev/null || echo "unknown")
    echo "   $POD_NAME: MongoDB $POD_VERSION"
done
echo ""

# ========================================
# 3. Call Upgrade API
# ========================================
echo -e "${BLUE}[3/6] Calling Upgrade API...${NC}"
RESPONSE=$(curl -s -X PATCH "${BACKEND_URL}/tenants/${TENANT_ID}/deployments/${DEPLOYMENT_ID}/version" \
    -H "Content-Type: application/json" \
    -d "{\"mongoVersion\": \"${NEW_VERSION}\"}" \
    -w "\n%{http_code}" 2>&1)

HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [[ "$HTTP_CODE" == "200" ]]; then
    echo -e "${GREEN}✅ API call successful (HTTP $HTTP_CODE)${NC}"
    echo "Response: $BODY"
else
    echo -e "${RED}❌ API call failed (HTTP $HTTP_CODE)${NC}"
    echo "Response: $BODY"
    exit 1
fi
echo ""

# ========================================
# 4. Check CR Version After Patch
# ========================================
echo -e "${BLUE}[4/6] Checking CR Version After Patch...${NC}"
sleep 2  # Wait for patch to apply
NEW_CR_VERSION=$(kubectl get mongodbcommunity "$DEPLOYMENT_ID" -n "$NAMESPACE" -o jsonpath='{.spec.version}' 2>/dev/null || echo "unknown")
if [[ "$NEW_CR_VERSION" == "$NEW_VERSION" ]]; then
    echo -e "${GREEN}✅ CR version updated: $NEW_CR_VERSION${NC}"
elif [[ "$NEW_CR_VERSION" == "$CURRENT_VERSION" ]]; then
    echo -e "${RED}❌ CR version NOT updated (still $CURRENT_VERSION)${NC}"
    echo ""
    echo "Possible issues:"
    echo "1. Backend doesn't have permission to patch MongoDBCommunity CRs"
    echo "2. API call succeeded but patch failed silently"
    echo "3. Wrong namespace or deployment ID"
    echo ""
    echo "Check backend logs:"
    echo "  kubectl logs -n mdbaas-system deployment/mdbaas-backend --tail=50 | grep -i upgrade"
    exit 1
else
    echo -e "${YELLOW}⚠️  CR version is $NEW_CR_VERSION (expected $NEW_VERSION)${NC}"
fi
echo ""

# ========================================
# 5. Check StatefulSet Image
# ========================================
echo -e "${BLUE}[5/6] Checking StatefulSet Image...${NC}"
sleep 5  # Wait for operator to update StatefulSet
IMAGE=$(kubectl get statefulset "$DEPLOYMENT_ID" -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null || echo "unknown")
echo "StatefulSet Image: $IMAGE"
if [[ "$IMAGE" == *"$NEW_VERSION"* ]]; then
    echo -e "${GREEN}✅ StatefulSet image updated${NC}"
else
    echo -e "${YELLOW}⚠️  StatefulSet image not yet updated (operator may be reconciling)${NC}"
fi
echo ""

# ========================================
# 6. Monitor Pod Updates
# ========================================
echo -e "${BLUE}[6/6] Monitoring Pod Updates (10 seconds)...${NC}"
echo "Watch pods being recreated with new version:"
echo ""

for i in {1..10}; do
    echo "Check #$i:"
    kubectl get pods -n "$NAMESPACE" -l "app=${DEPLOYMENT_ID}-svc" --no-headers | while read -r line; do
        POD_NAME=$(echo "$line" | awk '{print $1}')
        POD_STATUS=$(echo "$line" | awk '{print $3}')
        POD_VERSION=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -- mongosh --quiet --eval "db.version()" 2>/dev/null || echo "starting")
        echo "   $POD_NAME: $POD_STATUS | MongoDB $POD_VERSION"
    done
    echo ""
    
    if [[ $i -lt 10 ]]; then
        sleep 1
    fi
done

# ========================================
# Summary
# ========================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

FINAL_CR_VERSION=$(kubectl get mongodbcommunity "$DEPLOYMENT_ID" -n "$NAMESPACE" -o jsonpath='{.spec.version}' 2>/dev/null || echo "unknown")
echo "Initial CR Version: $CURRENT_VERSION"
echo "Target Version: $NEW_VERSION"
echo "Final CR Version: $FINAL_CR_VERSION"
echo ""

# Count upgraded pods
UPGRADED_COUNT=0
TOTAL_COUNT=0
PODS=$(kubectl get pods -n "$NAMESPACE" -l "app=${DEPLOYMENT_ID}-svc" --no-headers 2>/dev/null || echo "")
if [[ -n "$PODS" ]]; then
    while read -r line; do
        POD_NAME=$(echo "$line" | awk '{print $1}')
        POD_VERSION=$(kubectl exec "$POD_NAME" -n "$NAMESPACE" -- mongosh --quiet --eval "db.version()" 2>/dev/null || echo "unknown")
        TOTAL_COUNT=$((TOTAL_COUNT + 1))
        if [[ "$POD_VERSION" == "$NEW_VERSION" ]]; then
            UPGRADED_COUNT=$((UPGRADED_COUNT + 1))
        fi
        echo "Pod: $POD_NAME → $POD_VERSION"
    done <<< "$PODS"
fi
echo ""

if [[ "$FINAL_CR_VERSION" == "$NEW_VERSION" ]]; then
    echo -e "${GREEN}✅ CR updated successfully${NC}"
    if [[ $UPGRADED_COUNT -gt 0 ]]; then
        echo -e "${GREEN}✅ Upgrade in progress: $UPGRADED_COUNT/$TOTAL_COUNT pods upgraded${NC}"
        echo ""
        echo "To monitor progress:"
        echo "  watch kubectl get pods -n $NAMESPACE -l app=${DEPLOYMENT_ID}-svc"
    elif [[ $TOTAL_COUNT -gt 0 ]]; then
        echo -e "${YELLOW}⚠️  CR updated but pods not yet upgraded (operator reconciling)${NC}"
        echo ""
        echo "Check operator logs:"
        echo "  kubectl logs -n mongodb-operator deployment/mongodb-community-operator --tail=50"
    fi
else
    echo -e "${RED}❌ CR was NOT updated${NC}"
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Check backend logs:"
    echo "   kubectl logs -n mdbaas-system deployment/mdbaas-backend --tail=50"
    echo ""
    echo "2. Check RBAC permissions:"
    echo "   kubectl auth can-i patch mongodbcommunity --as=system:serviceaccount:mdbaas-system:mdbaas-backend -n $NAMESPACE"
    echo ""
    echo "3. Try manual patch:"
    echo "   kubectl patch mongodbcommunity $DEPLOYMENT_ID -n $NAMESPACE --type=merge -p '{\"spec\":{\"version\":\"$NEW_VERSION\"}}'"
fi
echo ""

echo -e "${GREEN}Test complete!${NC}"
