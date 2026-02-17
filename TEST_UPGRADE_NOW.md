# Test Community Upgrade - Quick Check

## Changes Made:

### 1. **Added Error Handling to CR Patch Functions**
- `patch_mongodb_enterprise_cr()` - now catches 404, 403, and other errors
- `patch_mongodb_community_cr()` - now catches 404, 403, and other errors
- Both now throw `ValueError` with clear error messages

### 2. **Fixed Upgrade Flow Order**
- **Before:** CR patch → DB update (even if patch failed!)
- **After:** CR patch → Only update DB if successful

### 3. **Added Version Format Fix for Community**
- Strips `-ent` suffix (Community uses "7.0.14", not "7.0.14-ent")

### 4. **Enhanced Logging**
- Shows requested version
- Shows cleaned version
- Shows current CR version
- Shows patch operation
- Shows success/failure

---

## Test Now:

### **Step 1: Restart Backend**

```bash
# Kill existing backend
pkill -f uvicorn

# Start with fresh logs
cd AtlasForge
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload 2>&1 | tee backend.log &
```

### **Step 2: Try Upgrade from UI**

1. Open UI
2. Go to Community deployment
3. Click [Upgrade Version]
4. Select a version (e.g., 7.0.15)
5. Click [Upgrade]

### **Step 3: Watch Backend Logs**

```bash
tail -f backend.log | grep -i "COMMUNITY_UPGRADE\|upgrade\|error"
```

**Expected logs (SUCCESS):**
```
[COMMUNITY_UPGRADE] Starting upgrade for mdb-t-comm/monitoring-comm
[COMMUNITY_UPGRADE] Requested version: 7.0.15-ent
[COMMUNITY_UPGRADE] Clean version (stripped -ent): 7.0.15
[COMMUNITY_UPGRADE] Current CR version: 7.0.14
[COMMUNITY_UPGRADE] Patching CR with: {'spec': {'version': '7.0.15'}}
[COMMUNITY_UPGRADE] Successfully patched CR to version 7.0.15
```

**Expected logs (FAILURE - Permission):**
```
[COMMUNITY_UPGRADE] Starting upgrade for mdb-t-comm/monitoring-comm
[COMMUNITY_UPGRADE] Requested version: 7.0.15-ent
[COMMUNITY_UPGRADE] Clean version (stripped -ent): 7.0.15
[COMMUNITY_UPGRADE] Current CR version: 7.0.14
[COMMUNITY_UPGRADE] Patching CR with: {'spec': {'version': '7.0.15'}}
ERROR: Failed to patch MongoDBCommunity CR monitoring-comm: Permission denied: Cannot patch MongoDBCommunity CR monitoring-comm in namespace mdb-t-comm. Check RBAC permissions.
```

**Expected logs (FAILURE - Not Found):**
```
[COMMUNITY_UPGRADE] Starting upgrade for mdb-t-comm/monitoring-comm
ERROR: MongoDBCommunity CR monitoring-comm not found in namespace mdb-t-comm
```

### **Step 4: Check UI Response**

**If SUCCESS:**
- No error message
- UI should show upgrade in progress

**If FAILURE:**
- UI shows error message with exact cause
- Database NOT updated (fixed!)

### **Step 5: Verify CR was Patched**

```bash
kubectl get mongodbcommunity monitoring-comm -n mdb-t-comm -o jsonpath='{.spec.version}'
```

Should show new version (e.g., `7.0.15`)

---

## Most Likely Issues:

### **Issue 1: RBAC Permissions (403)**

**Check:**
```bash
kubectl auth can-i patch mongodbcommunity \
  --as=system:serviceaccount:mdbaas-system:mdbaas-backend \
  -n mdb-t-comm
```

**If "no", fix:**
```bash
kubectl create clusterrole mdbaas-community-patch \
  --verb=patch,update,get,list \
  --resource=mongodbcommunity.mongodbcommunity.mongodb.com

kubectl create clusterrolebinding mdbaas-community-patch-binding \
  --clusterrole=mdbaas-community-patch \
  --serviceaccount=mdbaas-system:mdbaas-backend
```

### **Issue 2: CR Not Found (404)**

**Check:**
```bash
kubectl get mongodbcommunity -n mdb-t-comm
```

Should show your deployment.

### **Issue 3: Wrong API Group/Version**

**Check CRD:**
```bash
kubectl get crd mongodbcommunity.mongodbcommunity.mongodb.com -o yaml | grep -A 5 "versions:"
```

Should show `v1` as served version.

---

## What Changed vs Before:

### **Before:**
```python
# CR patch (might fail silently)
k8s.patch_mongodb_community_cr(namespace, deployment_id, patch)

# DB update (always happens!)
repo.update_deployment(tenant_id, deployment_id, {...})

# Returns success even if CR patch failed!
return {...}
```

**Result:** 
- UI thinks upgrade worked
- DB shows new version
- CR still has old version
- MongoDB still running old version

### **After:**
```python
try:
    # CR patch (throws error if fails)
    k8s.patch_mongodb_community_cr(namespace, deployment_id, patch)
except ValueError as e:
    # Error propagates to API
    raise ValueError(f"Failed to patch MongoDB CR: {str(e)}")

# DB update only if CR patch succeeded
repo.update_deployment(tenant_id, deployment_id, {...})

return {...}
```

**Result:**
- If CR patch fails → Error thrown
- API returns 400/500 error
- UI shows error message
- DB NOT updated
- User knows something is wrong

---

## Summary of Fixes:

1. ✅ **Strip `-ent` suffix** for Community versions
2. ✅ **Add error handling** to CR patch functions
3. ✅ **Fix upgrade order** - patch CR first, then update DB
4. ✅ **Add detailed logging** for debugging
5. ✅ **Proper error messages** - tell user exactly what failed

---

## Test Results Expected:

### **Scenario A: RBAC Issue (Most Likely)**
```
UI Error: "Failed to patch MongoDB CR: Permission denied: Cannot patch MongoDBCommunity CR monitoring-comm in namespace mdb-t-comm. Check RBAC permissions."

Database: NOT updated (old version still shown)
CR: NOT updated (old version)
```

**Fix:** Apply RBAC permissions above

### **Scenario B: Works Now!**
```
UI: No error, shows upgrade progress
Database: Updated to new version
CR: Updated to new version
Pods: Will start rolling upgrade
```

**Monitor:** Watch pods restart with new version

---

## Quick Verification:

```bash
# 1. Check current CR version
kubectl get mongodbcommunity monitoring-comm -n mdb-t-comm -o jsonpath='{.spec.version}'

# 2. Try upgrade via API
curl -X PATCH http://localhost:8001/tenants/t-comm/deployments/monitoring-comm/version \
  -H "Content-Type: application/json" \
  -d '{"mongoVersion": "7.0.15"}'

# 3. Check logs immediately
tail -20 backend.log | grep COMMUNITY_UPGRADE

# 4. Check if CR updated
kubectl get mongodbcommunity monitoring-comm -n mdb-t-comm -o jsonpath='{.spec.version}'
```

---

**Try it now and share what error you see in the logs!**
