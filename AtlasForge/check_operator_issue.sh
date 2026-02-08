#!/bin/bash

NAMESPACE="mdb-test1"

echo "=========================================="
echo "MongoDB Enterprise Operator Diagnosis"
echo "=========================================="
echo ""

# 1. Check if operator is running
echo "1. MongoDB Enterprise Operator Status:"
OPERATOR_POD=$(kubectl get pods --all-namespaces -l name=mongodb-enterprise-operator -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
OPERATOR_NS=$(kubectl get pods --all-namespaces -l name=mongodb-enterprise-operator -o jsonpath='{.items[0].metadata.namespace}' 2>/dev/null)

if [ -z "$OPERATOR_POD" ]; then
    echo "❌ Operator not found!"
    echo "Searching for operator..."
    kubectl get pods --all-namespaces | grep mongo
else
    echo "✅ Operator found: $OPERATOR_POD in namespace $OPERATOR_NS"
    kubectl get pod $OPERATOR_POD -n $OPERATOR_NS
fi
echo ""

# 2. Check MongoDB CRs in namespace
echo "2. MongoDB CRs in namespace $NAMESPACE:"
kubectl get mongodb -n $NAMESPACE
echo ""

# 3. Check StatefulSets (should be created by operator)
echo "3. StatefulSets in namespace $NAMESPACE:"
kubectl get statefulset -n $NAMESPACE
echo ""

# 4. Check Pods
echo "4. Pods in namespace $NAMESPACE:"
kubectl get pods -n $NAMESPACE
echo ""

# 5. Check events in namespace
echo "5. Recent events in namespace $NAMESPACE:"
kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | tail -20
echo ""

# 6. Describe the MongoDB CRs to see status
echo "6. Status of test-customers MongoDB CR:"
kubectl get mongodb test-customers -n $NAMESPACE -o jsonpath='{.status}' | jq '.'
echo ""

echo "7. Status of rs-analytics MongoDB CR:"
kubectl get mongodb rs-analytics -n $NAMESPACE -o jsonpath='{.status}' | jq '.'
echo ""

# 7. Check operator logs for errors
if [ -n "$OPERATOR_POD" ]; then
    echo "8. Operator logs (last 50 lines, filtering for $NAMESPACE):"
    kubectl logs $OPERATOR_POD -n $OPERATOR_NS --tail=50 | grep -i "$NAMESPACE\|error\|fail" || echo "(No relevant logs)"
    echo ""
    
    echo "9. Operator logs for rs-analytics:"
    kubectl logs $OPERATOR_POD -n $OPERATOR_NS --tail=100 | grep -i "rs-analytics" || echo "(No logs for rs-analytics)"
fi
echo ""

echo "=========================================="
echo "Diagnosis Summary"
echo "=========================================="
echo ""
echo "Key Questions:"
echo "1. Is operator running? $([ -n "$OPERATOR_POD" ] && echo 'YES' || echo 'NO')"
echo "2. Are MongoDB CRs created? $(kubectl get mongodb -n $NAMESPACE --no-headers 2>/dev/null | wc -l) found"
echo "3. Are StatefulSets created? $(kubectl get statefulset -n $NAMESPACE --no-headers 2>/dev/null | wc -l) found"
echo "4. Are Pods running? $(kubectl get pods -n $NAMESPACE --no-headers 2>/dev/null | wc -l) found"
echo ""

STS_COUNT=$(kubectl get statefulset -n $NAMESPACE --no-headers 2>/dev/null | wc -l | tr -d ' ')
if [ "$STS_COUNT" = "0" ]; then
    echo "❌ PROBLEM: MongoDB CRs exist but NO StatefulSets created!"
    echo ""
    echo "This means the operator is NOT reconciling the CRs."
    echo ""
    echo "Possible causes:"
    echo "1. Operator is not running or crashed"
    echo "2. Operator is not watching this namespace"
    echo "3. CRs have validation errors that block the operator"
    echo "4. Ops Manager connection is failing"
    echo "5. ConfigMap or Secret is missing/invalid"
    echo ""
    echo "Check:"
    echo "  kubectl describe mongodb test-customers -n $NAMESPACE"
    echo "  kubectl describe mongodb rs-analytics -n $NAMESPACE"
    echo "  kubectl logs -n $OPERATOR_NS $OPERATOR_POD --tail=200"
fi
