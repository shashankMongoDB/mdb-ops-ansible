#!/bin/bash

NAMESPACE="mdb-test1"
TENANT_ID="test1"

echo "=========================================="
echo "Ops Manager Connection Check"
echo "=========================================="
echo ""

# 1. Check ConfigMap
echo "1. Checking Ops Manager ConfigMap:"
kubectl get configmap om-${TENANT_ID}-project -n $NAMESPACE -o yaml
echo ""

# 2. Check Secret (without showing actual keys)
echo "2. Checking Ops Manager Credentials Secret:"
kubectl get secret om-${TENANT_ID}-credentials -n $NAMESPACE -o jsonpath='{.data.user}' | base64 -d
echo " (public key)"
echo ""

# 3. Test Ops Manager connectivity from your machine
echo "3. Testing Ops Manager API connectivity:"
OM_URL=$(kubectl get configmap om-${TENANT_ID}-project -n $NAMESPACE -o jsonpath='{.data.baseUrl}')
OM_USER=$(kubectl get secret om-${TENANT_ID}-credentials -n $NAMESPACE -o jsonpath='{.data.user}' | base64 -d)
OM_KEY=$(kubectl get secret om-${TENANT_ID}-credentials -n $NAMESPACE -o jsonpath='{.data.publicApiKey}' | base64 -d)

echo "Ops Manager URL: $OM_URL"
echo "Testing with --digest auth..."
curl --digest -u "$OM_USER:$OM_KEY" "$OM_URL/api/public/v1.0" -s | head -20
echo ""

# 4. Check if Ops Manager project exists
echo "4. Checking if Ops Manager project exists:"
OM_PROJECT=$(kubectl get configmap om-${TENANT_ID}-project -n $NAMESPACE -o jsonpath='{.data.projectName}')
echo "Project name: $OM_PROJECT"

curl --digest -u "$OM_USER:$OM_KEY" "$OM_URL/api/public/v1.0/groups/byName/$OM_PROJECT" -s | jq '.'
echo ""

# 5. Check operator can reach Ops Manager from inside cluster
echo "5. Testing Ops Manager connectivity FROM INSIDE Kubernetes:"
kubectl run test-om-conn --image=curlimages/curl --rm -i --restart=Never -- sh -c "
  echo 'Testing from pod...'
  curl --max-time 10 $OM_URL -s -o /dev/null -w 'HTTP Status: %{http_code}\n'
" 2>&1
echo ""

echo "=========================================="
echo "Summary"
echo "=========================================="
echo ""
echo "If connectivity test fails:"
echo "  - Firewall may be blocking K8s → Ops Manager"
echo "  - Ops Manager may be down"
echo "  - API keys may be invalid (need --digest flag)"
echo ""
echo "If project doesn't exist:"
echo "  - Operator should auto-create it"
echo "  - Or manually create project '$OM_PROJECT' in Ops Manager"
echo ""
echo "Next: Check why operator isn't processing the CRs:"
echo "  bash check_operator_issue.sh"
