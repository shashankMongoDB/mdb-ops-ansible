# Setup and Run Guide

## Prerequisites on Ubuntu

1. **Python 3.11+** must be installed
2. **kubectl** configured with access to your Kubernetes cluster
3. **kubeconfig** at `/home/ubuntu/.kube/config`
4. Network access to:
   - Kubernetes API server
   - MongoDB control-plane instance
   - Ops Manager instance

## Installation Steps

### 1. Install Python and pip (if not already installed)

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
```

### 2. Clone/Copy the application code

```bash
# Navigate to your application directory
cd /path/to/AtlasForge
```

### 3. Create and activate virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Set environment variables

**Option A: Export manually in terminal**

```bash
export MCP_MONGODB_URI="mongodb://shashank:password@ec2-34-213-34-101.us-west-2.compute.amazonaws.com:27017/?authSource=admin"
export MCP_DB_NAME="mdb_control_plane"
export MCP_KUBECONFIG_PATH="/home/ubuntu/.kube/config"
export MCP_NAMESPACE_PREFIX="mdb-"
export MCP_OPS_MANAGER_URL="http://ec2-35-88-225-248.us-west-2.compute.amazonaws.com:8080"
export MCP_OPS_MANAGER_ORG="69666befd5b6737b862a34b5"
export MCP_OM_GLOBAL_PUBLIC_KEY="yqhrwzfm"
export MCP_OM_GLOBAL_PRIVATE_KEY="99ad8914-3721-4249-83eb-d6d4c30b6ae5"
export MCP_LOG_LEVEL="INFO"
export MCP_SERVICE_PORT="8001"
```

**Option B: Create .env file and load it**

```bash
cat > .env << 'EOF'
export MCP_MONGODB_URI="mongodb://shashank:password@ec2-34-213-34-101.us-west-2.compute.amazonaws.com:27017/?authSource=admin"
export MCP_DB_NAME="mdb_control_plane"
export MCP_KUBECONFIG_PATH="/home/ubuntu/.kube/config"
export MCP_NAMESPACE_PREFIX="mdb-"
export MCP_OPS_MANAGER_URL="http://ec2-35-88-225-248.us-west-2.compute.amazonaws.com:8080"
export MCP_OPS_MANAGER_ORG="69666befd5b6737b862a34b5"
export MCP_OM_GLOBAL_PUBLIC_KEY="yqhrwzfm"
export MCP_OM_GLOBAL_PRIVATE_KEY="99ad8914-3721-4249-83eb-d6d4c30b6ae5"
export MCP_LOG_LEVEL="INFO"
export MCP_SERVICE_PORT="8001"
EOF

source .env
```

### 6. Verify kubeconfig

```bash
# Test kubectl connectivity
kubectl get nodes
kubectl get namespaces
```

### 7. Run the application in FOREGROUND (to track errors)

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Run with uvicorn in foreground
uvicorn app.main:app --host 0.0.0.0 --port 8001 --log-level info
```

**For development with auto-reload (restarts on code changes):**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload --log-level debug
```

### 8. Verify service is running

Open another terminal and test:

```bash
curl http://localhost:8001/health
# Should return: {"status":"healthy"}
```

---

## Postman API Testing

### Base Configuration

- **Base URL**: `http://<your-ubuntu-ip>:8001`
- If testing locally on Ubuntu: `http://localhost:8001`
- If testing from another machine: `http://<ubuntu-vm-ip>:8001`

---

### 1. Health Check

**Request:**
```
GET http://localhost:8001/health
```

**Expected Response:**
```json
{
  "status": "healthy"
}
```

---

### 2. Create Tenant (Onboard)

**Request:**
```
POST http://localhost:8001/tenants
Content-Type: application/json
```

**Payload:**
```json
{
  "tenantId": "t-acme",
  "displayName": "Acme Corporation"
}
```

**Expected Response (201 Created):**
```json
{
  "tenantId": "t-acme",
  "namespace": "mdb-t-acme",
  "projectName": "mdb-t-acme-project",
  "status": "Active"
}
```

**Additional Test Cases:**

*Tenant 2:*
```json
{
  "tenantId": "t-globex",
  "displayName": "Globex Industries"
}
```

*Tenant 3:*
```json
{
  "tenantId": "t-initech",
  "displayName": "Initech LLC"
}
```

---

### 3. Create ReplicaSet Deployment

**Request:**
```
POST http://localhost:8001/tenants/t-acme/deployments
Content-Type: application/json
```

**Payload:**
```json
{
  "deploymentId": "rs-orders",
  "mongoVersion": "8.0.3",
  "members": 3,
  "displayName": "Orders Database",
  "environment": "prod"
}
```

**Expected Response (201 Created):**
```json
{
  "tenantId": "t-acme",
  "deploymentId": "rs-orders",
  "mongoVersion": "8.0.3",
  "members": 3,
  "state": "Creating"
}
```

**Additional Test Cases:**

*Deployment 2 for same tenant:*
```json
{
  "deploymentId": "rs-customers",
  "mongoVersion": "8.0.3",
  "members": 3,
  "displayName": "Customers Database",
  "environment": "prod"
}
```

*Deployment with different member count:*
```json
{
  "deploymentId": "rs-analytics",
  "mongoVersion": "7.0.14",
  "members": 5,
  "displayName": "Analytics Database",
  "environment": "staging"
}
```

---

### 4. List All Deployments for a Tenant

**Request:**
```
GET http://localhost:8001/tenants/t-acme/deployments
```

**Expected Response (200 OK):**
```json
[
  {
    "tenantId": "t-acme",
    "deploymentId": "rs-orders",
    "displayName": "Orders Database",
    "environment": "prod",
    "mongoVersion": "8.0.3",
    "members": 3,
    "state": "Creating",
    "createdAt": "2026-02-07T10:30:00.123456+00:00"
  },
  {
    "tenantId": "t-acme",
    "deploymentId": "rs-customers",
    "displayName": "Customers Database",
    "environment": "prod",
    "mongoVersion": "8.0.3",
    "members": 3,
    "state": "Creating",
    "createdAt": "2026-02-07T10:35:00.123456+00:00"
  }
]
```

---

### 5. Get Specific Deployment Details

**Request:**
```
GET http://localhost:8001/tenants/t-acme/deployments/rs-orders
```

**Expected Response (200 OK):**
```json
{
  "tenantId": "t-acme",
  "deploymentId": "rs-orders",
  "displayName": "Orders Database",
  "environment": "prod",
  "mongoVersion": "8.0.3",
  "members": 3,
  "createdAt": "2026-02-07T10:30:00.123456+00:00",
  "state": "Creating",
  "k8sPhase": "Running"
}
```

Note: `k8sPhase` will be present only if the MongoDB CR has status information from Kubernetes.

---

## Error Scenarios to Test

### 1. Duplicate Tenant (409 Conflict)

Try creating the same tenant twice:

```
POST http://localhost:8001/tenants
```
```json
{
  "tenantId": "t-acme",
  "displayName": "Acme Corp Duplicate"
}
```

**Expected Response (409):**
```json
{
  "detail": "Tenant t-acme already exists"
}
```

---

### 2. Invalid Tenant ID (400 Bad Request)

```json
{
  "tenantId": "T_ACME_INVALID!",
  "displayName": "Invalid Tenant"
}
```

**Expected Response (400):**
```json
{
  "detail": "tenantId 'T_ACME_INVALID!' is not DNS-safe (must be [a-z0-9-], max 63 chars)"
}
```

---

### 3. Deployment for Non-existent Tenant (404)

```
POST http://localhost:8001/tenants/t-nonexistent/deployments
```
```json
{
  "deploymentId": "rs-test",
  "mongoVersion": "8.0.3",
  "members": 3,
  "displayName": "Test DB",
  "environment": "dev"
}
```

**Expected Response (404):**
```json
{
  "detail": "Tenant t-nonexistent not found"
}
```

---

### 4. Duplicate Deployment (409)

Try creating the same deployment twice for a tenant:

```
POST http://localhost:8001/tenants/t-acme/deployments
```
```json
{
  "deploymentId": "rs-orders",
  "mongoVersion": "8.0.3",
  "members": 3,
  "displayName": "Orders DB Duplicate",
  "environment": "prod"
}
```

**Expected Response (409):**
```json
{
  "detail": "Deployment rs-orders already exists for tenant t-acme"
}
```

---

## Monitoring and Logs

When running in foreground, you'll see logs like:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
INFO:     127.0.0.1:54321 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:54322 - "POST /tenants HTTP/1.1" 201 Created
```

**To see more detailed logs**, use debug level:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --log-level debug
```

---

## Verifying in Kubernetes

After creating deployments, verify in Kubernetes:

```bash
# List namespaces
kubectl get namespaces | grep mdb-

# Check resources in a tenant namespace
kubectl get all -n mdb-t-acme

# Check MongoDB CRs
kubectl get mongodb -n mdb-t-acme

# Describe a MongoDB CR
kubectl describe mongodb rs-orders -n mdb-t-acme

# Check ConfigMaps and Secrets
kubectl get configmaps -n mdb-t-acme
kubectl get secrets -n mdb-t-acme
```

---

## Stopping the Application

Press `CTRL+C` in the terminal where uvicorn is running.

---

## Running in Background (Production)

If you need to run in background:

```bash
# Using nohup
nohup uvicorn app.main:app --host 0.0.0.0 --port 8001 > app.log 2>&1 &

# View logs
tail -f app.log

# Stop the process
ps aux | grep uvicorn
kill <PID>
```

**Better option: Use systemd service** (see systemd section if needed)
