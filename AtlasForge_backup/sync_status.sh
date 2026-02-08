#!/bin/bash

# Sync Status Script
# This script fetches live status from Kubernetes and updates the control-plane DB

set -e

TENANT_ID="$1"
DEPLOYMENT_ID="$2"

if [ -z "$TENANT_ID" ] || [ -z "$DEPLOYMENT_ID" ]; then
    echo "Usage: $0 <tenant-id> <deployment-id>"
    echo "Example: $0 t-acme rs-orders"
    exit 1
fi

NAMESPACE="mdb-${TENANT_ID}"

echo "=========================================="
echo "Syncing Status for Deployment"
echo "=========================================="
echo "Tenant ID:      $TENANT_ID"
echo "Deployment ID:  $DEPLOYMENT_ID"
echo "Namespace:      $NAMESPACE"
echo ""

# Check if MongoDB CR exists
echo "Checking Kubernetes MongoDB CR..."
if ! kubectl get mongodb "$DEPLOYMENT_ID" -n "$NAMESPACE" &> /dev/null; then
    echo "ERROR: MongoDB CR '$DEPLOYMENT_ID' not found in namespace '$NAMESPACE'"
    exit 1
fi

# Get phase from Kubernetes
K8S_PHASE=$(kubectl get mongodb "$DEPLOYMENT_ID" -n "$NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null || echo "Unknown")

echo "Kubernetes Phase: $K8S_PHASE"
echo ""

# Get additional status info
echo "=========================================="
echo "Kubernetes Status Details"
echo "=========================================="
kubectl get mongodb "$DEPLOYMENT_ID" -n "$NAMESPACE"
echo ""

# Get pod status
echo "=========================================="
echo "Pod Status"
echo "=========================================="
kubectl get pods -n "$NAMESPACE" -l app="${DEPLOYMENT_ID}-svc"
echo ""

# Get detailed status
echo "=========================================="
echo "Detailed MongoDB CR Status"
echo "=========================================="
kubectl get mongodb "$DEPLOYMENT_ID" -n "$NAMESPACE" -o jsonpath='{.status}' | jq '.' 2>/dev/null || echo "No status available"
echo ""

# Update control-plane DB
if [ -n "$MCP_MONGODB_URI" ] && [ "$K8S_PHASE" != "Unknown" ]; then
    echo "=========================================="
    echo "Updating Control Plane Database"
    echo "=========================================="
    
    mongosh "$MCP_MONGODB_URI" --quiet --eval "
        use mdb_control_plane;
        const result = db.deployments.updateOne(
            {_id: '${TENANT_ID}:${DEPLOYMENT_ID}'},
            {\$set: {
                'lastKnownStatus.phase': '${K8S_PHASE}',
                'lastUpdatedAt': new Date().toISOString()
            }}
        );
        print('Matched: ' + result.matchedCount);
        print('Modified: ' + result.modifiedCount);
    " 2>/dev/null || echo "Warning: Could not update control-plane DB (MCP_MONGODB_URI not set or mongosh not available)"
    
    echo ""
fi

# Call control plane API to see updated status
if [ -n "$MCP_SERVICE_PORT" ]; then
    echo "=========================================="
    echo "Control Plane API Response"
    echo "=========================================="
    curl -s "http://localhost:${MCP_SERVICE_PORT:-8001}/tenants/${TENANT_ID}/deployments/${DEPLOYMENT_ID}" | jq '.' 2>/dev/null || echo "API not reachable"
    echo ""
fi

echo "=========================================="
echo "Status Summary"
echo "=========================================="
echo "Kubernetes Phase: $K8S_PHASE"
echo ""
echo "Next Steps:"
if [ "$K8S_PHASE" == "Running" ]; then
    echo "✅ Deployment is Running!"
    echo "   - Check Ops Manager UI for monitoring"
    echo "   - Get connection string from Ops Manager"
    echo "   - Test connectivity with mongosh"
elif [ "$K8S_PHASE" == "Pending" ]; then
    echo "⏳ Deployment is Pending"
    echo "   - Wait a few more minutes"
    echo "   - Check pod logs: kubectl logs ${DEPLOYMENT_ID}-0 -n ${NAMESPACE} -c mongodb-agent"
    echo "   - Check events: kubectl describe mongodb ${DEPLOYMENT_ID} -n ${NAMESPACE}"
elif [ "$K8S_PHASE" == "Failed" ]; then
    echo "❌ Deployment Failed!"
    echo "   - Check pod status: kubectl get pods -n ${NAMESPACE}"
    echo "   - Check pod logs: kubectl logs ${DEPLOYMENT_ID}-0 -n ${NAMESPACE} -c mongodb-agent"
    echo "   - Check events: kubectl describe mongodb ${DEPLOYMENT_ID} -n ${NAMESPACE}"
    echo "   - Check Ops Manager for alerts"
else
    echo "❓ Status Unknown"
    echo "   - Check if MongoDB CR exists: kubectl get mongodb -n ${NAMESPACE}"
    echo "   - Check if operator is running: kubectl get pods -n mongodb"
fi
echo "=========================================="
