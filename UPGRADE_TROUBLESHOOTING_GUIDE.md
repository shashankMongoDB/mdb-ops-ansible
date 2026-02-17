# Upgrade Status Issues - Troubleshooting Guide

## Issues Reported

1. ❌ Console error: "message channel closed before a response was received"
2. ❌ mongosh shows old version (upgrade not happening)
3. ❌ UI shows "Upgrade monitoring failed: Network Error"
4. ❓ CPU concerns - will low CPU cause problems?

---

## Issue 1: Console Error (Browser Extension)

### **Error:**
```
Uncaught (in promise) Error: A listener indicated an asynchronous response 
by returning true, but the message channel closed before a response was received
```

### **Cause:**
This is a **browser extension error**, not our application. Common culprits:
- Chrome extensions (ad blockers, privacy tools)
- React DevTools
- Redux DevTools

### **Solution:**
✅ **IGNORE THIS ERROR** - It won't affect functionality

**Optional: To remove the noise:**
```bash
# Test in incognito mode (disables most extensions)
# Or disable extensions one by one to find the culprit
```

---

## Issue 2: Upgrade Not Happening (mongosh shows old version)

### **Diagnosis Steps:**

#### **Step 1: Check if API call succeeded**

Open browser DevTools (F12) → Network tab:
```
Look for:
PATCH /tenants/{tid}/deployments/{did}/version

Status should be: 200 OK
```

#### **Step 2: Check backend logs**

```bash
# Check if upgrade endpoint was called
kubectl logs -n mdbaas-system deployment/mdbaas-backend --tail=50 | grep -i upgrade

# Or if running locally
tail -f /path/to/backend/logs
```

**Look for:**
```
INFO - Upgrading deployment rs-orders from 8.0.18-ent to 8.0.19-ent
```

#### **Step 3: Check if CR was patched**

```bash
# Get the MongoDB CR
kubectl get mongodb <deployment-id> -n <namespace> -o yaml

# Check the version field
kubectl get mongodb <deployment-id> -n <namespace> -o jsonpath='{.spec.version}'
```

**Expected:**
```yaml
spec:
  version: "8.0.19-ent"  # Should be NEW version
```

**If version is still old:**
- Backend didn't patch CR
- Check backend logs for errors
- Check if backend has permission to patch CRs

#### **Step 4: Check StatefulSet**

```bash
# Check if StatefulSet is updating
kubectl get statefulset <deployment-id> -n <namespace> -o yaml | grep image

# Expected: Should show new MongoDB image version
```

#### **Step 5: Check pods**

```bash
# Check pod status
kubectl get pods -n <namespace> -l app=<deployment-id>-svc

# Check if pods are being recreated
kubectl describe pod <pod-name> -n <namespace>

# Check pod events
kubectl get events -n <namespace> --sort-by='.lastTimestamp' | grep <deployment-id>
```

---

### **Common Issues & Fixes:**

#### **A) Backend RBAC Permissions**

**Problem:** Backend can't patch MongoDB CRs

**Check:**
```bash
# Check if ServiceAccount has permissions
kubectl get role -n <namespace>
kubectl get rolebinding -n <namespace>

# Check backend ServiceAccount
kubectl get sa mdbaas-backend -n mdbaas-system
```

**Fix:**
```yaml
# Create Role for backend
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: mdbaas-backend-role
rules:
- apiGroups: ["mongodb.com"]
  resources: ["mongodb"]
  verbs: ["get", "list", "patch", "update"]
- apiGroups: ["mongodbcommunity.mongodb.com"]
  resources: ["mongodbcommunity"]
  verbs: ["get", "list", "patch", "update"]

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

#### **B) CR Validation Webhook Blocking**

**Problem:** Operator webhook rejecting version change

**Check:**
```bash
# Check webhook logs
kubectl logs -n mongodb-operator deployment/mongodb-enterprise-operator | grep -i webhook
```

**Fix:**
- Ensure version format is correct (e.g., "8.0.19-ent")
- Check if version is supported by operator
- Verify MongoDB images are available

#### **C) Operator Not Running**

**Problem:** Operator not processing CR changes

**Check:**
```bash
# Check operator status
kubectl get pods -n mongodb-operator
kubectl logs -n mongodb-operator deployment/mongodb-enterprise-operator --tail=100
```

**Fix:**
```bash
# Restart operator
kubectl rollout restart deployment/mongodb-enterprise-operator -n mongodb-operator
```

---

## Issue 3: Network Error in UI

### **Error:**
```
Upgrade monitoring failed: Network Error
```

### **Cause:**
The polling hook is trying to call `getConnectionInfo` but failing.

### **Diagnosis:**

#### **Step 1: Check if backend is reachable**

```bash
# From browser console (F12)
fetch('http://localhost:8001/health')
  .then(r => r.json())
  .then(console.log)
  .catch(console.error)
```

**Expected:** `{status: "healthy"}`

#### **Step 2: Check CORS headers**

```bash
# Check if CORS is enabled
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     http://localhost:8001/tenants/test-tenant/deployments/rs-test/connection-info \
     -v
```

**Look for:**
```
< Access-Control-Allow-Origin: *
< Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
```

#### **Step 3: Test connection info endpoint**

```bash
# Test the endpoint directly
curl http://localhost:8001/tenants/<tenant-id>/deployments/<deployment-id>/connection-info
```

**Expected:**
```json
{
  "connectionString": "mongodb://...",
  "readyReplicas": 3,
  "totalReplicas": 3,
  "replicas": [...]
}
```

### **Fixes:**

#### **A) Backend Not Running**

```bash
# Check if backend is running
ps aux | grep uvicorn

# Or in K8s
kubectl get pods -n mdbaas-system -l app=mdbaas-backend
```

**Restart backend:**
```bash
# Local
pkill -f uvicorn
cd AtlasForge
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload &

# K8s
kubectl rollout restart deployment/mdbaas-backend -n mdbaas-system
```

#### **B) CORS Not Enabled**

Check `main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Should be "*" for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### **C) Frontend Using Wrong API URL**

Check `.env` or `config.ts`:
```typescript
// src/lib/config.ts
export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001',
};
```

**Set environment variable:**
```bash
# .env file
VITE_API_BASE_URL=http://localhost:8001
```

---

## Issue 4: CPU Concerns

### **Question:** Will low CPU cause upgrade problems?

### **Answer:** YES, low CPU can cause issues:

#### **Symptoms of Low CPU:**
- ❌ Pods take longer to start
- ❌ Upgrade appears "stuck"
- ❌ Pods in "Pending" or "ContainerCreating" state
- ❌ Slow API responses
- ❌ Timeouts

#### **Check CPU Usage:**

```bash
# Check node CPU
kubectl top nodes

# Check pod CPU
kubectl top pods -n <namespace>

# Check resource requests/limits
kubectl describe pod <pod-name> -n <namespace> | grep -A 5 "Requests:"
```

#### **Recommended CPU:**

| Component | Min CPU | Recommended |
|-----------|---------|-------------|
| Worker Node | 2 cores | 4+ cores |
| MongoDB Pod | 500m | 1000m-2000m |
| Backend Pod | 500m | 1000m |
| Frontend Pod | 200m | 500m |

#### **Solutions:**

**A) Add More Worker Nodes:**
```bash
# AWS EKS
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --scaling-config desiredSize=5

# Or add new node group with larger instances
```

**B) Increase Pod CPU Limits:**
```yaml
resources:
  requests:
    cpu: "1000m"
    memory: "2Gi"
  limits:
    cpu: "2000m"
    memory: "4Gi"
```

**C) Use Node Affinity:**
```yaml
# Pin MongoDB pods to larger nodes
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: node.kubernetes.io/instance-type
          operator: In
          values:
          - t3.xlarge
          - t3.2xlarge
```

---

## Debugging Workflow

### **Complete Debugging Process:**

```bash
# 1. Check backend is running
curl http://localhost:8001/health

# 2. Check if upgrade API works
curl -X PATCH http://localhost:8001/tenants/<tid>/deployments/<did>/version \
  -H "Content-Type: application/json" \
  -d '{"mongoVersion": "8.0.19-ent"}'

# 3. Check if CR was patched
kubectl get mongodb <deployment-id> -n <namespace> -o jsonpath='{.spec.version}'

# 4. Check operator logs
kubectl logs -n mongodb-operator deployment/mongodb-enterprise-operator --tail=50

# 5. Check if pods are updating
kubectl get pods -n <namespace> -w

# 6. Check pod events
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# 7. Check StatefulSet
kubectl get statefulset <deployment-id> -n <namespace> -o yaml | grep image

# 8. Check node resources
kubectl top nodes
kubectl describe node <node-name> | grep -A 5 "Allocated resources:"
```

---

## Quick Fixes

### **Fix 1: Restart Everything**

```bash
# Restart backend
kubectl rollout restart deployment/mdbaas-backend -n mdbaas-system

# Restart operator
kubectl rollout restart deployment/mongodb-enterprise-operator -n mongodb-operator

# Restart frontend (if needed)
kubectl rollout restart deployment/mdbaas-frontend -n mdbaas-system
```

### **Fix 2: Manual CR Patch**

If backend can't patch, do it manually:

```bash
kubectl patch mongodb <deployment-id> -n <namespace> --type=merge \
  -p '{"spec":{"version":"8.0.19-ent"}}'
```

### **Fix 3: Force Pod Recreation**

```bash
# Delete pods one by one (rolling restart)
kubectl delete pod <deployment-id>-0 -n <namespace>
# Wait for it to come back
kubectl delete pod <deployment-id>-1 -n <namespace>
# etc...
```

### **Fix 4: Check MongoDB Version Inside Pod**

```bash
# Connect to MongoDB
kubectl exec -it <pod-name> -n <namespace> -- mongosh

# Check version
db.version()
```

---

## Temporary Workaround

If polling is failing but upgrade is working, you can **disable the progress modal** temporarily:

Edit `UpgradeVersionModal.tsx`:

```typescript
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  
  setLoading(true);
  try {
    await deploymentsApi.upgradeVersion(tenantId, deploymentId, mongoVersion);
    
    // TEMPORARY: Don't show progress modal
    // setUpgradeState('upgrading');
    // startPolling();
    
    showSuccess('Version upgrade initiated', `Upgrading to ${mongoVersion}. Check deployment page in a few minutes.`);
    onClose();
    onSuccess();
  } catch (error: any) {
    showError('Failed to upgrade version', error.detail);
  } finally {
    setLoading(false);
  }
};
```

---

## Summary

### **Most Likely Issues:**

1. **Network Error** → Backend not reachable or CORS issue
2. **No Upgrade** → Backend can't patch CR (RBAC) or operator not running
3. **Low CPU** → Pods slow to start, upgrade appears stuck

### **Quick Checklist:**

```
☐ Backend running? (curl http://localhost:8001/health)
☐ CORS enabled? (Check Network tab in browser)
☐ Operator running? (kubectl get pods -n mongodb-operator)
☐ RBAC correct? (Backend can patch CRs?)
☐ CPU sufficient? (kubectl top nodes)
☐ CR patched? (kubectl get mongodb <id> -n <ns> -o jsonpath='{.spec.version}')
☐ Pods updating? (kubectl get pods -n <ns> -w)
```

### **Next Steps:**

1. Run the debugging workflow above
2. Share the outputs
3. I'll help identify the exact issue

Would you like me to create a **debug script** that runs all these checks automatically?
