# Ops Manager Verification Guide

## Understanding the "Creating" State

When your API shows `"state": "Creating"`, this is the **initial cached state** stored when the deployment was created. The actual deployment process happens asynchronously in Kubernetes and Ops Manager.

---

## Where to Check Real Status

### 1. **Ops Manager UI** (Most Important)
   - Shows the actual MongoDB cluster status
   - Provides monitoring, alerts, and configuration
   - This is your source of truth for cluster health

### 2. **Kubernetes** 
   - Shows pod and MongoDB CR status
   - Tells you if containers are running
   - Shows operator reconciliation status

### 3. **Control Plane API** (Our Service)
   - Shows cached metadata
   - `k8sPhase` field shows live K8s status
   - `state` field is cached and needs manual sync

---

## Step-by-Step: Check in Ops Manager

### Access Ops Manager

```
URL: http://ec2-35-88-225-248.us-west-2.compute.amazonaws.com:8080
Organization ID: 69666befd5b6737b862a34b5
```

### Scenario 1: Project Exists Automatically ✅

**What to look for:**

1. **Login to Ops Manager**
2. **Click "Projects"** in top navigation
3. **Look for project name:** `mdb-t-acme-project` (or `mdb-{your-tenant-id}-project`)
4. **Click on the project**
5. **You should see:**
   - Deployment name: `rs-orders` (or your deployment ID)
   - Type: Replica Set
   - Members: 3 nodes
   - Status: One of:
     - ✅ **OK / Running** - Fully operational
     - ⏳ **Pending / Configuring** - Still setting up
     - ⚠️ **Warning** - Non-critical issues
     - ❌ **Error** - Failed deployment

**If you see this:**
- Your deployment is successful!
- Click on deployment name to see:
  - Topology (3 replica set members)
  - Monitoring graphs
  - Connection strings
  - Configuration options

---

### Scenario 2: Project Doesn't Exist ⚠️

This means the MongoDB Operator hasn't created the project automatically.

**Why this happens:**
- Ops Manager project auto-creation is disabled
- API keys don't have Organization Owner permissions
- Network connectivity issue between K8s and Ops Manager

**Manual Fix:**

1. **Login to Ops Manager**
2. **Click "Projects"** → **"New Project"**
3. **Enter project name:** `mdb-t-acme-project` (exact name from ConfigMap)
4. **Click "Next"** → **"Create Project"**
5. **Add API Key to project:**
   - Go to **"Access Manager"** → **"API Keys"**
   - Add your global API key (`yqhrwzfm`) with **"Project Owner"** role
6. **Wait 2-5 minutes** - MongoDB Operator should detect project and provision cluster
7. **Refresh** - deployment should now appear

---

### Scenario 3: Project Exists but No Deployment ❓

**Possible causes:**

1. **MongoDB CR not created in Kubernetes**
   ```bash
   kubectl get mongodb -n mdb-t-acme
   # If empty, CR wasn't created by control plane
   ```

2. **MongoDB Operator not running**
   ```bash
   kubectl get pods -n mongodb
   # Should show: mongodb-enterprise-operator-xxxx
   ```

3. **Operator can't reach Ops Manager**
   - Check pod logs:
   ```bash
   kubectl logs -n mongodb <operator-pod-name>
   # Look for connection errors to Ops Manager
   ```

---

## Step-by-Step: Check in Kubernetes

### 1. Check if MongoDB CR Exists

```bash
kubectl get mongodb -n mdb-t-acme
```

**Expected output:**
```
NAME        PHASE     VERSION   AGE
rs-orders   Running   8.0.3     15m
```

**Possible PHASE values:**
- **Pending** → Still provisioning (wait 5-15 min)
- **Running** → Fully operational ✅
- **Failed** → Error occurred ❌
- **Updating** → Configuration change in progress

### 2. Get Detailed Status

```bash
kubectl describe mongodb rs-orders -n mdb-t-acme
```

Look for:
```yaml
Status:
  Phase: Running
  Version: 8.0.3
  Members: 3
  Opsmanager:
    Url: http://ec2-35-88-225-248.us-west-2.compute.amazonaws.com:8080
    Project: mdb-t-acme-project
  Last Transition: 2026-02-07T10:45:00Z
  
Events:
  Type    Reason                 Message
  ----    ------                 -------
  Normal  MongoDBCreated         MongoDB resource created
  Normal  StatefulSetCreated     StatefulSet rs-orders created
  Normal  ServiceCreated         Services created
  Normal  OpsManagerRegistered   Registered with Ops Manager
  Normal  ClusterReady           MongoDB cluster is ready
```

### 3. Check Pods

```bash
kubectl get pods -n mdb-t-acme
```

**Healthy output:**
```
NAME          READY   STATUS    RESTARTS   AGE
rs-orders-0   2/2     Running   0          15m
rs-orders-1   2/2     Running   0          14m
rs-orders-2   2/2     Running   0          13m
```

**Problem indicators:**
- `0/2` in READY column → Containers not starting
- `Pending` status → K8s can't schedule pod
- `Error` or `CrashLoopBackOff` → Container failing
- `ImagePullBackOff` → Can't pull container image

### 4. Check Logs (if issues)

```bash
# Check mongodb-agent logs (connects to Ops Manager)
kubectl logs rs-orders-0 -n mdb-t-acme -c mongodb-agent

# Check mongod logs
kubectl logs rs-orders-0 -n mdb-t-acme -c mongod
```

**Look for:**
- ✅ `Successfully registered with Ops Manager`
- ✅ `Replica set initialized`
- ❌ `Failed to connect to Ops Manager`
- ❌ `Authentication failed`
- ❌ `Connection timeout`

---

## Timeline: What to Expect

| Time | Status | Where to Check |
|------|--------|----------------|
| **0-30 sec** | Creating | API shows "Creating" |
| **30 sec - 2 min** | Pending | K8s shows MongoDB CR in "Pending" phase |
| **2-5 min** | Provisioning | Pods start appearing, Status: ContainerCreating |
| **5-10 min** | Connecting | Pods running, Agent connecting to Ops Manager |
| **10-15 min** | Configuring | Ops Manager shows deployment, Status: Configuring |
| **15-20 min** | Initializing | MongoDB processes starting, Replica set init |
| **20-30 min** | **Running ✅** | **Ops Manager shows "OK", K8s shows "Running"** |

**Note:** First deployment may take longer due to image pulls and storage provisioning.

---

## Quick Status Check Commands

### Check Everything at Once

```bash
#!/bin/bash
TENANT="t-acme"
DEPLOYMENT="rs-orders"
NAMESPACE="mdb-${TENANT}"

echo "=== MongoDB CR Status ==="
kubectl get mongodb $DEPLOYMENT -n $NAMESPACE

echo ""
echo "=== Pods ==="
kubectl get pods -n $NAMESPACE

echo ""
echo "=== Services ==="
kubectl get svc -n $NAMESPACE

echo ""
echo "=== Events (last 10) ==="
kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | tail -10
```

Save as `check_status.sh` and run: `bash check_status.sh`

---

## Sync Control Plane DB with Live Status

The control plane API caches the initial "Creating" state. To update it with live status:

### Option 1: Use the Sync Script

```bash
# Make sure MCP_MONGODB_URI is set
export MCP_MONGODB_URI="mongodb://shashank:password@ec2-34-213-34-101.us-west-2.compute.amazonaws.com:27017/?authSource=admin"

# Run sync script
bash sync_status.sh t-acme rs-orders
```

This will:
1. Fetch live phase from Kubernetes
2. Update control-plane MongoDB database
3. Show current status from all sources

### Option 2: Manual Update

```bash
# Get live phase
PHASE=$(kubectl get mongodb rs-orders -n mdb-t-acme -o jsonpath='{.status.phase}')

# Update DB
mongosh "$MCP_MONGODB_URI" --eval "
  use mdb_control_plane;
  db.deployments.updateOne(
    {_id: 't-acme:rs-orders'},
    {\$set: {'lastKnownStatus.phase': '$PHASE'}}
  )
"

# Verify via API
curl http://localhost:8001/tenants/t-acme/deployments/rs-orders | jq
```

Now the API will show updated status.

---

## Common Issues & Solutions

### Issue 1: "Creating" for 30+ minutes

**Diagnosis:**
```bash
kubectl get pods -n mdb-t-acme
kubectl describe mongodb rs-orders -n mdb-t-acme
```

**Common causes:**
- Pods stuck in `Pending` → Check: `kubectl describe pod rs-orders-0 -n mdb-t-acme`
- Pods in `ImagePullBackOff` → Can't pull MongoDB Enterprise image
- No pods at all → MongoDB Operator not working

**Solution:**
1. Check operator logs: `kubectl logs -n mongodb <operator-pod>`
2. Verify CRDs installed: `kubectl get crd | grep mongodb`
3. Check resource quotas: `kubectl describe namespace mdb-t-acme`

### Issue 2: Ops Manager shows "Failed" or "Error"

**Check Ops Manager alerts:**
1. Go to deployment in Ops Manager
2. Click **"Alerts"** tab
3. Read error messages

**Common errors:**
- **"Agent cannot connect"** → Network/firewall issue
- **"Authentication failed"** → Invalid API keys
- **"Automation config error"** → Ops Manager version incompatibility

**Solution:**
- Test connectivity from pod:
  ```bash
  kubectl exec -it rs-orders-0 -n mdb-t-acme -c mongodb-agent -- curl http://ec2-35-88-225-248.us-west-2.compute.amazonaws.com:8080
  ```

### Issue 3: Project exists but deployment not showing

**This means:** MongoDB CR exists in K8s but not registered with Ops Manager.

**Check:**
```bash
# Check if operator is watching the namespace
kubectl get mongodb rs-orders -n mdb-t-acme -o yaml
```

Look for:
```yaml
status:
  opsManager:
    url: http://...
    project: mdb-t-acme-project
    status: "Registered"  # Should be "Registered"
```

If status is not "Registered":
- Check agent logs in pods
- Verify API keys have project access
- Check Ops Manager API is reachable

---

## Success Indicators ✅

**You know it's working when:**

1. ✅ **Kubernetes shows:**
   ```
   kubectl get mongodb rs-orders -n mdb-t-acme
   NAME        PHASE     VERSION   AGE
   rs-orders   Running   8.0.3     20m
   ```

2. ✅ **Ops Manager shows:**
   - Project: `mdb-t-acme-project` exists
   - Deployment: `rs-orders` shows "OK" status
   - Topology shows 3 members, all healthy
   - Monitoring graphs showing metrics

3. ✅ **You can connect:**
   - Get connection string from Ops Manager
   - Connect with mongosh successfully
   - Can read/write data

---

## What to Check in Ops Manager UI

Once deployment shows in Ops Manager:

### 1. Deployment Overview
- **Status:** Should be "OK" (green)
- **Version:** Should match what you specified (8.0.3)
- **Members:** Should show 3 nodes

### 2. Topology
- Click deployment → **"Deployment"** tab
- Should show: `rs-orders` (replica set)
- 3 members: Primary, Secondary, Secondary
- All green checkmarks

### 3. Metrics & Monitoring
- Click **"Monitoring"** tab
- Graphs should show:
  - Operations per second
  - Connections
  - Memory usage
  - Disk usage

### 4. Connection String
- Click **"Connect"** button
- Copy connection string:
  ```
  mongodb://rs-orders-0.rs-orders-svc.mdb-t-acme.svc.cluster.local:27017,
          rs-orders-1.rs-orders-svc.mdb-t-acme.svc.cluster.local:27017,
          rs-orders-2.rs-orders-svc.mdb-t-acme.svc.cluster.local:27017/
          ?replicaSet=rs-orders
  ```

### 5. Alerts (if any)
- Click **"Alerts"** tab
- Should be empty if everything is healthy
- If there are alerts, read and address them

---

## Next Steps After Deployment is Running

1. **Get admin password:**
   ```bash
   kubectl get secret mongodb-admin-secret -n mdb-t-acme -o jsonpath='{.data.password}' | base64 -d
   ```

2. **Connect to MongoDB:**
   ```bash
   kubectl run -it mongosh --image=mongo:8.0.3 --rm -- \
     mongosh "mongodb://dbAdmin:<password>@rs-orders-0.rs-orders-svc.mdb-t-acme.svc.cluster.local:27017/?authSource=admin"
   ```

3. **Test database operations:**
   ```javascript
   // In mongosh
   use testdb
   db.test.insertOne({message: "Hello from control plane!"})
   db.test.find()
   ```

4. **Monitor in Ops Manager:**
   - Watch metrics in real-time
   - Set up alerts for your use case
   - Configure backups if needed

---

## Summary

**The "Creating" state is normal initially.** To see actual status:

1. **Check Ops Manager** (primary source of truth)
   - URL: http://ec2-35-88-225-248.us-west-2.compute.amazonaws.com:8080
   - Project: `mdb-{tenantId}-project`

2. **Check Kubernetes** (infrastructure status)
   - `kubectl get mongodb -n mdb-{tenantId}`
   - Look for `Phase: Running`

3. **Update control plane** (sync cached state)
   - Run `sync_status.sh` script
   - Or query API with `k8sPhase` field (shows live status)

**Typical deployment takes 15-30 minutes from creation to fully operational.**
