# MongoDB Control Plane - Deployment Guide

## Overview

MongoDB Control Plane (MDBaaS) is a production-ready, self-service platform for managing MongoDB deployments on Kubernetes. It supports both Enterprise (Ops Manager) and Community MongoDB editions with automated backup, monitoring, and lifecycle management.

---

## Prerequisites

### **What You Need:**

1. **Kubernetes Cluster** (Single or Multi-node)
   - Kubernetes version: 1.23+
   - Minimum 3 worker nodes (recommended)
   - Storage class for PersistentVolumes
   - LoadBalancer or NodePort support

2. **kubectl Access**
   - Configured `~/.kube/config`
   - Cluster admin permissions

3. **System Requirements**
   - **Control Plane Node:** 2 CPU, 4GB RAM
   - **Per MongoDB Deployment:** 
     - Standalone: 1 CPU, 2GB RAM
     - ReplicaSet (3 members): 3 CPU, 6GB RAM
     - ShardedCluster: Varies by configuration

**That's it!** Our deployment script will install everything else:
- MongoDB Enterprise Operator
- MongoDB Community Operator
- Ops Manager (optional)
- Prometheus + Grafana (optional)
- Backup infrastructure
- Control Plane backend + frontend
- Metadata database

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                        │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Phase 1: Operators (mongodb-operator namespace)   │    │
│  │  - MongoDB Enterprise Operator                     │    │
│  │  - MongoDB Community Operator                      │    │
│  │  - Ops Manager (optional)                          │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Phase 2: Control Plane (mdbaas-system namespace)  │    │
│  │  - Backend API (FastAPI)                           │    │
│  │  - Frontend UI (React)                             │    │
│  │  - Metadata Database (MongoDB)                     │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Phase 3: Monitoring (monitoring namespace)        │    │
│  │  - Prometheus                                      │    │
│  │  - Grafana                                         │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Phase 4: Backup Infrastructure                    │    │
│  │  - S3 bucket (for Community backups)               │    │
│  │  - IRSA roles (for EKS)                            │    │
│  │  - Backup CronJobs                                 │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Tenant Namespaces (created on-demand)             │    │
│  │  - mdb-{tenant-id}                                 │    │
│  │  - MongoDB deployments                             │    │
│  │  - Per-tenant resources                            │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### **Step 1: Clone Repository**

```bash
git clone https://github.com/your-org/mdb-ops-ansible.git
cd mdb-ops-ansible
```

---

### **Step 2: Configure Environment**

Copy and edit the production configuration:

```bash
cp config/production.env.example config/production.env
vi config/production.env
```

**Required Configuration:**

```bash
# Kubernetes Configuration
KUBECONFIG_PATH="/home/ubuntu/.kube/config"
NAMESPACE_PREFIX="mdb-"

# Control Plane Metadata Database
MCP_MONGODB_URI="mongodb://admin:password@metadata-db:27017/?authSource=admin"
MCP_DB_NAME="mdb_control_plane"

# Ops Manager (for Enterprise deployments)
OPS_MANAGER_URL="https://ops-manager.example.com:8080"
OPS_MANAGER_ORG_ID="your-org-id"
OPS_MANAGER_PUBLIC_KEY="your-public-key"
OPS_MANAGER_PRIVATE_KEY="your-private-key"

# Optional: Custom CA for Ops Manager SSL
OPS_MANAGER_CA_CERT_PATH="/path/to/ca.crt"
OPS_MANAGER_VERIFY_SSL="true"

# AWS Configuration (for Community backups)
AWS_REGION="us-east-1"
AWS_S3_BUCKET="mdbaas-community-backups"
AWS_ACCESS_KEY_ID="your-access-key"
AWS_SECRET_ACCESS_KEY="your-secret-key"

# UI Configuration
FRONTEND_PORT="3000"
BACKEND_PORT="8001"
```

---

### **Step 3: Deploy in Phases**

Our deployment script installs components in phases with dependency checks.

#### **Phase 1: Install Operators**

```bash
./scripts/deploy.sh --config config/production.env --phase operator
```

**What it installs:**
- MongoDB Enterprise Operator
- MongoDB Community Operator
- Custom Resource Definitions (CRDs)
- Operator ServiceAccounts and RBAC
- Operator namespace: `mongodb-operator`

**Checks:**
- ✅ CRDs are created
- ✅ Operators are running
- ✅ Webhooks are ready

**Duration:** ~3-5 minutes

---

#### **Phase 2: Install Ops Manager** (Optional - Enterprise only)

```bash
./scripts/deploy.sh --config config/production.env --phase ops-manager
```

**What it installs:**
- MongoDB Ops Manager deployment
- Ops Manager database
- Ops Manager backup daemon
- SSL/TLS certificates
- Initial organization and API keys

**Checks:**
- ✅ Ops Manager pods running
- ✅ Ops Manager UI accessible
- ✅ API authentication working

**Duration:** ~10-15 minutes

**Skip if:** Using existing Ops Manager or Community-only deployment

---

#### **Phase 3: Install Backup Infrastructure**

```bash
./scripts/deploy.sh --config config/production.env --phase appdb-backup
```

**What it installs:**
- S3 bucket for Community backups (if not exists)
- IAM roles and policies (EKS IRSA)
- Backup CronJob templates
- Restore job templates
- Backup retention policies

**Checks:**
- ✅ S3 bucket exists and accessible
- ✅ IAM roles configured
- ✅ Backup jobs can authenticate

**Duration:** ~2-3 minutes

---

#### **Phase 4: Install Monitoring**

```bash
./scripts/deploy.sh --config config/production.env --phase monitoring
```

**What it installs:**
- Prometheus deployment
- Grafana deployment
- Pre-configured dashboards
- AlertManager (optional)
- ServiceMonitor CRDs

**Checks:**
- ✅ Prometheus is scraping
- ✅ Grafana is accessible
- ✅ Dashboards are loaded

**Duration:** ~5-7 minutes

---

#### **Phase 5: Install Control Plane** (Backend + Frontend)

```bash
./scripts/deploy.sh --config config/production.env --phase control-plane
```

**What it installs:**
- Metadata MongoDB database
- Backend API (FastAPI)
- Frontend UI (React)
- LoadBalancer/Ingress
- SSL certificates (if configured)

**What it creates:**
- Namespace: `mdbaas-system`
- Deployment: `mdbaas-backend`
- Deployment: `mdbaas-frontend`
- Deployment: `mdbaas-metadata-db`
- Service: `mdbaas-backend-svc` (LoadBalancer)
- Service: `mdbaas-frontend-svc` (LoadBalancer)

**Checks:**
- ✅ Metadata DB is running
- ✅ Backend API health check passes
- ✅ Frontend is serving
- ✅ Services have external IPs

**Duration:** ~5-7 minutes

---

### **Step 4: Verify Installation**

```bash
# Check all components
./scripts/deploy.sh --config config/production.env --phase verify

# Or manually check
kubectl get pods -n mongodb-operator
kubectl get pods -n mdbaas-system
kubectl get pods -n monitoring

# Get service URLs
kubectl get svc -n mdbaas-system
```

**Expected Output:**

```
NAME                          TYPE           EXTERNAL-IP      PORT(S)
mdbaas-backend-svc            LoadBalancer   34.213.34.101    8001:30001/TCP
mdbaas-frontend-svc           LoadBalancer   34.213.34.102    3000:30002/TCP
mdbaas-metadata-db-svc        ClusterIP      10.100.10.50     27017/TCP
```

---

### **Step 5: Access the UI**

1. **Get Frontend URL:**
   ```bash
   export FRONTEND_URL=$(kubectl get svc mdbaas-frontend-svc -n mdbaas-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
   echo "Access UI at: http://${FRONTEND_URL}:3000"
   ```

2. **Open in browser:**
   ```
   http://34.213.34.102:3000
   ```

3. **Create your first tenant:**
   - Click **[+ Create Tenant]**
   - Enter Tenant ID: `demo-tenant`
   - Display Name: `Demo Tenant`
   - Plan: `Enterprise` or `Community`
   - Click **[Create]**

4. **Create your first MongoDB deployment:**
   - Select tenant: `demo-tenant`
   - Click **[+ Create Deployment]**
   - Type: `ReplicaSet`
   - Members: `3`
   - Version: `8.0.19-ent` (Enterprise) or `8.0.10` (Community)
   - Click **[Create]**

5. **Monitor deployment:**
   - Watch replica status in real-time
   - Access available when 1+ replica ready
   - Get connection string
   - Create DB users
   - Enable backup

---

## Deployment Script Reference

### **Usage**

```bash
./scripts/deploy.sh [OPTIONS]
```

### **Options**

```
--config FILE          Configuration file (required)
--phase PHASE          Deployment phase (required)
--skip-checks          Skip pre-installation checks
--dry-run              Show what would be installed without installing
--force                Force reinstall even if already exists
--uninstall            Uninstall the specified phase
--help                 Show help message
```

### **Phases**

| Phase | Description | Dependencies | Duration |
|-------|-------------|--------------|----------|
| `operator` | Install MongoDB operators | None | ~3-5 min |
| `ops-manager` | Install Ops Manager | `operator` | ~10-15 min |
| `appdb-backup` | Install backup infrastructure | `operator` | ~2-3 min |
| `monitoring` | Install Prometheus + Grafana | `operator` | ~5-7 min |
| `control-plane` | Install backend + frontend | `operator` | ~5-7 min |
| `verify` | Verify all components | All | ~1-2 min |

---

## Configuration File Reference

### **Complete Example: `config/production.env`**

```bash
#
# MongoDB Control Plane - Production Configuration
#

# ==========================================
# Kubernetes Configuration
# ==========================================
KUBECONFIG_PATH="/home/ubuntu/.kube/config"
NAMESPACE_PREFIX="mdb-"
OPERATOR_NAMESPACE="mongodb-operator"
CONTROL_PLANE_NAMESPACE="mdbaas-system"
MONITORING_NAMESPACE="monitoring"

# ==========================================
# Control Plane Metadata Database
# ==========================================
# MongoDB instance for storing control plane metadata
# (tenants, deployments, users, backup configs, etc.)
MCP_MONGODB_URI="mongodb://admin:SuperSecretPass123@mdbaas-metadata-db:27017/?authSource=admin"
MCP_DB_NAME="mdb_control_plane"

# ==========================================
# MongoDB Ops Manager (Enterprise)
# ==========================================
# External Ops Manager URL (if using existing) or leave blank to install new
OPS_MANAGER_URL="https://ops-manager.example.com:8080"
OPS_MANAGER_ORG_ID="69666befd5b6737b862a34b5"

# Ops Manager API Keys (Org Owner level)
OPS_MANAGER_PUBLIC_KEY="yqhrwzfm"
OPS_MANAGER_PRIVATE_KEY="99ad8914-3721-4249-83eb-d6d4c30b6ae5"

# SSL/TLS Configuration (optional)
OPS_MANAGER_CA_CERT_PATH="/etc/ssl/certs/ops-manager-ca.crt"
OPS_MANAGER_VERIFY_SSL="true"

# Install new Ops Manager (if blank above)
INSTALL_OPS_MANAGER="false"
OPS_MANAGER_VERSION="8.0.10"
OPS_MANAGER_ADMIN_EMAIL="admin@example.com"
OPS_MANAGER_ADMIN_PASSWORD="ChangeMe123!"

# ==========================================
# AWS Configuration (Community Backups)
# ==========================================
AWS_REGION="us-east-1"
AWS_S3_BUCKET="mdbaas-community-backups"
AWS_S3_PREFIX="community-mongodb-backup"

# Option 1: AWS Access Keys (for non-EKS)
AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

# Option 2: IRSA Role ARN (for EKS)
AWS_IRSA_ROLE_ARN="arn:aws:iam::123456789012:role/mdbaas-backup-s3-role"

# ==========================================
# Backup Configuration
# ==========================================
COMMUNITY_BACKUP_SCHEDULE="0 */4 * * *"  # Every 4 hours
COMMUNITY_BACKUP_RETENTION_DAYS="7"
COMMUNITY_BACKUP_MONGODUMP_IMAGE="mongo:8.0"
COMMUNITY_BACKUP_AWS_CLI_IMAGE="amazon/aws-cli:2.27.28"

# ==========================================
# Monitoring Configuration
# ==========================================
INSTALL_MONITORING="true"
PROMETHEUS_RETENTION="15d"
PROMETHEUS_STORAGE_SIZE="50Gi"
GRAFANA_ADMIN_PASSWORD="admin123"

# ==========================================
# Control Plane UI/API
# ==========================================
BACKEND_PORT="8001"
FRONTEND_PORT="3000"
BACKEND_IMAGE="your-registry/mdbaas-backend:latest"
FRONTEND_IMAGE="your-registry/mdbaas-frontend:latest"

# External access
BACKEND_SERVICE_TYPE="LoadBalancer"  # or NodePort
FRONTEND_SERVICE_TYPE="LoadBalancer"  # or NodePort

# Optional: Ingress configuration
USE_INGRESS="false"
INGRESS_CLASS="nginx"
INGRESS_HOST="mdbaas.example.com"
INGRESS_TLS_SECRET="mdbaas-tls"

# ==========================================
# Resource Limits
# ==========================================
# Backend
BACKEND_CPU_REQUEST="500m"
BACKEND_MEMORY_REQUEST="512Mi"
BACKEND_CPU_LIMIT="2000m"
BACKEND_MEMORY_LIMIT="2Gi"

# Frontend
FRONTEND_CPU_REQUEST="200m"
FRONTEND_MEMORY_REQUEST="256Mi"
FRONTEND_CPU_LIMIT="1000m"
FRONTEND_MEMORY_LIMIT="1Gi"

# Metadata DB
METADATA_DB_CPU_REQUEST="1000m"
METADATA_DB_MEMORY_REQUEST="2Gi"
METADATA_DB_CPU_LIMIT="2000m"
METADATA_DB_MEMORY_LIMIT="4Gi"
METADATA_DB_STORAGE_SIZE="20Gi"
METADATA_DB_STORAGE_CLASS="gp3"

# ==========================================
# Operator Configuration
# ==========================================
ENTERPRISE_OPERATOR_VERSION="1.30.0"
COMMUNITY_OPERATOR_VERSION="0.10.0"

# ==========================================
# Security
# ==========================================
# Enable Pod Security Standards
ENABLE_POD_SECURITY="true"
POD_SECURITY_STANDARD="restricted"

# Enable Network Policies
ENABLE_NETWORK_POLICIES="true"

# ==========================================
# Logging
# ==========================================
LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR
```

---

## Deployment Script Features

### **1. Idempotency**

The script checks if components are already installed:

```bash
# Check if operator exists
if kubectl get deployment mongodb-enterprise-operator -n mongodb-operator >/dev/null 2>&1; then
  echo "✅ MongoDB Enterprise Operator already installed"
  exit 0
fi
```

### **2. Dependency Checks**

Each phase verifies prerequisites:

```bash
# Phase: ops-manager requires operator
if ! kubectl get crd mongodb.mongodb.com >/dev/null 2>&1; then
  echo "❌ Operator not installed. Run: --phase operator first"
  exit 1
fi
```

### **3. Health Checks**

Waits for components to be ready:

```bash
# Wait for operator pods
kubectl wait --for=condition=ready pod \
  -l app=mongodb-enterprise-operator \
  -n mongodb-operator \
  --timeout=300s
```

### **4. Rollback Support**

Can uninstall phases cleanly:

```bash
./scripts/deploy.sh --config config/production.env --phase operator --uninstall
```

### **5. Dry Run Mode**

Preview what will be installed:

```bash
./scripts/deploy.sh --config config/production.env --phase operator --dry-run
```

---

## Post-Installation

### **1. Create Admin User**

```bash
# Get backend pod
BACKEND_POD=$(kubectl get pod -n mdbaas-system -l app=mdbaas-backend -o jsonpath='{.items[0].metadata.name}')

# Create admin user in metadata DB
kubectl exec -it $BACKEND_POD -n mdbaas-system -- python3 -c "
from app.services.mongo_repo import get_repo
repo = get_repo()
repo.create_admin_user('admin@example.com', 'AdminPass123!')
print('Admin user created')
"
```

### **2. Configure Ops Manager** (Enterprise)

If you installed new Ops Manager:

1. Access Ops Manager UI:
   ```bash
   kubectl get svc -n mongodb-operator | grep ops-manager
   ```

2. Complete first-time setup:
   - Create organization
   - Generate API keys
   - Update `config/production.env` with new keys
   - Restart backend:
     ```bash
     kubectl rollout restart deployment mdbaas-backend -n mdbaas-system
     ```

### **3. Configure Monitoring**

Access Grafana:

```bash
kubectl get svc -n monitoring | grep grafana
# Open http://<EXTERNAL-IP>:3000
# Login: admin / <GRAFANA_ADMIN_PASSWORD from config>
```

Import dashboards:
- MongoDB Overview
- Ops Manager Metrics
- Control Plane API Metrics

### **4. Test Deployment**

```bash
# Create test tenant
curl -X POST http://<BACKEND-IP>:8001/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "tenantId": "test-tenant",
    "displayName": "Test Tenant",
    "plan": "community"
  }'

# Create test MongoDB deployment
curl -X POST http://<BACKEND-IP>:8001/tenants/test-tenant/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentId": "rs-test",
    "type": "ReplicaSet",
    "mongoVersion": "8.0.10",
    "members": 3
  }'

# Watch deployment
kubectl get mongodbcommunity -n mdb-test-tenant -w
```

---

## Troubleshooting

### **Operator Not Starting**

```bash
# Check operator logs
kubectl logs -n mongodb-operator deployment/mongodb-enterprise-operator
kubectl logs -n mongodb-operator deployment/mongodb-community-operator

# Check CRDs
kubectl get crd | grep mongodb
```

### **Backend Cannot Connect to Metadata DB**

```bash
# Check metadata DB status
kubectl get pods -n mdbaas-system -l app=mdbaas-metadata-db

# Check backend logs
kubectl logs -n mdbaas-system deployment/mdbaas-backend

# Test connection
kubectl exec -it deployment/mdbaas-backend -n mdbaas-system -- \
  python3 -c "from app.services.mongo_repo import get_repo; get_repo().list_tenants()"
```

### **Ops Manager Connection Issues**

```bash
# Test Ops Manager connectivity
kubectl exec -it deployment/mdbaas-backend -n mdbaas-system -- \
  curl -u ${OPS_MANAGER_PUBLIC_KEY}:${OPS_MANAGER_PRIVATE_KEY} \
  ${OPS_MANAGER_URL}/api/public/v1.0/orgs/${OPS_MANAGER_ORG_ID}

# Check SSL certificate
kubectl exec -it deployment/mdbaas-backend -n mdbaas-system -- \
  openssl s_client -connect ops-manager.example.com:8080 -showcerts
```

### **Community Backups Failing**

```bash
# Check backup CronJob
kubectl get cronjob -n mdb-test-tenant

# Check backup job logs
kubectl logs -n mdb-test-tenant job/rs-test-backup-<timestamp>

# Test S3 access
kubectl exec -it deployment/mdbaas-backend -n mdbaas-system -- \
  aws s3 ls s3://mdbaas-community-backups/
```

### **Deployment Script Logs**

```bash
# All logs saved to
./logs/deploy-<phase>-<timestamp>.log

# View recent deployment
tail -f ./logs/deploy-operator-*.log
```

---

## Uninstallation

### **Uninstall Specific Phase**

```bash
# Uninstall control plane (keeps data)
./scripts/deploy.sh --config config/production.env --phase control-plane --uninstall

# Uninstall monitoring
./scripts/deploy.sh --config config/production.env --phase monitoring --uninstall

# Uninstall operators
./scripts/deploy.sh --config config/production.env --phase operator --uninstall
```

### **Complete Uninstall**

```bash
# Uninstall everything (destructive!)
./scripts/deploy.sh --config config/production.env --uninstall-all

# Or manually
kubectl delete namespace mdbaas-system
kubectl delete namespace mongodb-operator
kubectl delete namespace monitoring
kubectl delete crd -l app=mongodb
```

⚠️ **Warning:** This will delete all MongoDB deployments and data!

---

## Production Checklist

### **Before Going to Production:**

- [ ] K8s cluster has sufficient resources
- [ ] Storage class configured for PVs
- [ ] Backup S3 bucket created and accessible
- [ ] Ops Manager deployed and configured (Enterprise)
- [ ] SSL certificates installed
- [ ] Network policies reviewed
- [ ] Resource limits configured
- [ ] Monitoring dashboards imported
- [ ] Admin users created
- [ ] Test deployments successful
- [ ] Backup/restore tested
- [ ] Documentation reviewed
- [ ] Disaster recovery plan documented

### **Production Recommendations:**

- ✅ Use separate Ops Manager per environment
- ✅ Enable Pod Security Standards
- ✅ Use Network Policies for tenant isolation
- ✅ Configure resource quotas per tenant
- ✅ Enable audit logging
- ✅ Set up alerting (PagerDuty, Slack)
- ✅ Configure automated backups
- ✅ Test restore procedures
- ✅ Document runbooks
- ✅ Set up CI/CD for updates

---

## Next Steps

1. **Read the User Guide:** `UI_GUIDE.md`
2. **Explore API:** `API_DOCUMENTATION_AUDIT.md`
3. **Test with Postman:** Import `MongoDB_Control_Plane.postman_collection.json`
4. **Configure Monitoring:** Import Grafana dashboards
5. **Set Up Backups:** Test backup and restore procedures
6. **Train Users:** Share UI Guide with team

---

## Support

### **Documentation:**
- Deployment Guide (this file)
- User Guide: `UI_GUIDE.md`
- API Documentation: `API_DOCUMENTATION_AUDIT.md`
- Troubleshooting: `TROUBLESHOOTING.md`
- Architecture: `ARCHITECTURE.md`

### **Resources:**
- MongoDB Enterprise Operator: https://docs.mongodb.com/kubernetes-operator/
- MongoDB Community Operator: https://github.com/mongodb/mongodb-kubernetes-operator
- Ops Manager: https://docs.mongodb.com/ops-manager/

### **Get Help:**
- Open GitHub issue
- Contact support team
- Check logs: `./logs/`

---

**Ready to deploy? Run the first phase:**

```bash
./scripts/deploy.sh --config config/production.env --phase operator
```

🚀 **Let's get started!**
