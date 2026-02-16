# Community Deployment Troubleshooting Guide

## Issue: Pods Stuck in Pending State

When community MongoDB pods are stuck in "Pending", follow these steps:

---

## Step 1: Check Pod Status and Events

```bash
# Get pod status
kubectl get pods -n mdb-t5

# Describe the pending pod
kubectl describe pod test-5-deployment-0 -n mdb-t5

# Look at Events section at the bottom
# Common issues:
# - "0/X nodes are available: X Insufficient cpu"
# - "0/X nodes are available: X Insufficient memory"
# - "persistentvolumeclaim not found"
# - "no nodes available to schedule pods"
```

---

## Step 2: Check Node Resources

```bash
# Check node status
kubectl get nodes

# Check node resources
kubectl top nodes

# Check if nodes are ready
kubectl describe nodes | grep -A 5 "Conditions:"

# Expected output: All nodes should be "Ready"
```

**Problem Indicators:**
- Nodes showing "NotReady"
- CPU/Memory usage at 100%
- No nodes available

**Solutions:**
- Add more worker nodes
- Free up resources by deleting unused pods
- Increase node capacity

---

## Step 3: Check PVC Status

```bash
# List PVCs in namespace
kubectl get pvc -n mdb-t5

# Expected: STATUS should be "Bound"
# If "Pending", there's a storage issue

# Describe PVC
kubectl describe pvc -n mdb-t5

# Check for events like:
# - "no persistent volumes available"
# - "storageclass not found"
```

**Problem: PVC Pending**

Solution 1: Check if StorageClass exists
```bash
kubectl get storageclass

# Ensure default storageclass exists
kubectl get sc -o jsonpath='{.items[?(@.metadata.annotations.storageclass\.kubernetes\.io/is-default-class=="true")].metadata.name}'
```

Solution 2: Set a default StorageClass
```bash
# Example: Set standard as default
kubectl patch storageclass standard -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

Solution 3: Check PV availability
```bash
# List available PVs
kubectl get pv

# Should have PVs in "Available" state
```

---

## Step 4: Check MongoDB Community Operator

```bash
# Check if operator is running
kubectl get pods -n mongodb-operator-system

# Expected: mongodb-community-operator pod in "Running" state

# Check operator logs
kubectl logs -n mongodb-operator-system deployment/mongodb-community-operator

# Look for errors related to:
# - Webhook configuration
# - RBAC permissions
# - CR reconciliation
```

**Problem: Operator not running**

Reinstall operator:
```bash
kubectl apply -f https://raw.githubusercontent.com/mongodb/mongodb-kubernetes-operator/master/config/crd/bases/mongodbcommunity.mongodb.com_mongodbcommunity.yaml
kubectl apply -f https://raw.githubusercontent.com/mongodb/mongodb-kubernetes-operator/master/config/rbac/role.yaml
kubectl apply -f https://raw.githubusercontent.com/mongodb/mongodb-kubernetes-operator/master/config/manager/manager.yaml
```

---

## Step 5: Check MongoDBCommunity CR

```bash
# Get CR status
kubectl get mongodbcommunity -n mdb-t5

# Describe CR
kubectl describe mongodbcommunity test-5-deployment -n mdb-t5

# Check status conditions at bottom
```

**Check for:**
- CR created successfully?
- Status shows any errors?
- Operator recognized the CR?

---

## Step 6: Check Resource Requests

```bash
# Check StatefulSet resource requests
kubectl get statefulset -n mdb-t5 -o yaml | grep -A 5 "resources:"

# Default MongoDB requests:
#   cpu: 500m
#   memory: 1Gi
```

**Problem: Insufficient resources**

Option 1: Free up cluster resources
```bash
# Delete unused deployments
kubectl delete deployment <unused-deployment> -n <namespace>

# Delete completed jobs
kubectl delete jobs --field-selector status.successful=1 -A
```

Option 2: Reduce MongoDB resource requests (not recommended for production)

Edit the MongoDBCommunity CR:
```yaml
spec:
  statefulSet:
    spec:
      template:
        spec:
          containers:
          - name: mongod
            resources:
              requests:
                cpu: 250m      # Reduced from 500m
                memory: 512Mi  # Reduced from 1Gi
```

---

## Step 7: Check Image Pull

```bash
# Check if image can be pulled
kubectl describe pod test-5-deployment-0 -n mdb-t5 | grep -A 10 "Events:"

# Look for:
# - "ErrImagePull"
# - "ImagePullBackOff"
# - "Failed to pull image"
```

**Problem: Image pull errors**

Common causes:
- No internet access from worker nodes
- Docker Hub rate limiting
- Private registry authentication issues

Solutions:
```bash
# Check if nodes can access internet
kubectl run test-curl --image=curlimages/curl:7.85.0 --rm -it -- curl -I https://docker.io

# Check imagePullSecrets if using private registry
kubectl get secrets -n mdb-t5
```

---

## Step 8: Check Network Policies

```bash
# List network policies
kubectl get networkpolicies -n mdb-t5

# Check if policies are blocking pod communication
kubectl describe networkpolicy -n mdb-t5
```

**Problem: Network policies blocking traffic**

Temporarily disable to test:
```bash
kubectl delete networkpolicies --all -n mdb-t5
```

---

## Step 9: Check Admin Secret

MongoDB Community operator requires an admin password secret:

```bash
# Check if secret exists
kubectl get secret mongodb-admin-secret -n mdb-t5

# If not found, create it:
kubectl create secret generic mongodb-admin-secret \
  -n mdb-t5 \
  --from-literal="password=$(openssl rand -base64 20)"
```

---

## Step 10: Check Complete Diagnostic Info

```bash
# Get everything in namespace
kubectl get all -n mdb-t5

# Get events (last 30 minutes)
kubectl get events -n mdb-t5 --sort-by='.lastTimestamp' | tail -20

# Get MongoDB CR YAML
kubectl get mongodbcommunity test-5-deployment -n mdb-t5 -o yaml

# Check operator webhook
kubectl get validatingwebhookconfigurations | grep mongodb
kubectl get mutatingwebhookconfigurations | grep mongodb
```

---

## Common Root Causes & Quick Fixes

### 1. Missing Admin Secret
```bash
kubectl create secret generic mongodb-admin-secret \
  -n mdb-t5 \
  --from-literal="password=$(openssl rand -base64 20)"
```

### 2. No Default StorageClass
```bash
kubectl patch storageclass standard -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

### 3. Insufficient Resources
```bash
# Check available resources
kubectl describe nodes | grep -A 5 "Allocated resources:"

# If low, scale down other workloads or add nodes
```

### 4. Operator Not Running
```bash
# Restart operator
kubectl rollout restart deployment mongodb-community-operator -n mongodb-operator-system
```

### 5. PVC Stuck in Pending
```bash
# Delete and recreate
kubectl delete pvc data-test-5-deployment-0 -n mdb-t5
kubectl delete pod test-5-deployment-0 -n mdb-t5
# StatefulSet will recreate both
```

---

## Debug Command Checklist

Run these commands in order:

```bash
# 1. Pod status
kubectl get pods -n mdb-t5

# 2. Pod events (MOST IMPORTANT)
kubectl describe pod test-5-deployment-0 -n mdb-t5 | tail -30

# 3. Node status
kubectl get nodes
kubectl top nodes

# 4. PVC status
kubectl get pvc -n mdb-t5

# 5. StorageClass
kubectl get sc

# 6. Operator status
kubectl get pods -n mongodb-operator-system

# 7. CR status
kubectl get mongodbcommunity -n mdb-t5

# 8. Namespace events
kubectl get events -n mdb-t5 --sort-by='.lastTimestamp' | tail -20

# 9. Admin secret
kubectl get secret mongodb-admin-secret -n mdb-t5

# 10. Full diagnostic
kubectl describe mongodbcommunity test-5-deployment -n mdb-t5
```

---

## What We Haven't Changed

The community deployment code has **NOT** been changed recently. The pending pods issue is likely due to:

1. **Cluster resources exhausted** - Most common
2. **Storage provisioner issues** - Very common
3. **Operator issues** - Rare but possible
4. **Admin secret missing** - Common on new namespaces

## Next Steps

1. Run the debug command checklist above
2. Look at the "Events:" section in `kubectl describe pod`
3. Share the output here for specific diagnosis
4. Check if other namespaces can create pods successfully

---

## Testing with Minimal Resources

If cluster is low on resources, test with a minimal deployment:

```bash
# Edit MongoDB CR to reduce resources
kubectl edit mongodbcommunity test-5-deployment -n mdb-t5

# Add under spec.statefulSet.spec.template.spec:
containers:
- name: mongod
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: 500m
      memory: 512Mi
```

Then wait and check:
```bash
kubectl get pods -n mdb-t5 -w
```

If it starts with reduced resources, you know it's a resource constraint issue.
