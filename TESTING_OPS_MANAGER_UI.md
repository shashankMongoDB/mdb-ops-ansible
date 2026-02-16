# Testing Ops Manager-Style UI

## How to Test

### **Step 1: Restart Backend**

```bash
cd /home/ubuntu/mdbaas-repo/mdb-ops-ansible/AtlasForge
pkill -f uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload &
```

### **Step 2: Test Status API**

```bash
# Test single deployment status
curl http://localhost:8001/tenants/t-acme/deployments/rs-orders/status | jq

# Expected response:
{
  "deploymentId": "rs-orders",
  "type": "ReplicaSet",
  "status": "running",
  "phase": "Running",
  "pods": [...],
  "readyReplicas": 3,
  "totalReplicas": 3,
  "topology": {
    "replicaSet": {
      "name": "rs-orders",
      "members": [...]
    }
  },
  "lastUpdated": "2026-02-16T10:30:00Z"
}

# Test batch status (all deployments)
curl http://localhost:8001/tenants/t-acme/deployments-status | jq

# Expected response:
{
  "deployments": [
    { "deploymentId": "rs-orders", ... },
    { "deploymentId": "rs-customers", ... }
  ]
}
```

### **Step 3: Check Frontend**

```bash
cd /home/ubuntu/mdbaas-repo/mdb-ops-ansible/AtlasForge-UI-Vite
npm run dev
```

### **Step 4: Test UI**

1. **Navigate to tenant details page**
   - Go to http://localhost:5173
   - Click on a tenant (e.g., "ACME")

2. **Verify List View**
   - ✅ See deployments in list format (not cards)
   - ✅ Each row shows: name, type, status, pods count, version
   - ✅ Status indicator (●/◐/○/✗) with color
   - ✅ Chevron (▶) on left side

3. **Test Expand/Collapse**
   - ✅ Click chevron → Row expands
   - ✅ See topology details (pods, shards, etc.)
   - ✅ Click again → Row collapses

4. **Test Navigation**
   - ✅ Click deployment name → Goes to details page
   - ✅ Click "Details" button → Goes to details page
   - ✅ Back button still works

5. **Test Status Polling**
   - ✅ Leave page open for 10+ seconds
   - ✅ Status should auto-update
   - ✅ Check browser console for API calls every 10s

6. **Test Different Deployment Types**

   **ReplicaSet:**
   - ✅ Shows "3 Members" in summary
   - ✅ Expand shows all 3 pods
   - ✅ Green ● if all ready

   **ShardedCluster:**
   - ✅ Shows "2 Shards • 2 Mongos" in summary
   - ✅ Expand shows shards section
   - ✅ Expand shows config servers section
   - ✅ Expand shows mongos section
   - ✅ Each section shows pod names and status

   **Shutdown Deployment:**
   - ✅ Gray ○ indicator
   - ✅ "Shutdown" phase
   - ✅ "0/3" pods
   - ✅ Expand shows "Deployment is shutdown" message

---

## What to Look For

### **✅ Success Indicators:**

1. **List renders correctly**
   - All deployments visible
   - Status icons show
   - Pod counts display

2. **Polling works**
   - Browser network tab shows requests every 10s
   - Status updates automatically
   - No errors in console

3. **Expand/collapse works**
   - Smooth transition
   - Topology details show correctly
   - Pod names visible

4. **Navigation works**
   - Can still access detail page
   - Back button works
   - No broken links

---

## ❌ Troubleshooting

### **Problem: "500 Internal Server Error" on status endpoint**

**Check:**
```bash
# Look at backend logs
tail -f /path/to/uvicorn/logs

# Common issues:
# - Kubernetes not accessible
# - Wrong namespace
# - Pod labels don't match
```

**Solution:**
```bash
# Test K8s access
kubectl get pods -n mdb-t-acme

# If fails, check kubeconfig
echo $KUBECONFIG
```

---

### **Problem: "Deployment status not updating"**

**Check:**
```bash
# Open browser console (F12)
# Look for errors in Network tab
# Should see requests to /deployments-status every 10s
```

**Solution:**
- Check if backend is running
- Check if CORS is enabled
- Clear browser cache

---

### **Problem: "Topology not showing when expanded"**

**Check:**
```bash
# Test API directly
curl http://localhost:8001/tenants/t-acme/deployments/rs-orders/status | jq '.topology'

# Should see:
{
  "replicaSet": {
    "name": "rs-orders",
    "members": [...]
  }
}
```

**Solution:**
- Check if pods exist in K8s
- Check pod labels match expected format
- Check namespace is correct

---

### **Problem: "All deployments show as 'pending'"**

**Possible causes:**
1. Pods are actually pending (check K8s)
2. Label selector not matching
3. Wrong namespace

**Debug:**
```bash
# Check actual pod status
kubectl get pods -n mdb-t-acme

# Check pod labels
kubectl get pods -n mdb-t-acme --show-labels

# Expected labels:
# ReplicaSet: app=rs-orders-svc
# ShardedCluster: app=sh-orders-shard-0-svc
```

---

### **Problem: "Frontend shows old card view"**

**Solution:**
```bash
# Clear cache and rebuild
cd AtlasForge-UI-Vite
rm -rf node_modules/.vite
npm run dev
```

---

## Expected Behavior for Each Status

### **running (Green ●):**
- All pods Running
- All pods Ready
- No issues

### **partial (Yellow ◐):**
- Some pods Running
- Some pods Pending
- Deployment in progress

### **pending (Yellow ◐):**
- All pods Pending
- Waiting for resources or image pull

### **shutdown (Gray ○):**
- 0 pods running
- Deployment.status === "shutdown" in DB
- Expand shows "Deployment is shutdown" message

### **error (Red ✗):**
- Pods in error state
- CrashLoopBackOff
- ImagePullBackOff

---

## Performance Check

### **Polling Performance:**
```bash
# Open browser dev tools
# Network tab
# Filter: /deployments-status

# Should see:
# - Requests every 10 seconds
# - Response time < 500ms
# - Status 200 OK
```

### **If slow (> 2 seconds):**
- Too many deployments? (add pagination)
- K8s API slow? (check cluster health)
- Network latency? (check backend location)

---

## Manual Testing Checklist

```
Frontend:
[ ] List view renders
[ ] Status icons show
[ ] Pod counts display
[ ] Chevron clickable
[ ] Expand shows topology
[ ] Collapse hides topology
[ ] Deployment name clickable
[ ] Details button works
[ ] Polling works (watch for 30s)
[ ] No console errors

Backend:
[ ] /deployments-status returns data
[ ] /deployments/{id}/status works
[ ] Status matches K8s reality
[ ] Topology includes all pods
[ ] Response time acceptable

Integration:
[ ] Status updates reflect K8s changes
[ ] Shutdown status shows correctly
[ ] Multiple deployment types work
[ ] Navigation preserved
[ ] Existing features work
```

---

## Next Steps After Testing

If everything works:
1. ✅ Commit changes
2. ✅ Create PR
3. ✅ Update documentation
4. ✅ Deploy to production

If issues found:
1. ❌ Check error logs
2. ❌ Test API directly
3. ❌ Verify K8s connectivity
4. ❌ Check browser console
5. ❌ Report bugs with details
