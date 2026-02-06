# API Reference

Base URL: `http://<your-server>:8001`

## Quick Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/tenants` | Create tenant |
| POST | `/tenants/{tenantId}/deployments` | Create deployment |
| GET | `/tenants/{tenantId}/deployments` | List deployments |
| GET | `/tenants/{tenantId}/deployments/{deploymentId}` | Get deployment details |

---

## Endpoints

### 1. Health Check

**Request:**
```http
GET /health
```

**Response: 200 OK**
```json
{
  "status": "healthy"
}
```

---

### 2. Create Tenant

Onboards a new tenant by creating Kubernetes namespace, ConfigMaps, and Secrets.

**Request:**
```http
POST /tenants
Content-Type: application/json

{
  "tenantId": "t-acme",
  "displayName": "Acme Corporation"
}
```

**Request Fields:**
- `tenantId` (string, required): DNS-safe identifier ([a-z0-9-], max 63 chars)
- `displayName` (string, required): Human-readable name

**Response: 201 Created**
```json
{
  "tenantId": "t-acme",
  "namespace": "mdb-t-acme",
  "projectName": "mdb-t-acme-project",
  "status": "Active"
}
```

**Errors:**
- `400 Bad Request`: Invalid tenantId format
- `409 Conflict`: Tenant already exists

**Kubernetes Resources Created:**
- Namespace: `mdb-{tenantId}`
- ConfigMap: `om-{tenantId}-project` (Ops Manager connection details)
- Secret: `om-{tenantId}-credentials` (Ops Manager API keys)
- Secret: `mongodb-admin-secret` (Generated admin password)

---

### 3. Create MongoDB ReplicaSet Deployment

Creates a MongoDB ReplicaSet by writing a MongoDB Custom Resource to Kubernetes.

**Request:**
```http
POST /tenants/{tenantId}/deployments
Content-Type: application/json

{
  "deploymentId": "rs-orders",
  "mongoVersion": "8.0.3",
  "members": 3,
  "displayName": "Orders Database",
  "environment": "prod"
}
```

**Path Parameters:**
- `tenantId` (string): Existing tenant identifier

**Request Fields:**
- `deploymentId` (string, required): DNS-safe identifier
- `mongoVersion` (string, required): MongoDB version (e.g., "8.0.3", "7.0.14")
- `members` (integer, required): Number of replica set members (1-50, default: 3)
- `displayName` (string, required): Human-readable name
- `environment` (string, optional): Environment tag (default: "prod")

**Response: 201 Created**
```json
{
  "tenantId": "t-acme",
  "deploymentId": "rs-orders",
  "mongoVersion": "8.0.3",
  "members": 3,
  "state": "Creating"
}
```

**Errors:**
- `400 Bad Request`: Invalid deploymentId format
- `404 Not Found`: Tenant does not exist
- `409 Conflict`: Deployment already exists

**Kubernetes Resources Created:**
- MongoDB CR: `{deploymentId}` in namespace `mdb-{tenantId}`

---

### 4. List Deployments

Lists all MongoDB deployments for a tenant.

**Request:**
```http
GET /tenants/{tenantId}/deployments
```

**Path Parameters:**
- `tenantId` (string): Tenant identifier

**Response: 200 OK**
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
    "state": "Running",
    "createdAt": "2026-02-07T10:35:00.123456+00:00"
  }
]
```

**Errors:**
- `404 Not Found`: Tenant does not exist

---

### 5. Get Deployment Details

Retrieves detailed information about a specific deployment, including live Kubernetes status.

**Request:**
```http
GET /tenants/{tenantId}/deployments/{deploymentId}
```

**Path Parameters:**
- `tenantId` (string): Tenant identifier
- `deploymentId` (string): Deployment identifier

**Response: 200 OK**
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

**Response Fields:**
- `state`: State from control-plane DB
- `k8sPhase`: Live status from Kubernetes MongoDB CR (may be null)

**Errors:**
- `404 Not Found`: Tenant or deployment does not exist

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
  "detail": "<detailed error message>"
}
```

---

## Deployment States

Possible values for `state` and `k8sPhase`:

- **Creating**: Initial state, MongoDB CR submitted to Kubernetes
- **Pending**: Kubernetes resources being provisioned
- **Running**: MongoDB cluster is operational
- **Failed**: Deployment encountered an error
- **Unknown**: Status cannot be determined

Note: `k8sPhase` reflects the actual Kubernetes CR status, while `state` is tracked in the control-plane database.

---

## Testing Examples

### Using cURL

```bash
# Create tenant
curl -X POST http://localhost:8001/tenants \
  -H "Content-Type: application/json" \
  -d '{"tenantId":"t-acme","displayName":"Acme Corp"}'

# Create deployment
curl -X POST http://localhost:8001/tenants/t-acme/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentId":"rs-orders",
    "mongoVersion":"8.0.3",
    "members":3,
    "displayName":"Orders DB",
    "environment":"prod"
  }'

# List deployments
curl http://localhost:8001/tenants/t-acme/deployments

# Get deployment details
curl http://localhost:8001/tenants/t-acme/deployments/rs-orders
```

### Using Python Requests

```python
import requests

BASE_URL = "http://localhost:8001"

# Create tenant
response = requests.post(
    f"{BASE_URL}/tenants",
    json={"tenantId": "t-acme", "displayName": "Acme Corp"}
)
print(response.json())

# Create deployment
response = requests.post(
    f"{BASE_URL}/tenants/t-acme/deployments",
    json={
        "deploymentId": "rs-orders",
        "mongoVersion": "8.0.3",
        "members": 3,
        "displayName": "Orders DB",
        "environment": "prod"
    }
)
print(response.json())

# List deployments
response = requests.get(f"{BASE_URL}/tenants/t-acme/deployments")
print(response.json())
```

---

## Rate Limits & Constraints

- **Tenant ID**: Max 63 characters, lowercase alphanumeric + hyphens
- **Deployment ID**: Max 63 characters, lowercase alphanumeric + hyphens
- **Members**: 1-50 (replica set size)
- **No authentication** in v1 (add before production)

---

## API Documentation

Interactive API documentation available at:
- **Swagger UI**: `http://localhost:8001/docs`
- **ReDoc**: `http://localhost:8001/redoc`
