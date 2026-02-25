# Installation Guide (Production) — MongoDB MDBaaS Control Plane

## 1. Scope

This guide installs the full stack:

- `backend` (FastAPI control plane)
- `frontend` (React/Vite UI)
- external dependencies already prepared by customer (Kubernetes, operator stack, infra)

The platform is **idempotent** for many bootstrap resources (namespace/configmaps/secrets/service accounts/roles) and will skip existing components where supported.

---

## 2. Prerequisites

## Infrastructure prerequisites

- Kubernetes cluster reachable from backend host
- MongoDB operators installed:
  - Enterprise path: MongoDB Enterprise Operator (MCK) + Ops Manager connectivity
  - Community path: MongoDB Community Operator CRDs/controllers
- Ops Manager available (EA path only)
- Metadata MongoDB for control-plane state
- S3 (or S3-compatible) + IAM/credentials for community backup (if used)

## Host prerequisites (backend/frontend VM or nodes)

- Linux host with outbound access to K8s API, Ops Manager, metadata DB
- Python 3.10+ (3.12 validated in your environment)
- Node.js 18+ and npm
- Git

---

## 3. Repository Layout

```text
mdbaas-control-plane/
├── backend/
└── frontend/
```

---

## 4. Backend Installation (`backend`)

## 4.1 Create virtual environment and install dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 4.2 Configure environment variables

Create `.env` (or export in systemd env) with production values:

```bash
# Metadata DB
MCP_MONGODB_URI="mongodb://<user>:<pass>@<metadata-host>:27017/?authSource=admin"
MCP_DB_NAME="mdb_control_plane"

# Kubernetes access
MCP_KUBECONFIG_PATH="/home/<user>/.kube/config"
MCP_NAMESPACE_PREFIX="mdb-"
MCP_OPERATOR_NAMESPACE="mongodb-operator"

# Ops Manager (EA)
MCP_OPS_MANAGER_URL="https://<ops-manager-host>"
MCP_OPS_MANAGER_ORG="<org-id>"
MCP_OM_GLOBAL_PUBLIC_KEY="<public-key>"
MCP_OM_GLOBAL_PRIVATE_KEY="<private-key>"
OPS_MANAGER_VERIFY_SSL="true"
# or OPS_MANAGER_CA_CERT_PATH="/path/to/ops-manager-ca.pem"

# Community backup defaults (optional)
COMMUNITY_BACKUP_S3_BUCKET="<bucket>"
COMMUNITY_BACKUP_S3_REGION="<region>"
COMMUNITY_BACKUP_S3_ENDPOINT_URL=""   # set for MinIO/S3-compatible
COMMUNITY_BACKUP_S3_NO_VERIFY_SSL="false"

# Runtime
MCP_LOG_LEVEL="INFO"
MCP_SERVICE_PORT="8001"
```

## 4.3 Start backend

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001 --log-level info
```

Health check:

```bash
curl http://<backend-host>:8001/health
```

Expected:

```json
{"status":"healthy"}
```

---

## 5. Frontend Installation (`frontend`)

## 5.1 Install dependencies

```bash
cd frontend
npm install
```

## 5.2 Configure environment

Create `.env`:

```bash
VITE_API_BASE_URL="http://<backend-host>:8001"
VITE_ENVIRONMENT="PROD"
```

## 5.3 Run (dev) or build (prod)

Development:

```bash
npm run dev
```

Production build:

```bash
npm run build
npm run preview
```

---

## 6. First-Time Platform Validation

## 6.1 Tenant onboarding test

```bash
curl -X POST "http://<backend-host>:8001/tenants" \
  -H "Content-Type: application/json" \
  -d '{
    "tenantId": "test4",
    "displayName": "Test Tenant",
    "plan": "community"
  }'
```

This validates namespace bootstrap + metadata DB writes.

## 6.2 Deployment creation test

```bash
curl -X POST "http://<backend-host>:8001/tenants/test4/deployments" \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentId": "e-commerce",
    "type": "ReplicaSet",
    "mongoVersion": "8.0.0",
    "displayName": "e-commerce",
    "environment": "prod",
    "members": 3
  }'
```

Backend creates CR; operator creates StatefulSet/pods/PVCs.

---

## 7. Runtime Architecture and Control Flow

```text
User
  │
  ▼
Frontend (React/Vite)
  │  REST API
  ▼
Backend (FastAPI)
  ├─ Metadata state ───────────────▶ Metadata MongoDB
  ├─ CR/Service/Job orchestration ─▶ Kubernetes API
  │                                  ├─ Enterprise Operator -> MongoDB StatefulSets/PVCs
  │                                  └─ Community Operator -> MongoDB StatefulSets/PVCs
  └─ EA backup/policy/restore  ────▶ Ops Manager APIs
```

## StatefulSet creation responsibility

- Backend creates/patches CRDs only.
- Operators reconcile CRDs and create StatefulSets.

---

## 8. EA vs Community Install Notes

## Enterprise Advanced (EA)

- Requires valid Ops Manager URL/org/API keys
- Tenant onboarding creates OM project config artifacts in tenant namespace
- Backup and restore are Ops Manager API-driven

## Community Edition

- No Ops Manager dependency
- Uses `MongoDBCommunity` CRs
- Backup/restore are K8s CronJob/Job based (S3/filesystem)

---

## 9. Security Hardening Checklist

- Remove default values from config; enforce env injection from secret manager
- Restrict CORS origins to frontend domain only
- Rotate Ops Manager and database credentials
- Restrict kubeconfig permissions and host network access
- Use TLS for frontend/backend and backend/Ops Manager/DB paths

---

## 10. Scalability and Reliability Checklist

- Run backend behind process manager (systemd/supervisor) with restart policy
- Put frontend behind reverse proxy/CDN
- Use HA metadata MongoDB deployment
- Monitor operator health, reconcile lag, and API error rates
- Use persistent centralized logs for backend and Kubernetes events

---

## 11. Troubleshooting Quick Map

- **UI cannot load data**: verify `VITE_API_BASE_URL`, backend CORS, backend health
- **Deployment stuck Creating**: inspect operator logs and CR events
- **EA backup unavailable**: verify Ops Manager project discovery and API key permissions
- **Community restore issues**: inspect restore job logs and S3 path/credentials
- **K8s websocket handshake errors**: restart backend and ensure pod exec uses isolated API client path

