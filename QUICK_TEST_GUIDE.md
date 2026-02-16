# Quick Test Guide

## 🚀 Quick Start

### **1. Restart Backend** (1 minute)

```bash
cd /home/ubuntu/mdbaas-repo/mdb-ops-ansible/AtlasForge
pkill -f uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload &

# Verify it's running
curl http://localhost:8001/health
# Expected: {"status":"healthy"}
```

---

### **2. Test Community Shutdown** (3 minutes)

```bash
# Assuming you have a Community deployment named "test-5-deployment"
# in tenant "t5"

# Step 1: Check current status
kubectl get pods -n mdb-t5 | grep test-5

# Should see 3 running pods

# Step 2: Shutdown via API
curl -X POST http://localhost:8001/tenants/t5/deployments/test-5-deployment/actions/shutdown

# Step 3: Wait 5 seconds, then check
sleep 5
kubectl get pods -n mdb-t5 | grep test-5

# Expected: No pods (all terminated)

# Step 4: Verify CR deleted
kubectl get mongodbcommunity test-5-deployment -n mdb-t5

# Expected: Error (not found)

# Step 5: Verify PVCs still exist
kubectl get pvc -n mdb-t5

# Expected: PVCs present (data preserved!)

# Step 6: Start deployment
curl -X POST http://localhost:8001/tenants/t5/deployments/test-5-deployment/actions/start

# Step 7: Watch pods come back
kubectl get pods -n mdb-t5 -w

# Expected: 3 pods created and become Running
```

---

### **3. Test Monitoring Auto-Enable** (2 minutes)

```bash
# Create a NEW deployment
curl -X POST http://localhost:8001/tenants/t-acme/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentId": "rs-mon-test",
    "type": "ReplicaSet",
    "mongoVersion": "8.0.19-ent",
    "displayName": "Monitoring Test",
    "environment": "dev",
    "members": 3
  }'

# Check if monitoring enabled
curl http://localhost:8001/tenants/t-acme/deployments/rs-mon-test | jq '.prometheusEnabled'

# Expected: true

# Check if ServiceMonitor created (if Prometheus installed)
kubectl get servicemonitor rs-mon-test -n mdb-t-acme

# If Prometheus not installed, this will fail (expected)
# But deployment still succeeds
```

---

### **4. Test UI** (2 minutes)

```bash
# Open UI
cd /home/ubuntu/mdbaas-repo/mdb-ops-ansible/AtlasForge-UI-Vite
npm run dev

# Navigate to: http://localhost:5173
# Click on any tenant
# You should see:
# - List view (not cards)
# - Status indicators (● ◐ ○)
# - Pod counts (e.g., "3/3")
# - Monitoring column shows ✓ or ✗
# - Chevron to expand (▶/▼)

# Click chevron on a deployment:
# - Should expand and show topology
# - See pod names and status
# - See "Running" or "Pending" for each pod

# Click deployment name:
# - Should navigate to detail page (existing functionality)
```

---

## ✅ Success Criteria

### **Community Shutdown:**
- ✅ API returns 200 OK
- ✅ All pods terminate within 10 seconds
- ✅ MongoDB CR is deleted
- ✅ PVCs remain (data not lost)
- ✅ UI shows "Shutdown" status

### **Community Start:**
- ✅ API returns 200 OK
- ✅ MongoDB CR is recreated
- ✅ Pods are created and become Running
- ✅ Same PVCs are reused (data intact)
- ✅ UI shows "Running" status

### **Monitoring:**
- ✅ New deployments have `prometheusEnabled: true`
- ✅ ServiceMonitor created (if Prometheus available)
- ✅ UI shows ✓ in Monitoring column
- ✅ No deployment failures

### **UI Polling:**
- ✅ Network tab shows requests every 10s
- ✅ Status updates automatically
- ✅ Expand/collapse works smoothly
- ✅ Pod status shows real-time

---

## ❌ Troubleshooting

### **Problem: Shutdown doesn't work**

```bash
# Check backend logs
tail -50 /home/ubuntu/mdbaas-repo/mdb-ops-ansible/AtlasForge/app.log

# Look for errors mentioning:
# - "Failed to delete MongoDBCommunity CR"
# - "Could not delete pod"
# - Permission errors

# Check if operator is running
kubectl get pods -n mongodb-operator-system

# Check RBAC
kubectl auth can-i delete mongodbcommunity --as=system:serviceaccount:default:default -n mdb-t5
```

---

### **Problem: Pods keep running after shutdown**

```bash
# Verify CR actually deleted
kubectl get mongodbcommunity -n <namespace>

# If CR still exists, operator is bringing pods back
# Solution: Check if backend has permissions to delete CR

# Manually delete for testing
kubectl delete mongodbcommunity <deployment-id> -n <namespace>
kubectl delete pods --all -n <namespace> --grace-period=0 --force
```

---

### **Problem: Monitoring shows disabled**

```bash
# Check deployment document
curl http://localhost:8001/tenants/<tenant-id>/deployments/<deployment-id> | jq

# Look for: "prometheusEnabled": true

# If false, deployment was created before this change
# Manually enable:
curl -X PATCH http://localhost:8001/tenants/<tenant-id>/deployments/<deployment-id>/monitoring \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

---

### **Problem: UI not showing new list view**

```bash
# Clear browser cache
# Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)

# Or rebuild frontend
cd AtlasForge-UI-Vite
rm -rf node_modules/.vite
npm run dev
```

---

## 📊 Expected Behavior

### **Shutdown Button:**
```
Before Click:
  Status: ● Running
  Pods: 3/3
  Button: [Shutdown]

After Click (10s later):
  Status: ○ Shutdown
  Pods: 0/3
  Button: [Start]
  Banner: "Deployment is shutdown. Click Start to resume."
```

### **Start Button:**
```
After Click:
  Status: ◐ Starting...
  Pods: 0/3 → 1/3 → 2/3 → 3/3
  
After 2 minutes:
  Status: ● Running
  Pods: 3/3
  Button: [Shutdown]
```

### **Monitoring Indicator:**
```
New Deployments:
  Monitoring: ✓ (green checkmark)
  Tooltip: "Prometheus metrics enabled"

Old Deployments (before this change):
  Monitoring: ✗ (gray X)
  Tooltip: "Monitoring not enabled"
```

---

## 🎯 Quick Verification Commands

```bash
# 1. Check backend running
curl -s http://localhost:8001/health | jq

# 2. Check deployments status
curl -s http://localhost:8001/tenants/t5/deployments-status | jq

# 3. Check specific deployment
curl -s http://localhost:8001/tenants/t5/deployments/test-5-deployment | jq '.status, .prometheusEnabled'

# 4. Check pods
kubectl get pods -n mdb-t5

# 5. Check PVCs (should always exist)
kubectl get pvc -n mdb-t5

# 6. Check CRs
kubectl get mongodbcommunity -n mdb-t5
```

---

## 📝 Notes

- **Data is NEVER lost** - PVCs are preserved during shutdown
- **Monitoring is free** - No resource cost, just metrics scraping
- **UI polls every 10s** - Status updates automatically
- **Shutdown takes 5-10s** - Be patient
- **Start takes 1-2 minutes** - Operator needs to reconcile

---

## 🆘 Need Help?

1. Check backend logs: `tail -f /path/to/backend/logs`
2. Check browser console: F12 → Console tab
3. Check Network tab: Look for failed requests
4. Run diagnostic commands above
5. Check Kubernetes: `kubectl describe pod <pod-name>`

---

## ✨ Quick Demo Flow

```bash
# Complete demo in 5 minutes:

# 1. Show current deployments
curl http://localhost:8001/tenants/t5/deployments-status | jq

# 2. Shutdown one
curl -X POST http://localhost:8001/tenants/t5/deployments/test-5-deployment/actions/shutdown

# 3. Verify pods gone
kubectl get pods -n mdb-t5

# 4. Show PVCs still there
kubectl get pvc -n mdb-t5

# 5. Start it back
curl -X POST http://localhost:8001/tenants/t5/deployments/test-5-deployment/actions/start

# 6. Watch pods return
kubectl get pods -n mdb-t5 -w

# 7. Show in UI
# Navigate to http://localhost:5173
# Click tenant → See Ops Manager-style list
# See status change from Shutdown → Starting → Running
```

---

**Done!** 🎉 If all tests pass, you're good to go!
