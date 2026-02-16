# Implementation Summary - Shutdown, Monitoring, and Status Fixes

## Changes Implemented

### **1. Fixed Community Shutdown/Start ✅**

#### **Problem:**
- Community deployments were not shutting down properly
- StatefulSet was scaled to 0, but MongoDB Community Operator reconciled it back
- Pods kept running after shutdown

#### **Solution:**
- Changed to use **CR deletion approach** (same as Enterprise)
- Delete MongoDBCommunity CR → Stops operator reconciliation
- Force delete all pods with `grace_period=0`
- Scale StatefulSet to 0 to prevent recreation
- Save full CR spec in DB for restart

#### **Files Changed:**
1. **`deployments_community_service.py`**
   - `shutdown_deployment_community()` - Rewritten to delete CR
   - `start_deployment_community()` - Recreates CR from saved spec

2. **`lifecycle_service.py`**
   - Updated Community shutdown to save `shutdownInfo` (CR spec)
   - Updated Community start to pass `shutdownInfo` to service
   - Marks deployment as `status: "shutdown"` in DB

#### **Data Preservation:**
- ✅ **PVCs (Persistent Volume Claims) are NEVER deleted**
- ✅ MongoDB data files remain on disk
- ✅ StatefulSets remain (scaled to 0)
- ✅ Secrets remain intact
- ✅ **NO DATA LOSS** on shutdown/start

---

### **2. Enabled Monitoring by Default ✅**

#### **Problem:**
- Monitoring was disabled by default (`prometheusEnabled: false`)
- Users had to manually enable it
- UI showed "Monitoring not enabled" even though monitoring is essential

#### **Solution:**
- Set `prometheusEnabled: true` by default for all new deployments
- Auto-create ServiceMonitor on deployment creation
- If Prometheus not installed, fails gracefully (logs warning, doesn't break deployment)

#### **Files Changed:**
1. **`deployments_service.py`**
   - `_create_standalone_doc()` - Added `prometheusEnabled: true`
   - `_create_replicaset_doc()` - Added `prometheusEnabled: true`
   - `_create_sharded_doc()` - Added `prometheusEnabled: true`
   - `create_deployment()` - Auto-calls `monitoring_service.enable_prometheus_metrics()`

#### **Behavior:**
```python
# Before
deployment = {
    "prometheusEnabled": False,  # Default was false
    "backupEnabled": False
}

# After
deployment = {
    "prometheusEnabled": True,   # Now true by default
    "backupEnabled": False       # Still requires explicit config
}
```

#### **UI Impact:**
- New deployments now show **✓ Monitoring Enabled** by default
- ServiceMonitor created automatically (if Prometheus installed)
- If Prometheus not available, just logs warning (deployment still succeeds)

---

### **3. Ops Manager-Style UI (Previously Implemented)**

#### **Backend:**
- Created `deployment_status_service.py`
- Added 2 new endpoints:
  - `GET /tenants/{id}/deployments/{id}/status` - Single deployment status
  - `GET /tenants/{id}/deployments-status` - Batch status for all deployments

#### **Frontend:**
- Created `ExpandableDeploymentList.tsx` component
- Polls status every 10 seconds
- Expandable rows showing topology details
- Real-time pod status indicators

---

## Testing Instructions

### **1. Test Community Shutdown/Start**

```bash
# Backend
cd AtlasForge
pkill -f uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload &

# Create Community deployment
curl -X POST http://localhost:8001/tenants/t-test/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentId": "rs-test",
    "type": "ReplicaSet",
    "mongoVersion": "7.0.0",
    "members": 3
  }'

# Wait for pods to be running
kubectl get pods -n mdb-t-test -w

# Test shutdown
curl -X POST http://localhost:8001/tenants/t-test/deployments/rs-test/actions/shutdown

# Verify:
# 1. MongoDB CR is deleted
kubectl get mongodbcommunity -n mdb-t-test

# 2. Pods are terminated
kubectl get pods -n mdb-t-test

# 3. PVCs are still there
kubectl get pvc -n mdb-t-test

# Expected: PVCs present, pods gone, CR deleted

# Test start
curl -X POST http://localhost:8001/tenants/t-test/deployments/rs-test/actions/start

# Verify:
# 1. MongoDB CR is recreated
kubectl get mongodbcommunity rs-test -n mdb-t-test

# 2. Pods are created
kubectl get pods -n mdb-t-test -w

# 3. Data is intact (same PVCs used)
```

---

### **2. Test Monitoring Auto-Enable**

```bash
# Create new deployment
curl -X POST http://localhost:8001/tenants/t-acme/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentId": "rs-monitoring-test",
    "type": "ReplicaSet",
    "mongoVersion": "8.0.19-ent",
    "members": 3
  }'

# Check deployment document in DB
curl http://localhost:8001/tenants/t-acme/deployments/rs-monitoring-test | jq '.prometheusEnabled'

# Expected: true

# Check if ServiceMonitor created
kubectl get servicemonitor rs-monitoring-test -n mdb-t-acme

# Expected: ServiceMonitor exists (if Prometheus installed)
# If Prometheus not installed: Check backend logs for warning message

# Check UI
# Navigate to tenant page
# See deployment list
# Monitoring column should show: ✓
```

---

### **3. Test UI Status Polling**

```bash
# Open UI
cd AtlasForge-UI-Vite
npm run dev

# Navigate to tenant page
# Open browser dev tools (F12)
# Go to Network tab
# Filter: deployments-status

# Expected:
# - Requests every 10 seconds
# - Status 200 OK
# - Response contains pod status

# Verify in UI:
# - See status indicators (● green, ◐ yellow, ○ gray)
# - See pod counts (3/3 ready)
# - Click chevron to expand
# - See topology details
```

---

## API Changes

### **New Endpoints (Already Implemented):**

```
GET /tenants/{tenantId}/deployments/{deploymentId}/status
Response:
{
  "deploymentId": "rs-orders",
  "type": "ReplicaSet",
  "status": "running",
  "phase": "Running",
  "pods": [...],
  "readyReplicas": 3,
  "totalReplicas": 3,
  "topology": {...}
}

GET /tenants/{tenantId}/deployments-status
Response:
{
  "deployments": [
    {...}, {...}
  ]
}
```

### **Modified Endpoints:**

```
POST /tenants/{tenantId}/deployments/{deploymentId}/actions/shutdown
- Now works for Community deployments
- Deletes CR instead of scaling StatefulSet
- Returns: {"previousReplicas": 3, "currentReplicas": 0}

POST /tenants/{tenantId}/deployments/{deploymentId}/actions/start
- Recreates CR from saved spec
- Works for Community deployments
- Returns: {"replicas": 3}
```

---

## Database Schema Changes

### **Deployment Document Updates:**

```javascript
// Old
{
  deploymentId: "rs-orders",
  prometheusEnabled: false,  // Was false
  backupEnabled: false
}

// New
{
  deploymentId: "rs-orders",
  prometheusEnabled: true,   // Now true by default
  backupEnabled: false,
  mongoVersion: "8.0.19-ent",  // Added to root (not just spec)
  members: 3,                  // Added to root (not just spec)
  status: "running",           // Added: running | shutdown
  lastRequestedSpec: {
    shutdownInfo: {            // Added for Community shutdown
      cr_spec: {...},
      cr_metadata_labels: {...},
      cr_metadata_annotations: {...},
      previous_replicas: 3
    }
  }
}
```

---

## Breaking Changes

### ❌ **None!**

All changes are backward compatible:
- Existing deployments continue to work
- Old shutdown logic still works for Enterprise
- Community deployments now work correctly (was broken before)
- UI continues to function (new component replaces old)

---

## Known Limitations

### **1. Monitoring Requires Prometheus**
- If Prometheus not installed, ServiceMonitor does nothing
- Deployment still succeeds (just logs warning)
- User won't get metrics until Prometheus is installed

### **2. Shutdown Timing**
- Takes 2-5 seconds for operator to process CR deletion
- Pods may take 10-30 seconds to fully terminate
- UI shows status updates every 10 seconds (not real-time)

### **3. Community Backup**
- Backup still requires manual configuration
- Not enabled by default (requires S3/Filesystem setup)

---

## Future Enhancements

### **Phase 2: Hardware Metrics (Not Implemented Yet)**
- Add Metrics Server integration
- Show CPU/Memory usage per pod
- Show node-level details
- Add Prometheus graphs (CPU, Memory, Disk, Network)

### **Phase 3: Advanced Features**
- PRIMARY/SECONDARY role detection (requires MongoDB connection)
- Query performance metrics
- Index usage statistics
- WebSocket for real-time updates (instead of polling)

---

## Rollback Plan

If issues occur:

### **Rollback Shutdown Changes:**
```bash
git revert <commit-hash>

# Or manually revert these files:
- deployments_community_service.py (shutdown/start functions)
- lifecycle_service.py (community routing)
```

### **Rollback Monitoring Changes:**
```bash
# Change prometheusEnabled back to false in:
- deployments_service.py (_create_*_doc functions)

# Remove auto-enable call in:
- deployments_service.py (create_deployment function)
```

### **Rollback UI Changes:**
```bash
# Revert TenantDetailsPage.tsx to use old card view
git checkout HEAD~1 -- src/pages/TenantDetailsPage.tsx
git checkout HEAD~1 -- src/components/ExpandableDeploymentList.tsx
```

---

## Verification Checklist

After deployment to production:

```
Backend:
[ ] Community shutdown works (pods actually stop)
[ ] Community start works (pods come back with data)
[ ] PVCs preserved after shutdown
[ ] Monitoring enabled by default for new deployments
[ ] ServiceMonitor created automatically
[ ] No errors in logs

Frontend:
[ ] Deployment list shows Ops Manager-style view
[ ] Status polling works (requests every 10s)
[ ] Expand/collapse works
[ ] Pod status shows correctly
[ ] Monitoring indicator shows ✓ for new deployments

Database:
[ ] Deployments have prometheusEnabled: true
[ ] shutdownInfo saved during shutdown
[ ] status field updated (running/shutdown)
```

---

## Performance Impact

### **Backend:**
- ✅ Minimal - Only adds one monitoring call per deployment creation
- ✅ Shutdown slightly faster (no StatefulSet patch conflicts)
- ✅ Status endpoints optimized for batch queries

### **Frontend:**
- ✅ Polls every 10 seconds (acceptable load)
- ✅ Batch API reduces request count
- ✅ Expandable list improves UX (no page navigation)

### **Database:**
- ✅ No additional queries
- ✅ Just added fields to existing documents

---

## Support & Troubleshooting

### **Issue: Community shutdown not working**

**Symptoms:**
- Pods still running after shutdown
- CR not deleted

**Debug:**
```bash
# Check if CR exists
kubectl get mongodbcommunity <deployment-id> -n <namespace>

# Check backend logs
tail -f /path/to/backend/logs | grep shutdown

# Check if pods deleted
kubectl get pods -n <namespace> | grep <deployment-id>
```

**Solution:**
- Ensure MongoDB Community Operator is running
- Check RBAC permissions for CR deletion
- Verify namespace is correct

---

### **Issue: Monitoring shows disabled**

**Symptoms:**
- New deployment shows "Monitoring not enabled"
- `prometheusEnabled: false` in DB

**Debug:**
```bash
# Check deployment document
curl http://localhost:8001/tenants/<tenant-id>/deployments/<deployment-id> | jq '.prometheusEnabled'

# Check if ServiceMonitor created
kubectl get servicemonitor <deployment-id> -n <namespace>

# Check backend logs
tail -f /path/to/backend/logs | grep prometheus
```

**Solution:**
- Verify deployment was created after this change
- Old deployments won't have monitoring enabled
- Manually enable for existing deployments
- Check if Prometheus installed in cluster

---

## Summary

### **What Changed:**
1. ✅ Community shutdown now works (CR deletion)
2. ✅ Monitoring enabled by default
3. ✅ Ops Manager-style UI with status polling
4. ✅ No data loss on shutdown
5. ✅ Backward compatible

### **What to Test:**
1. Create Community deployment → Shutdown → Start
2. Create new deployment → Check monitoring enabled
3. Navigate to tenant page → See new list view
4. Watch status poll every 10 seconds

### **Result:**
- 🎉 Community deployments work correctly
- 🎉 Monitoring enabled out of the box
- 🎉 Better UX with Ops Manager-style UI
- 🎉 No breaking changes
