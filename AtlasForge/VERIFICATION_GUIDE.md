# Verification Guide - Ops Manager & Kubernetes

## Understanding Deployment States

When you create a deployment, the control plane:
1. Creates MongoDB CR in Kubernetes
2. Records state as "Creating" in control-plane DB
3. MongoDB Enterprise Operator (MCK) reconciles the CR
4. MCK creates pods, services, and registers with Ops Manager
5. Ops Manager provisions and monitors the cluster

**The "Creating" state in the API is the INITIAL state** - it doesn't auto-update. You need to check Ops Manager and Kubernetes for actual status.

---

## Check Status in Ops Manager

### 1. Access Ops Manager UI

```
URL: http://ec2-35-88-225-248.us-west-2.compute.amazonaws.com:8080
```

### 2. Navigate to Project

1. Log in to Ops Manager
2. Go to **Projects** (top navigation)
3. Look for project: **`mdb-t-acme-project`** (or whatever tenant you created)
   - Project name format: `mdb-{tenantId}-project`

### 3. View MongoDB Deployments

Once in the project:
- You should see your MongoDB deployment (e.g., `rs-orders`)
- Check the **Status** column:
  - **Goal State: OK** ✅ - Deployment is healthy
  - **Goal State: Pending** ⏳ - Still provisioning
  - **Goal State: Failed** ❌ - Error occurred

### 4. What to Look For

**If deployment is successful:**
- Status shows as "Running" or "OK"
- You can see cluster topology (3 members for rs-orders)
- Monitoring data appears (metrics, logs)
- You can view connection strings

**If project doesn't exist:**
- Ops Manager integration might not be working
- Check if MCK operator is creating the project automatically
- You may need to manually create the project first

**If deployment shows errors:**
- Click on the deployment name
- Check **Alerts** tab for specific errors
- Common issues:
  - Network connectivity between K8s and Ops Manager
  - Invalid API keys
  - Resource constraints

---

## Check Status in Kubernetes

### 1. Check MongoDB Custom Resource Status

```bash
# Get the MongoDB CR
kubectl get mongodb rs-orders -n mdb-t-acme

# Expected output:
# NAME        PHASE     VERSION   AGE
# rs-orders   Running   8.0.3     5m
```

**Possible PHASE values:**
- **Pending**: Initial state, operator starting work
- **Running**: All pods running, cluster healthy
- **Failed**: Error occurred
- **Updating**: Configuration change in progress

### 2. Get Detailed Status

```bash
# Describe the MongoDB CR for detailed information
kubectl describe mongodb rs-orders -n mdb-t-acme
```

Look for:
```yaml
Status:
  Phase: Running
  Version: 8.0.3
  Members: 3
  Link: https://ops-manager-url/projects/xxx/deployments/rs-orders
  Current State:
    State: Running
    Members Ready: 3/3
  Conditions:
    Type: Ready
    Status: True
    Reason: AllMembersReady
```

### 3. Check Pods Created by Operator

```bash
# List all pods in the namespace
kubectl get pods -n mdb-t-acme

# Expected output:
# NAME              READY   STATUS    RESTARTS   AGE
# rs-orders-0       2/2     Running   0          5m
# rs-orders-1       2/2     Running   0          4m
# rs-orders-2       2/2     Running   0          3m
```

**Healthy state:** All pods should show `Running` status with `2/2` ready containers.

### 4. Check Pod Logs

```bash
# Check mongodb-agent container logs (connects to Ops Manager)
kubectl logs rs-orders-0 -n mdb-t-acme -c mongodb-agent

# Check mongod container logs
kubectl logs rs-orders-0 -n mdb-t-acme -c mongod
```

Look for:
- Successful connection to Ops Manager
- Replica set initialization
- No authentication errors

### 5. Check Services Created

```bash
kubectl get svc -n mdb-t-acme

# Expected services:
# NAME                    TYPE        CLUSTER-IP      PORT(S)
# rs-orders               ClusterIP   10.x.x.x        27017/TCP
# rs-orders-0             ClusterIP   10.x.x.x        27017/TCP
# rs-orders-1             ClusterIP   10.x.x.x        27017/TCP
# rs-orders-2             ClusterIP   10.x.x.x        27017/TCP
```

### 6. Check StatefulSet

```bash
kubectl get statefulset -n mdb-t-acme

# Expected:
# NAME        READY   AGE
# rs-orders   3/3     5m
```

---

## Timeline: What Happens After Creation

| Time | What's Happening |
|------|------------------|
| 0s | API creates MongoDB CR in Kubernetes |
| 0s | Control-plane DB records state as "Creating" |
| 1-5s | MCK operator detects new CR |
| 5-30s | Operator creates StatefulSet, Services, ConfigMaps |
| 30s-2m | Kubernetes schedules pods, pulls images |
| 2-5m | Pods start, mongodb-agent connects to Ops Manager |
| 5-10m | Ops Manager provisions automation config |
| 10-15m | MongoDB processes start on all members |
| 15-20m | Replica set is initialized and syncing |
| 20-30m | **Cluster is fully operational** ✅ |

**Note:** Times vary based on:
- Container image pull speed
- Storage provisioning speed
- Ops Manager response time
- Network latency

---

## Troubleshooting: Deployment Stuck in "Creating"

### Issue 1: Ops Manager Project Doesn't Exist

**Check if auto-creation is enabled:**

```bash
# Check the ConfigMap created by control plane
kubectl get configmap om-t-acme-project -n mdb-t-acme -o yaml
```

Expected data:
```yaml
data:
  baseUrl: http://ec2-35-88-225-248.us-west-2.compute.amazonaws.com:8080
  projectName: mdb-t-acme-project
  orgId: 69666befd5b6737b862a34b5
```

**Manual fix:**
1. Log in to Ops Manager
2. Go to Organization (ID: `69666befd5b6737b862a34b5`)
3. Create project manually: **`mdb-t-acme-project`**
4. Verify API keys have access to this project

### Issue 2: Invalid API Keys

**Check the credentials secret:**

```bash
kubectl get secret om-t-acme-credentials -n mdb-t-acme -o yaml
```

**Test API keys manually:**

```bash
curl -u "yqhrwzfm:99ad8914-3721-4249-83eb-d6d4c30b6ae5" \
  http://ec2-35-88-225-248.us-west-2.compute.amazonaws.com:8080/api/public/v1.0/orgs/69666befd5b6737b862a34b5
```

Should return organization details. If it fails, API keys are invalid.

### Issue 3: MongoDB Operator Not Running

**Check if MCK operator is installed:**

```bash
kubectl get pods -n mongodb

# Expected output:
# NAME                                           READY   STATUS    RESTARTS   AGE
# mongodb-enterprise-operator-xxxxx              1/1     Running   0          5d
```

**If not found:**
- MongoDB Enterprise Kubernetes Operator is not installed
- Install MCK first: https://www.mongodb.com/docs/kubernetes-operator/stable/tutorial/install-k8s-operator/

### Issue 4: Network Connectivity Issues

**Test from inside cluster:**

```bash
# Run a test pod
kubectl run test-curl --image=curlimages/curl -it --rm -- sh

# From inside the pod, test Ops Manager connectivity
curl -v http://ec2-35-88-225-248.us-west-2.compute.amazonaws.com:8080/api/public/v1.0
```

If this fails, Kubernetes pods cannot reach Ops Manager (firewall/network issue).

### Issue 5: Pods Stuck in Pending

**Check pod status:**

```bash
kubectl get pods -n mdb-t-acme
kubectl describe pod rs-orders-0 -n mdb-t-acme
```

Common reasons:
- Insufficient cluster resources (CPU/Memory)
- Storage class not available
- Node selector not matching any nodes

---

## Check Control Plane DB vs Live Status

The control plane API shows cached state. To sync with live status:

### Current Behavior

```bash
# API shows cached state
curl http://localhost:8001/tenants/t-acme/deployments/rs-orders
```

Returns:
```json
{
  "state": "Creating",      # From control-plane DB (cached)
  "k8sPhase": "Running"     # Live from Kubernetes
}
```

**Important:** The `state` field is what was recorded at creation time. The `k8sPhase` field shows the **actual live status** from Kubernetes.

### Sync Status (Manual Script)

Create a script to update the control plane DB:

```bash
# Get live status from Kubernetes
PHASE=$(kubectl get mongodb rs-orders -n mdb-t-acme -o jsonpath='{.status.phase}')

# Update in MongoDB control plane DB
mongosh "$MCP_MONGODB_URI" --eval "
  use mdb_control_plane;
  db.deployments.updateOne(
    {_id: 't-acme:rs-orders'},
    {\$set: {'lastKnownStatus.phase': '$PHASE'}}
  )
"
```

---

## Expected Results Summary

### ✅ Successful Deployment Checklist

- [ ] Kubernetes namespace exists: `mdb-t-acme`
- [ ] ConfigMap and Secrets created in namespace
- [ ] MongoDB CR exists with `Phase: Running`
- [ ] 3 pods running: `rs-orders-0`, `rs-orders-1`, `rs-orders-2`
- [ ] StatefulSet shows `3/3` ready
- [ ] Services created for each replica
- [ ] Ops Manager shows project: `mdb-t-acme-project`
- [ ] Ops Manager shows deployment: `rs-orders` with status "OK"
- [ ] Can see monitoring metrics in Ops Manager
- [ ] Can connect to MongoDB using connection string from Ops Manager

### ⏳ Still Provisioning

- Pods show `ContainerCreating` or `Pending`
- Ops Manager shows deployment but status is "Pending"
- MongoDB CR phase is `Pending`

### ❌ Failed Deployment

- Pods show `Error`, `CrashLoopBackOff`, or `ImagePullBackOff`
- MongoDB CR phase is `Failed`
- Ops Manager shows alerts/errors
- No pods created after 5 minutes

---

## Quick Check Commands

```bash
# One-liner to check everything
echo "=== Namespace ===" && \
kubectl get namespace mdb-t-acme && \
echo "=== MongoDB CR ===" && \
kubectl get mongodb -n mdb-t-acme && \
echo "=== Pods ===" && \
kubectl get pods -n mdb-t-acme && \
echo "=== Services ===" && \
kubectl get svc -n mdb-t-acme
```

---

## Access MongoDB Deployment

Once deployment is **Running** in both K8s and Ops Manager:

### 1. Get Connection String from Ops Manager

1. Go to your project in Ops Manager
2. Click on `rs-orders` deployment
3. Click **Connect**
4. Copy the connection string

Format: `mongodb://rs-orders-0.rs-orders-svc.mdb-t-acme.svc.cluster.local:27017,rs-orders-1...`

### 2. Get Admin Password

```bash
kubectl get secret mongodb-admin-secret -n mdb-t-acme -o jsonpath='{.data.password}' | base64 -d
```

### 3. Connect from Inside Cluster

```bash
# Run mongosh in a pod
kubectl run -it mongosh --image=mongodb/mongodb-community-server:8.0.3 --rm -- bash

# Inside the pod
mongosh "mongodb://dbAdmin:<password>@rs-orders-0.rs-orders-svc.mdb-t-acme.svc.cluster.local:27017/?replicaSet=rs-orders&authSource=admin"
```

---

## Need Help?

If deployment is still stuck, share:
1. Output of `kubectl describe mongodb rs-orders -n mdb-t-acme`
2. Output of `kubectl get pods -n mdb-t-acme`
3. Logs from `kubectl logs rs-orders-0 -n mdb-t-acme -c mongodb-agent`
4. Screenshot from Ops Manager showing project and deployment status
