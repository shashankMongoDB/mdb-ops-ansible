# Community Upgrade Not Working - Diagnosis Guide

## Problem Statement

**Symptom:**
- ✅ Enterprise upgrades work fine (Ops Manager reconciles)
- ❌ Community upgrades not working at all
- mongosh shows old version even after upgrade attempt
- UI shows no progress or fails with error

---

## How It Should Work

### **Enterprise Upgrade Flow:**
```
1. User clicks [Upgrade Version]
   ↓
2. Backend patches MongoDB CR:
   spec.version: "8.0.19-ent"
   ↓
3. Ops Manager reconciles
   ↓
4. Automation updates deployment
   ↓
5. Rolling upgrade of replicas
   ↓
6. ✅ Complete!
```

### **Community Upgrade Flow:**
```
1. User clicks [Upgrade Version]
   ↓
2. Backend patches MongoDBCommunity CR:
   spec.version: "7.0.15"
   ↓
3. Community Operator reconciles
   ↓
4. Operator updates StatefulSet image
   ↓
5. K8s performs rolling update
   ↓
6. Pods restart with new version
   ↓
7. ✅ Complete!
```

**Key Difference:**
- Enterprise: Ops Manager handles upgrade logic (FCV, rolling restart, etc.)
- Community: Community Operator + K8s handle it (simpler, but requires operator)

---

## Current Implementation

### **Backend Code:**

**File:** `app/services/scaling_service.py`

```python
def upgrade_version(tenant_id: str, deployment_id: str, mongo_version: str):
    # ... version checks ...
    
    if plan == "community":
        # Route to community service
        deployments_community_service.upgrade_version_community(
            namespace, deployment_id, mongo_version
        )
    else:
        # Enterprise: patch CR
        patch = {"spec": {"version": mongo_version}}
        k8s.patch_mongodb_enterprise_cr(namespace, deployment_id, patch)
    
    # Update DB
    repo.update_deployment(tenant_id, deployment_id, {
        "lastRequestedSpec.mongoVersion": mongo_version
    })
```

**File:** `app/services/deployments_community_service.py`

```python
def upgrade_version_community(namespace: str, deployment_id: str, new_version: str):
    """Upgrade MongoDB version for a community deployment by patching the CR."""
    k8s = get_k8s_client()
    
    logger.info(f"Upgrading community deployment: {namespace}/{deployment_id} to version {new_version}")
    
    patch = {
        "spec": {
            "version": new_version
        }
    }
    
    k8s.patch_mongodb_community_cr(namespace, deployment_id, patch)
    logger.info(f"Patched community MongoDB CR with version={new_version}")
```

**File:** `app/services/k8s_client.py`

```python
def patch_mongodb_community_cr(self, namespace: str, name: str, patch: Dict[str, Any]):
    """Patch a community MongoDB CR"""
    self.custom_objects.patch_namespaced_custom_object(
        group="mongodbcommunity.mongodb.com",
        version="v1",
        namespace=namespace,
        plural="mongodbcommunity",
        name=name,
        body=patch
    )
```

**The code looks correct!** So why isn't it working?

---

## Possible Root Causes

### **1. Backend RBAC Permissions** ⚠️

**Problem:** Backend service account doesn't have permission to patch MongoDBCommunity CRs.

**Check:**
```bash
# Check if backend can patch community CRs
kubectl auth can-i patch mongodbcommunity \
  --as=system:serviceaccount:mdbaas-system:mdbaas-backend \
  -n mdb-t-comm

# Expected: yes
# If "no" → RBAC issue!
```

**Solution:**
Create ClusterRole with MongoDBCommunity permissions:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: mdbaas-backend-role
rules:
# Enterprise MongoDB
- apiGroups: ["mongodb.com"]
  resources: ["mongodb", "mongodbusers"]
  verbs: ["get", "list", "patch", "update", "create", "delete"]

# Community MongoDB
- apiGroups: ["mongodbcommunity.mongodb.com"]
  resources: ["mongodbcommunity"]
  verbs: ["get", "list", "patch", "update", "create", "delete"]

# Other resources...
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: mdbaas-backend-binding
subjects:
- kind: ServiceAccount
  name: mdbaas-backend
  namespace: mdbaas-system
roleRef:
  kind: ClusterRole
  name: mdbaas-backend-role
  apiGroup: rbac.authorization.k8s.io
```

---

### **2. Community Operator Not Running** ⚠️

**Problem:** MongoDB Community Operator is not installed or not running.

**Check:**
```bash
# Check if operator exists
kubectl get pods -n mongodb-operator | grep community

# Expected: mongodb-community-operator-xxx Running
# If not found → Operator not installed!
```

**Check operator logs:**
```bash
kubectl logs -n mongodb-operator deployment/mongodb-community-operator --tail=50
```

**Solution:**
Install Community Operator:

```bash
# Install MongoDB Community Operator
kubectl apply -f https://raw.githubusercontent.com/mongodb/mongodb-kubernetes-operator/master/config/crd/bases/mongodbcommunity.mongodb.com_mongodbcommunity.yaml

kubectl apply -f https://raw.githubusercontent.com/mongodb/mongodb-kubernetes-operator/master/config/rbac/role.yaml
kubectl apply -f https://raw.githubusercontent.com/mongodb/mongodb-kubernetes-operator/master/config/rbac/role_binding.yaml
kubectl apply -f https://raw.githubusercontent.com/mongodb/mongodb-kubernetes-operator/master/config/manager/manager.yaml
```

---

### **3. CR Not Being Patched (Silent Failure)** ⚠️

**Problem:** API returns 200 OK but CR is not actually updated.

**Check:**
```bash
# Get current version
kubectl get mongodbcommunity monitoring-comm -n mdb-t-comm -o jsonpath='{.spec.version}'

# Call upgrade API
curl -X PATCH http://localhost:8001/tenants/t-comm/deployments/monitoring-comm/version \
  -H "Content-Type: application/json" \
  -d '{"mongoVersion": "7.0.15"}'

# Check version again
kubectl get mongodbcommunity monitoring-comm -n mdb-t-comm -o jsonpath='{.spec.version}'

# Did it change? If not → patch is failing silently
```

**Check backend logs:**
```bash
kubectl logs -n mdbaas-system deployment/mdbaas-backend --tail=50 | grep -i upgrade

# Look for errors or exceptions
```

---

### **4. Operator Not Reconciling CR Changes** ⚠️

**Problem:** CR is updated but operator doesn't reconcile the change.

**Check:**
```bash
# Check operator logs for reconciliation events
kubectl logs -n mongodb-operator deployment/mongodb-community-operator --tail=100 | grep monitoring-comm

# Look for:
# - Reconcile events
# - Version update events
# - Errors or warnings
```

**Check CR status:**
```bash
kubectl get mongodbcommunity monitoring-comm -n mdb-t-comm -o yaml

# Look at:
# - spec.version (should be new version)
# - status.phase
# - status.mongoUri
# - status.message
```

---

### **5. StatefulSet Not Being Updated** ⚠️

**Problem:** Operator reconciles but doesn't update StatefulSet.

**Check:**
```bash
# Check StatefulSet image
kubectl get statefulset monitoring-comm -n mdb-t-comm -o jsonpath='{.spec.template.spec.containers[0].image}'

# Expected: mongo:7.0.15 or similar
# If still old version → StatefulSet not updated
```

**Check StatefulSet events:**
```bash
kubectl describe statefulset monitoring-comm -n mdb-t-comm

# Look for recent events
```

---

### **6. Wrong Version Format** ⚠️

**Problem:** Community operator expects different version format than Enterprise.

**Community expects:**
```yaml
spec:
  version: "7.0.14"  # Simple version
```

**Enterprise expects:**
```yaml
spec:
  version: "7.0.14-ent"  # With edition suffix
```

**Check:**
```bash
# What version format is in the CR?
kubectl get mongodbcommunity monitoring-comm -n mdb-t-comm -o jsonpath='{.spec.version}'

# Are we passing "7.0.14" or "7.0.14-ent"?
```

**Fix in code if needed:**
```python
def upgrade_version_community(namespace: str, deployment_id: str, new_version: str):
    # Strip -ent suffix for community
    clean_version = new_version.replace("-ent", "").replace("-community", "")
    
    patch = {
        "spec": {
            "version": clean_version  # Use cleaned version
        }
    }
    
    k8s.patch_mongodb_community_cr(namespace, deployment_id, patch)
```

---

### **7. Pods Not Restarting** ⚠️

**Problem:** StatefulSet updated but pods not restarting.

**Check:**
```bash
# Check if pods are being recreated
kubectl get pods -n mdb-t-comm -l app=monitoring-comm-svc -w

# Watch for pod deletions and creations
```

**Check pod events:**
```bash
kubectl get events -n mdb-t-comm --sort-by='.lastTimestamp' | grep monitoring-comm
```

**Manual restart if needed:**
```bash
# Delete pods one by one (rolling restart)
kubectl delete pod monitoring-comm-0 -n mdb-t-comm
# Wait for it to come back
kubectl delete pod monitoring-comm-1 -n mdb-t-comm
# etc...
```

---

## Diagnostic Script

Run the test script I created:

```bash
chmod +x scripts/test-community-upgrade.sh

./scripts/test-community-upgrade.sh t-comm monitoring-comm 7.0.15
```

This will:
1. ✅ Check current CR version
2. ✅ Check current pod versions
3. ✅ Call upgrade API
4. ✅ Verify CR was patched
5. ✅ Check StatefulSet image
6. ✅ Monitor pod updates

---

## Manual Testing

### **Step 1: Verify Current State**

```bash
# Check CR
kubectl get mongodbcommunity monitoring-comm -n mdb-t-comm -o yaml | grep version

# Check pods
kubectl get pods -n mdb-t-comm -l app=monitoring-comm-svc

# Check MongoDB version in pod
kubectl exec monitoring-comm-0 -n mdb-t-comm -- mongosh --eval "db.version()"
```

### **Step 2: Call Upgrade API**

```bash
curl -X PATCH http://localhost:8001/tenants/t-comm/deployments/monitoring-comm/version \
  -H "Content-Type: application/json" \
  -d '{"mongoVersion": "7.0.15"}'
```

### **Step 3: Check Backend Logs**

```bash
kubectl logs -n mdbaas-system deployment/mdbaas-backend --tail=50 | grep -i upgrade

# Look for:
# - "Upgrading community deployment"
# - "Patched community MongoDB CR"
# - Any errors or exceptions
```

### **Step 4: Verify CR Patch**

```bash
# Wait 2 seconds, then check
sleep 2
kubectl get mongodbcommunity monitoring-comm -n mdb-t-comm -o jsonpath='{.spec.version}'

# Should show: 7.0.15 (or new version)
```

### **Step 5: Check Operator Logs**

```bash
kubectl logs -n mongodb-operator deployment/mongodb-community-operator --tail=50 | grep monitoring-comm
```

### **Step 6: Monitor StatefulSet**

```bash
# Wait for operator to reconcile (5-10 seconds)
sleep 10

kubectl get statefulset monitoring-comm -n mdb-t-comm -o jsonpath='{.spec.template.spec.containers[0].image}'

# Should show new MongoDB image
```

### **Step 7: Watch Pods**

```bash
kubectl get pods -n mdb-t-comm -l app=monitoring-comm-svc -w

# Watch for pods being deleted and recreated
```

---

## Most Likely Issue: RBAC Permissions

Based on the fact that Enterprise works but Community doesn't, the most likely issue is **RBAC permissions**.

**Why Enterprise works:**
- Backend already has permission to patch `mongodb.com/v1/mongodb` CRs
- These permissions were set up for Enterprise

**Why Community fails:**
- Backend doesn't have permission to patch `mongodbcommunity.mongodb.com/v1/mongodbcommunity` CRs
- Different API group = different permission needed
- Patch fails silently, API returns 200 but CR not updated

### **Quick Fix:**

```bash
kubectl create clusterrole mdbaas-community-role \
  --verb=get,list,patch,update,create,delete \
  --resource=mongodbcommunity.mongodbcommunity.mongodb.com

kubectl create clusterrolebinding mdbaas-community-binding \
  --clusterrole=mdbaas-community-role \
  --serviceaccount=mdbaas-system:mdbaas-backend
```

---

## Complete RBAC Configuration

Create this file and apply it:

```yaml
# rbac-community.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: mdbaas-backend-community
rules:
- apiGroups: ["mongodbcommunity.mongodb.com"]
  resources: ["mongodbcommunity"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["pods", "pods/exec", "services", "secrets"]
  verbs: ["get", "list", "create", "update", "patch", "delete"]
- apiGroups: ["apps"]
  resources: ["statefulsets"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: mdbaas-backend-community-binding
subjects:
- kind: ServiceAccount
  name: mdbaas-backend
  namespace: mdbaas-system
roleRef:
  kind: ClusterRole
  name: mdbaas-backend-community
  apiGroup: rbac.authorization.k8s.io
```

```bash
kubectl apply -f rbac-community.yaml
```

---

## Testing After Fix

```bash
# 1. Apply RBAC fix
kubectl apply -f rbac-community.yaml

# 2. Restart backend (to refresh permissions)
kubectl rollout restart deployment/mdbaas-backend -n mdbaas-system

# 3. Wait for backend to be ready
kubectl wait --for=condition=available deployment/mdbaas-backend -n mdbaas-system

# 4. Run test script
./scripts/test-community-upgrade.sh t-comm monitoring-comm 7.0.15

# 5. Should work now!
```

---

## Summary

### **Most Likely Issue:**
❌ Backend doesn't have RBAC permission to patch MongoDBCommunity CRs

### **Quick Check:**
```bash
kubectl auth can-i patch mongodbcommunity \
  --as=system:serviceaccount:mdbaas-system:mdbaas-backend \
  -n mdb-t-comm
```

### **Quick Fix:**
```bash
kubectl create clusterrole mdbaas-community-role \
  --verb=get,list,patch,update,create,delete \
  --resource=mongodbcommunity.mongodbcommunity.mongodb.com

kubectl create clusterrolebinding mdbaas-community-binding \
  --clusterrole=mdbaas-community-role \
  --serviceaccount=mdbaas-system:mdbaas-backend

kubectl rollout restart deployment/mdbaas-backend -n mdbaas-system
```

### **Verify:**
```bash
./scripts/test-community-upgrade.sh t-comm monitoring-comm 7.0.15
```

---

**Run the diagnostic script and share the output - it will tell us exactly what's wrong!** 🔍
