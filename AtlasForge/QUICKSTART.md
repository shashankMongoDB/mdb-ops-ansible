# Quick Start Guide

## Run on Ubuntu (Step-by-Step)

### 1. Install Dependencies

```bash
# Update system
sudo apt update

# Install Python 3 and pip
sudo apt install -y python3 python3-pip python3-venv

# Verify installation
python3 --version  # Should be 3.11+
pip3 --version
```

### 2. Setup Application

```bash
# Navigate to application directory
cd /path/to/AtlasForge

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Set all required environment variables
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

### 4. Verify Prerequisites

```bash
# Test Kubernetes connectivity
kubectl get nodes
kubectl get namespaces

# Test MongoDB connectivity (optional)
mongosh "$MCP_MONGODB_URI" --eval "db.adminCommand('ping')"
```

### 5. Run Application in FOREGROUND

```bash
# Make sure venv is activated
source venv/bin/activate

# Run with standard logging
uvicorn app.main:app --host 0.0.0.0 --port 8001 --log-level info

# OR run with debug logging for troubleshooting
uvicorn app.main:app --host 0.0.0.0 --port 8001 --log-level debug

# OR run with auto-reload for development
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

You should see:
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
```

### 6. Test the Service

Open a **new terminal** and test:

```bash
# Health check
curl http://localhost:8001/health

# Expected: {"status":"healthy"}
```

---

## API Testing with cURL

### 1. Create a Tenant

```bash
curl -X POST http://localhost:8001/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "tenantId": "t-acme",
    "displayName": "Acme Corporation"
  }'
```

**Expected Response:**
```json
{
  "tenantId": "t-acme",
  "namespace": "mdb-t-acme",
  "projectName": "mdb-t-acme-project",
  "status": "Active"
}
```

### 2. Create a MongoDB ReplicaSet

```bash
curl -X POST http://localhost:8001/tenants/t-acme/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentId": "rs-orders",
    "mongoVersion": "8.0.3",
    "members": 3,
    "displayName": "Orders Database",
    "environment": "prod"
  }'
```

**Expected Response:**
```json
{
  "tenantId": "t-acme",
  "deploymentId": "rs-orders",
  "mongoVersion": "8.0.3",
  "members": 3,
  "state": "Creating"
}
```

### 3. List Deployments

```bash
curl http://localhost:8001/tenants/t-acme/deployments
```

### 4. Get Deployment Details

```bash
curl http://localhost:8001/tenants/t-acme/deployments/rs-orders
```

---

## Postman Testing

### Import Collection

1. Open Postman
2. Click **Import**
3. Select file: `MongoDB_Control_Plane.postman_collection.json`
4. Update the `baseUrl` variable:
   - If testing on same machine: `http://localhost:8001`
   - If testing remotely: `http://<ubuntu-ip>:8001`

### Test Sequence

1. **Health Check** - Verify service is running
2. **Create Tenant - Acme** - Onboard first tenant
3. **Create Deployment - Orders DB** - Create MongoDB ReplicaSet
4. **List All Deployments for Tenant** - View all deployments
5. **Get Specific Deployment Details** - Check status

---

## Verify in Kubernetes

```bash
# Check tenant namespace was created
kubectl get namespace mdb-t-acme

# Check ConfigMap and Secret
kubectl get configmap -n mdb-t-acme
kubectl get secret -n mdb-t-acme

# Check MongoDB Custom Resource
kubectl get mongodb -n mdb-t-acme

# Describe MongoDB CR for detailed status
kubectl describe mongodb rs-orders -n mdb-t-acme

# Watch MongoDB CR status
kubectl get mongodb rs-orders -n mdb-t-acme -w
```

---

## Verify in MongoDB (Control Plane DB)

```bash
# Connect to control-plane MongoDB
mongosh "$MCP_MONGODB_URI"

# Switch to control plane database
use mdb_control_plane

# View tenants
db.tenants.find().pretty()

# View deployments
db.deployments.find().pretty()

# Find specific tenant
db.tenants.findOne({tenantId: "t-acme"})

# Find deployments for tenant
db.deployments.find({tenantId: "t-acme"}).pretty()
```

---

## Troubleshooting

### Service won't start

```bash
# Check Python version
python3 --version  # Must be 3.11+

# Check if port is already in use
sudo lsof -i :8001
sudo netstat -tuln | grep 8001

# Check if venv is activated
which python  # Should show path inside venv

# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

### Kubernetes errors

```bash
# Verify kubeconfig
kubectl config view
kubectl cluster-info

# Check kubeconfig path
ls -la /home/ubuntu/.kube/config

# Test with specific kubeconfig
export KUBECONFIG=/home/ubuntu/.kube/config
kubectl get nodes
```

### MongoDB connection errors

```bash
# Test MongoDB connectivity
mongosh "$MCP_MONGODB_URI" --eval "db.adminCommand('ping')"

# Check if MongoDB URI is exported
echo $MCP_MONGODB_URI

# Test from Python
python3 -c "from pymongo import MongoClient; client = MongoClient('$MCP_MONGODB_URI'); print(client.server_info())"
```

### View detailed logs

```bash
# Run with debug logging
uvicorn app.main:app --host 0.0.0.0 --port 8001 --log-level debug

# In another terminal, watch for errors
tail -f <log-output>
```

---

## Stop the Service

Press `CTRL+C` in the terminal running uvicorn.

---

## Common Error Responses

### 400 Bad Request
```json
{
  "detail": "tenantId 'INVALID!' is not DNS-safe (must be [a-z0-9-], max 63 chars)"
}
```

### 404 Not Found
```json
{
  "detail": "Tenant t-xyz not found"
}
```

### 409 Conflict
```json
{
  "detail": "Tenant t-acme already exists"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error",
  "detail": "<error details>"
}
```

Check the foreground terminal for detailed error traces.
