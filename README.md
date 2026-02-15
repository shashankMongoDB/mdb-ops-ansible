# MDBaaS Control Plane - Atlas Forge

**MongoDB Database-as-a-Service (MDBaaS) Accelerator Platform**

A production-ready control plane for MongoDB Database-as-a-Service offerings, enabling service providers to rapidly deploy, manage, and monetize MongoDB infrastructure at scale.

---

## Table of Contents

1. [Overview](#overview)
2. [What is MDBaaS Accelerator?](#what-is-mdbaas-accelerator)
3. [Architecture](#architecture)
4. [Technology Stack](#technology-stack)
5. [Prerequisites](#prerequisites)
6. [Installation & Setup](#installation--setup)
7. [Features](#features)
   - [Tenant & Deployment Management](#tenant--deployment-management)
   - [DB User Management](#db-user-management)
   - [Backup Management](#backup-management)
   - [Monitoring Integration](#monitoring-integration)
8. [Enterprise vs Community Deployments](#enterprise-vs-community-deployments)
9. [Configuration Reference](#configuration-reference)
10. [Troubleshooting](#troubleshooting)

---

## Overview

**Atlas Forge** is a MongoDB-as-a-Service control plane that enables infrastructure providers, cloud platforms, and enterprises to offer MongoDB database services with minimal operational overhead.

### Key Capabilities

- **Multi-Tenant Management**: Isolate customers with namespace-based tenancy
- **Dual Deployment Models**: Support both Enterprise (Ops Manager) and Community (Standalone) MongoDB
- **Automated Lifecycle**: Deploy, scale, upgrade, and delete MongoDB clusters via UI
- **Integrated Backups**: S3 and Filesystem backup options with automated retention
- **Database User Management**: Self-service user creation with role-based access
- **Monitoring Integration**: Prometheus scrape configurations with auto-discovery
- **External Connectivity**: Automatic NodePort provisioning for external access

---

## What is MDBaaS Accelerator?

### The Challenge

Building a MongoDB-as-a-Service platform from scratch requires:
- Complex Kubernetes operator integration
- Multi-tenancy isolation and RBAC
- Backup and disaster recovery workflows
- Monitoring and alerting setup
- User self-service portals
- Security and compliance controls

**Time to build**: 6-12 months of engineering effort

### The Solution

**Atlas Forge** provides a **production-ready control plane** that accelerates MongoDB service delivery:

✅ **Deploy in Days, Not Months**: Pre-built UI, API, and automation  
✅ **White-Label Ready**: Customizable branding and tenant isolation  
✅ **Enterprise & Community**: Support both paid (Enterprise) and freemium (Community) tiers  
✅ **Cloud-Native**: Kubernetes-native with GitOps compatibility  
✅ **Extensible**: REST API for integration with billing, ITSM, and portals  

### Use Cases

| Provider Type | Use Case |
|--------------|----------|
| **Cloud Providers** | Offer MongoDB as a managed service alongside compute/storage |
| **Managed Service Providers (MSPs)** | Add MongoDB to service catalog with automated provisioning |
| **Enterprises** | Internal developer platform (IDP) for MongoDB self-service |
| **SaaS Platforms** | Embedded database service for customer workloads |

### Business Benefits

- **Faster Time-to-Market**: Launch MongoDB services in weeks
- **Lower OpEx**: Automated operations reduce manual toil
- **Scalable**: Handle hundreds of tenants on shared infrastructure
- **Monetization Ready**: Integrate with billing systems via metadata APIs

---

## Architecture

### Physical Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Client Browser / API                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                   ┌─────────▼──────────┐
                   │   Load Balancer    │
                   │   (External IP)    │
                   └─────────┬──────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼─────┐      ┌─────▼──────┐    ┌──────▼─────┐
    │ UI (Vite)│      │  API (Fast │    │  MongoDB   │
    │  Port    │      │  API)      │    │  Control   │
    │  5173    │      │  Port 8001 │    │  Plane DB  │
    └──────────┘      └────┬───────┘    └────────────┘
                           │
                    ┌──────▼────────┐
                    │  Kubernetes   │
                    │    Cluster    │
                    └───────┬───────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────▼──────┐    ┌───────▼────────┐  ┌──────▼─────────┐
   │ MongoDB   │    │  MongoDB       │  │  Prometheus    │
   │ Enterprise│    │  Community     │  │  Monitoring    │
   │ Operator  │    │  Operator      │  │  Stack         │
   └───────────┘    └────────────────┘  └────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────▼──────┐    ┌───────▼────────┐  ┌──────▼─────────┐
   │ Ops       │    │  MongoDB       │  │  S3 / NFS      │
   │ Manager   │    │  Community     │  │  Backup        │
   │ (Ent)     │    │  Clusters      │  │  Storage       │
   └───────────┘    └────────────────┘  └────────────────┘
```

### Logical Architecture

```
┌────────────────────────────────────────────────────────────┐
│                     Presentation Layer                      │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Vite React UI                                       │ │
│  │  - Tenant Management   - Deployment Lifecycle        │ │
│  │  - User Management     - Backup Configuration        │ │
│  │  - Monitoring Setup    - Connection Info             │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────┬───────────────────────────────┘
                             │ REST API
┌────────────────────────────▼───────────────────────────────┐
│                      Application Layer                      │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  FastAPI Services                                    │ │
│  │  - Tenants         - Lifecycle    - Monitoring       │ │
│  │  - Deployments     - Scaling      - DB Users         │ │
│  │  - Backup (S3/FS)  - Ops Manager  - K8s Client       │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────┬───────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼─────┐    ┌─────────▼────────┐  ┌───────▼────────┐
│  MongoDB    │    │  Kubernetes      │  │  Ops Manager   │
│  Metadata   │    │  API             │  │  REST API      │
│  Repository │    │  (CRDs, Pods,    │  │  (Enterprise)  │
│             │    │   Services)      │  │                │
└─────────────┘    └──────────────────┘  └────────────────┘
```

### Data Flow

1. **User Interaction**: User interacts with Vite UI
2. **API Request**: UI sends REST API calls to FastAPI backend
3. **Tenant Isolation**: Backend creates namespaced Kubernetes resources
4. **Operator Reconciliation**: MongoDB operators detect CR changes and deploy clusters
5. **Connectivity**: K8s services (ClusterIP + NodePort) enable internal/external access
6. **Monitoring**: Prometheus scrapes metrics from MongoDB pods
7. **Backup**: CronJobs run mongodump and upload to S3/Filesystem
8. **Metadata Tracking**: All tenant/deployment info stored in control plane MongoDB

---

## Technology Stack

### Backend
- **Language**: Python 3.12+
- **Framework**: FastAPI (async REST API)
- **Database**: MongoDB (control plane metadata)
- **K8s Client**: kubernetes-client/python
- **Ops Manager Client**: Custom REST API wrapper

### Frontend
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite 5
- **Styling**: Tailwind CSS
- **UI Components**: Headless UI
- **HTTP Client**: Axios
- **Routing**: React Router v6

### Infrastructure
- **Orchestration**: Kubernetes 1.28+
- **MongoDB Operators**:
  - MongoDB Enterprise Operator (for Enterprise plan)
  - MongoDB Community Operator (for Community plan)
- **Ops Manager**: 6.x+ (for Enterprise deployments)
- **Monitoring**: Prometheus (optional)

### Backup Storage
- **S3**: AWS S3 or S3-compatible (MinIO, Wasabi, etc.)
- **Filesystem**: NFS, EFS, or any PVC-mountable storage

---

## Prerequisites

### Infrastructure Requirements

#### 1. Kubernetes Cluster
- **Version**: 1.28+ (tested on 1.30)
- **Node Count**: Minimum 3 worker nodes
- **Resources per Node**:
  - CPU: 4 cores
  - Memory: 16 GB RAM
  - Storage: 100 GB SSD
- **Network**: VPC with private subnet for pods
- **Access**: kubectl configured with cluster-admin rights

#### 2. MongoDB Operators Installed

**Enterprise Operator** (for Enterprise plan deployments):
```bash
kubectl apply -f https://raw.githubusercontent.com/mongodb/mongodb-enterprise-kubernetes/master/crds.yaml
kubectl apply -f https://raw.githubusercontent.com/mongodb/mongodb-enterprise-kubernetes/master/mongodb-enterprise.yaml
```

**Community Operator** (for Community plan deployments):
```bash
helm repo add mongodb https://mongodb.github.io/helm-charts
helm install community-operator mongodb/community-operator --namespace mongodb --create-namespace
```

#### 3. Ops Manager (for Enterprise Deployments)
- **Version**: 6.0+
- **Organization ID**: Pre-created organization
- **API Key**: Organization-level programmatic API key with "Organization Owner" role
- **Network**: Accessible from Kubernetes cluster

#### 4. Control Plane MongoDB
- **Standalone MongoDB instance** for storing control plane metadata
- **Connection String**: `mongodb://user:pass@host:port/admin`
- **Database**: `mdb_control_plane` (auto-created)
- **Collections**: `tenants`, `deployments`, `db_users` (auto-created)

#### 5. VM/Server for Control Plane Services
- **OS**: Ubuntu 22.04 LTS (recommended)
- **Resources**:
  - CPU: 2 cores
  - Memory: 4 GB RAM
  - Storage: 20 GB
- **Software**:
  - Python 3.12+
  - Node.js 18+ and npm
  - kubectl configured
  - AWS CLI (for S3 backups)

#### 6. AWS/S3 for Backups (Optional)
- **S3 Bucket**: Pre-created bucket for Community backups
- **IAM Permissions**: PutObject, GetObject, ListBucket, DeleteObject
- **Access**:
  - **EKS**: IRSA (IAM Roles for Service Accounts)
  - **Non-EKS**: AWS Access Key + Secret Key

#### 7. NFS/EFS for Filesystem Backups (Optional)
- **NFS Server** or **AWS EFS** accessible from Kubernetes cluster
- **Network**: Security groups allow NFS traffic (port 2049)
- **Permissions**: Write access to backup path

---

## Installation & Setup

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd mdb-ops-ansible
```

### Step 2: Backend Setup

#### 2.1 Install Dependencies

```bash
cd AtlasForge
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 2.2 Configure Environment Variables

Create `.env` file or export variables:

```bash
# Required: Control Plane MongoDB
export MCP_MONGODB_URI="mongodb://username:password@host:port/?authSource=admin"
export MCP_DB_NAME="mdb_control_plane"

# Required: Kubernetes Access
export MCP_KUBECONFIG_PATH="/home/ubuntu/.kube/config"
export MCP_NAMESPACE_PREFIX="mdb-"

# Required: Ops Manager (for Enterprise deployments)
export MCP_OPS_MANAGER_URL="http://ops-manager-host:8080"
export MCP_OPS_MANAGER_ORG="your-org-id"
export MCP_OM_GLOBAL_PUBLIC_KEY="your-public-key"
export MCP_OM_GLOBAL_PRIVATE_KEY="your-private-key"

# Optional: Logging
export MCP_LOG_LEVEL="INFO"
export MCP_SERVICE_PORT="8001"

# Optional: Community Backup - S3 Configuration
export COMMUNITY_BACKUP_S3_BUCKET="your-backup-bucket"
export COMMUNITY_BACKUP_S3_PREFIX="community-mongodb-backup"
export COMMUNITY_BACKUP_S3_REGION="us-east-1"
export COMMUNITY_BACKUP_SCHEDULE="0 */4 * * *"
export COMMUNITY_BACKUP_RETENTION_DAYS="7"

# Optional: AWS Credentials (for non-EKS environments)
export AWS_ACCESS_KEY_ID="YOUR_AWS_ACCESS_KEY"
export AWS_SECRET_ACCESS_KEY="YOUR_AWS_SECRET_KEY"
export AWS_DEFAULT_REGION="us-east-1"

# Optional: Community Backup - IRSA (for EKS)
export COMMUNITY_BACKUP_IRSA_ROLE_ARN="arn:aws:iam::ACCOUNT:role/backup-role"

# Optional: Resource Limits
export COMMUNITY_BACKUP_CPU_REQUEST="200m"
export COMMUNITY_BACKUP_MEMORY_REQUEST="256Mi"
export COMMUNITY_BACKUP_CPU_LIMIT="1"
export COMMUNITY_BACKUP_MEMORY_LIMIT="1Gi"
```

#### 2.3 Start Backend

```bash
cd AtlasForge
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Backend will be available at: `http://localhost:8001`

**API Documentation**: `http://localhost:8001/docs`

### Step 3: Frontend Setup

#### 3.1 Install Dependencies

```bash
cd AtlasForge-UI-Vite
npm install
```

#### 3.2 Configure API Endpoint

Edit `.env` file:

```bash
VITE_API_BASE_URL=http://localhost:8001
```

For production, set to your backend URL:

```bash
VITE_API_BASE_URL=https://api.your-domain.com
```

#### 3.3 Start Frontend

```bash
npm run dev
```

UI will be available at: `http://localhost:5173`

### Step 4: Verify Installation

1. **Access UI**: Open `http://localhost:5173`
2. **Create Tenant**: Click "Create Tenant" and create a test tenant
3. **Create Deployment**: Create a Community or Enterprise MongoDB deployment
4. **Check Kubernetes**:
   ```bash
   kubectl get namespaces | grep mdb-
   kubectl get mongodbcommunity -A
   kubectl get mongodb -A
   ```

---

## Features

### Tenant & Deployment Management

#### Creating Tenants

**Tenant** = Customer/Project isolation boundary

- Each tenant gets a dedicated Kubernetes namespace (`mdb-{tenantId}`)
- Supports **Enterprise** or **Community** plan selection
- Network policies and RBAC automatically configured

**Via UI:**
1. Go to "Tenants" page
2. Click "Create Tenant"
3. Enter:
   - Tenant ID (e.g., `acme-corp`)
   - Display Name (e.g., `ACME Corporation`)
   - Plan: `enterprise` or `community`
4. Click "Create"

**Via API:**
```bash
curl -X POST http://localhost:8001/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "tenantId": "acme-corp",
    "displayName": "ACME Corporation",
    "plan": "enterprise"
  }'
```

#### Creating Deployments

**Deployment** = MongoDB cluster (ReplicaSet or Sharded Cluster)

**Enterprise Deployment** (Ops Manager-backed):
- Managed via Ops Manager
- Automated backups via Ops Manager Backup Daemon
- Monitoring via Ops Manager agents
- Point-in-time recovery

**Community Deployment** (Standalone operator):
- Managed via MongoDB Community Operator
- Manual backups via CronJob (S3/Filesystem)
- Prometheus monitoring
- Snapshot-based recovery

**Via UI:**
1. Go to tenant details page
2. Click "Create Deployment"
3. Enter:
   - Deployment ID (e.g., `users-db`)
   - Type: `ReplicaSet` or `ShardedCluster`
   - Version (e.g., `8.0.3`, `7.0.15`)
   - Members: 3, 5, 7
   - Environment: `dev`, `test`, `prod`
4. Click "Create Deployment"

**Via API:**
```bash
curl -X POST http://localhost:8001/tenants/acme-corp/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentId": "users-db",
    "type": "ReplicaSet",
    "version": "8.0.3",
    "members": 3,
    "environment": "prod"
  }'
```

#### Lifecycle Operations

- **Scale**: Change replica count (3 → 5 members)
- **Upgrade**: Change MongoDB version (7.0.15 → 8.0.3)
- **Delete**: Remove deployment and all associated resources
- **Connection Info**: Get internal/external connection strings

---

### DB User Management

Self-service database user creation with role-based access control.

#### Supported Roles

**Database-Level Roles:**
- `read`: Read data from database
- `readWrite`: Read and write data
- `dbAdmin`: Database administration
- `userAdmin`: Manage users and roles
- `dbOwner`: Full database privileges

**Admin Roles (admin database only):**
- `readAnyDatabase`: Read all databases
- `readWriteAnyDatabase`: Read/write all databases
- `userAdminAnyDatabase`: Manage users across databases
- `dbAdminAnyDatabase`: Admin operations on all databases
- `clusterAdmin`: Full cluster administration
- `clusterMonitor`: Read cluster monitoring data
- `backup`: Backup and restore operations
- `restore`: Restore operations only
- `root`: Full superuser access

#### Creating Users

**Via UI:**
1. Go to deployment details → "DB Users" tab
2. Click "Create User"
3. Enter:
   - Username (e.g., `appuser`)
   - Database (e.g., `appdb`)
   - Roles: Select from dropdowns
4. Click "Create User"
5. **Copy password** (shown only once!)

**Via API:**
```bash
curl -X POST http://localhost:8001/tenants/acme-corp/deployments/users-db/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "appuser",
    "db": "appdb",
    "roles": [
      {"db": "appdb", "name": "readWrite"},
      {"db": "admin", "name": "clusterMonitor"}
    ]
  }'
```

**Response includes:**
- Auto-generated secure password
- Internal connection URI
- External connection URI (NodePort)
- mongosh connection command

#### Implementation Details

**Enterprise Plan:**
- Uses MongoDB Enterprise Operator's `MongoDBUser` CRD
- User synced to Ops Manager
- Centralized user management

**Community Plan:**
- Direct user creation via `kubectl exec mongosh`
- Requires admin credentials (auto-discovered from secrets)
- User stored in MongoDB's `admin.system.users`

---

### Backup Management

#### Enterprise Plan Backup (Ops Manager)

**Read-Only Backup UI:**
- View backup status
- List snapshots
- Restore from snapshot (triggers Ops Manager restore job)

**Note**: Backup configuration is managed in Ops Manager, not via control plane.

**Features:**
- Continuous backups
- Point-in-time recovery
- Queryable snapshots
- Automated retention

#### Community Plan Backup

**Two Backup Targets:**

##### 1. S3 Backup

Automated backups uploaded to Amazon S3 or S3-compatible storage.

**How it Works:**
1. Kubernetes CronJob runs `mongodump` on schedule
2. Creates compressed `.tar.gz` archive
3. Uploads to S3 bucket via AWS CLI
4. Cleans up backups older than retention period

**Configuration:**
- S3 Bucket Name
- S3 Prefix/Folder Path
- S3 Region
- Cron Schedule (e.g., `0 */4 * * *` = every 4 hours)
- Retention Days (default: 7)

**Requirements:**
- S3 bucket already exists
- IAM permissions: `s3:PutObject`, `s3:ListBucket`, `s3:DeleteObject`
- **EKS**: IRSA annotation on ServiceAccount
- **Non-EKS**: AWS credentials via environment variables

**Enable via UI:**
1. Go to deployment → "Backup" tab
2. Click "Enable Backup"
3. Select "S3"
4. Enter S3 bucket, prefix, region
5. Set schedule and retention
6. Click "Enable Backup"

**Snapshots:**
- Listed in UI with filename, timestamp, size
- Pagination for >10 snapshots
- Restore button (greyed out, coming soon)

**S3 Path Structure:**
```
s3://bucket-name/
  community-mongodb-backup/
    snapshots/
      dump-20260213-114500.tar.gz
      dump-20260213-150000.tar.gz
      ...
```

##### 2. Filesystem Backup

Backups written directly to NFS/EFS storage.

**How it Works:**
1. Kubernetes CronJob runs `mongodump` on schedule
2. Writes compressed `.gz` archive to mounted filesystem
3. Cleans up backups older than retention period

**Configuration:**
- Backup Host (NFS/EFS IP or DNS)
- Backup Path (e.g., `/mnt/backups`)
- Subdirectory (optional, default: deployment ID)
- Cron Schedule
- Retention Days

**Requirements:**
- NFS/EFS server accessible from K8s cluster
- Security groups allow NFS traffic (port 2049)
- Write permissions to backup path
- Network connectivity validated before enabling

**Enable via UI:**
1. Go to deployment → "Backup" tab
2. Click "Enable Backup"
3. Select "Filesystem (NFS/EFS)"
4. Enter host, path, subdirectory
5. Set schedule and retention
6. Click "Enable Backup"

**Validation:**
- Control plane creates test pod to verify write access
- If validation fails, clear error message shown

**Filesystem Path Structure:**
```
/mnt/backups/
  deployment-id/
    dump-20260213-114500.gz
    dump-20260213-150000.gz
    ...
```

#### Manual Backup Trigger

```bash
# For S3 backup
kubectl create job --from=cronjob/deployment-id-backup manual-backup -n mdb-tenant

# For Filesystem backup
kubectl create job --from=cronjob/deployment-id-backup-fs manual-backup -n mdb-tenant
```

#### Restore Process

**S3 Backup:**
```bash
# Download backup
aws s3 cp s3://bucket/prefix/snapshots/dump-20260213-114500.tar.gz ./

# Extract
tar -xzf dump-20260213-114500.tar.gz

# Restore
mongorestore --uri="mongodb://user:pass@host:port/db" ./dump-20260213-114500/
```

**Filesystem Backup:**
```bash
# Access NFS mount
# Copy dump file locally
scp user@nfs-host:/mnt/backups/deployment/dump-20260213-114500.gz ./

# Restore
mongorestore --uri="mongodb://user:pass@host:port/db" --archive=./dump-20260213-114500.gz --gzip
```

---

### Monitoring Integration

Prometheus-ready monitoring with auto-generated scrape configurations.

#### Features

- **Toggle Monitoring**: Enable/disable Prometheus monitoring per deployment
- **Auto-Discovery**: Scrape config includes all MongoDB pod IPs
- **Password Management**:
  - One-time password reveal
  - Password rotation
- **Copy-to-Clipboard**: Ready-to-use YAML config

#### Enable Monitoring

**Via UI:**
1. Go to deployment → "Monitoring" tab
2. Toggle "Enable Prometheus Monitoring"
3. Click "Reveal Password" (one-time view)
4. Click "Copy Scrape Config"
5. Add to your `prometheus.yml`

**Scrape Config Format:**
```yaml
scrape_configs:
  - job_name: 'mongodb-deployment-id'
    static_configs:
      - targets:
        - '10.244.1.10:9216'
        - '10.244.2.15:9216'
        - '10.244.3.20:9216'
    basic_auth:
      username: 'prometheus'
      password: 'REVEALED_PASSWORD'
```

#### Password Rotation

1. Click "Rotate Password" in UI
2. New password generated
3. Update Prometheus config with new password
4. Restart Prometheus

---

## Enterprise vs Community Deployments

### Comparison Matrix

| Feature | Enterprise Plan | Community Plan |
|---------|----------------|----------------|
| **MongoDB Operator** | MongoDB Enterprise Operator | MongoDB Community Operator |
| **Ops Manager** | Required | Not used |
| **Licensing** | MongoDB Enterprise license required | Free, SSPL license |
| **Deployment Types** | ReplicaSet, ShardedCluster | ReplicaSet only |
| **Backup** | Ops Manager continuous backup | CronJob-based (S3/Filesystem) |
| **Point-in-Time Recovery** | ✅ Yes | ❌ No (snapshot-based only) |
| **Monitoring** | Ops Manager + Prometheus | Prometheus only |
| **LDAP/Kerberos** | ✅ Yes | ❌ No |
| **Encryption at Rest** | ✅ Yes | ❌ No |
| **Auditing** | ✅ Yes | ❌ No |
| **DB User Management** | MongoDBUser CRD + Ops Manager | Direct mongosh exec |
| **Use Case** | Production, regulated industries | Development, testing, non-critical |

### When to Use Enterprise

- **Regulated Industries**: Finance, healthcare, government
- **Compliance Requirements**: SOC2, HIPAA, PCI-DSS
- **Mission-Critical Workloads**: 24/7 uptime SLAs
- **Advanced Security**: LDAP, Kerberos, field-level encryption
- **Large-Scale**: Sharded clusters, 50+ nodes

### When to Use Community

- **Development/Testing**: Non-production environments
- **Startups/SMBs**: Cost-sensitive workloads
- **Proof of Concept**: Quick MongoDB deployments
- **Freemium Tier**: Offer free Community, upsell to Enterprise
- **Internal Tools**: Non-customer-facing databases

---

## Configuration Reference

### Environment Variables

<table>
<tr><th>Variable</th><th>Required</th><th>Default</th><th>Description</th></tr>
<tr><td colspan="4"><strong>Control Plane MongoDB</strong></td></tr>
<tr>
  <td><code>MCP_MONGODB_URI</code></td>
  <td>✅ Yes</td>
  <td>-</td>
  <td>MongoDB connection string for control plane metadata</td>
</tr>
<tr>
  <td><code>MCP_DB_NAME</code></td>
  <td>No</td>
  <td><code>mdb_control_plane</code></td>
  <td>Database name for control plane</td>
</tr>

<tr><td colspan="4"><strong>Kubernetes Access</strong></td></tr>
<tr>
  <td><code>MCP_KUBECONFIG_PATH</code></td>
  <td>✅ Yes</td>
  <td><code>/home/ubuntu/.kube/config</code></td>
  <td>Path to kubeconfig file</td>
</tr>
<tr>
  <td><code>MCP_NAMESPACE_PREFIX</code></td>
  <td>No</td>
  <td><code>mdb-</code></td>
  <td>Namespace prefix for tenants</td>
</tr>

<tr><td colspan="4"><strong>Ops Manager (Enterprise)</strong></td></tr>
<tr>
  <td><code>MCP_OPS_MANAGER_URL</code></td>
  <td>✅ Yes*</td>
  <td>-</td>
  <td>Ops Manager base URL</td>
</tr>
<tr>
  <td><code>MCP_OPS_MANAGER_ORG</code></td>
  <td>✅ Yes*</td>
  <td>-</td>
  <td>Ops Manager Organization ID</td>
</tr>
<tr>
  <td><code>MCP_OM_GLOBAL_PUBLIC_KEY</code></td>
  <td>✅ Yes*</td>
  <td>-</td>
  <td>Ops Manager API public key</td>
</tr>
<tr>
  <td><code>MCP_OM_GLOBAL_PRIVATE_KEY</code></td>
  <td>✅ Yes*</td>
  <td>-</td>
  <td>Ops Manager API private key</td>
</tr>

<tr><td colspan="4"><strong>Community Backup - S3</strong></td></tr>
<tr>
  <td><code>COMMUNITY_BACKUP_S3_BUCKET</code></td>
  <td>No</td>
  <td><code>mdbaas-community-mongodb-backups</code></td>
  <td>S3 bucket for backups</td>
</tr>
<tr>
  <td><code>COMMUNITY_BACKUP_S3_PREFIX</code></td>
  <td>No</td>
  <td><code>community-mongodb-backup</code></td>
  <td>S3 prefix/folder path</td>
</tr>
<tr>
  <td><code>COMMUNITY_BACKUP_S3_REGION</code></td>
  <td>No</td>
  <td><code>us-east-1</code></td>
  <td>S3 region</td>
</tr>
<tr>
  <td><code>COMMUNITY_BACKUP_SCHEDULE</code></td>
  <td>No</td>
  <td><code>0 */4 * * *</code></td>
  <td>Cron schedule for backups</td>
</tr>
<tr>
  <td><code>COMMUNITY_BACKUP_RETENTION_DAYS</code></td>
  <td>No</td>
  <td><code>7</code></td>
  <td>Backup retention period</td>
</tr>

<tr><td colspan="4"><strong>AWS Credentials (Non-EKS)</strong></td></tr>
<tr>
  <td><code>AWS_ACCESS_KEY_ID</code></td>
  <td>No</td>
  <td>-</td>
  <td>AWS access key for S3 backups</td>
</tr>
<tr>
  <td><code>AWS_SECRET_ACCESS_KEY</code></td>
  <td>No</td>
  <td>-</td>
  <td>AWS secret key for S3 backups</td>
</tr>
<tr>
  <td><code>AWS_DEFAULT_REGION</code></td>
  <td>No</td>
  <td><code>us-east-1</code></td>
  <td>Default AWS region</td>
</tr>

<tr><td colspan="4"><strong>Community Backup - IRSA (EKS)</strong></td></tr>
<tr>
  <td><code>COMMUNITY_BACKUP_IRSA_ROLE_ARN</code></td>
  <td>No</td>
  <td>-</td>
  <td>IAM role ARN for IRSA</td>
</tr>

<tr><td colspan="4"><strong>Logging</strong></td></tr>
<tr>
  <td><code>MCP_LOG_LEVEL</code></td>
  <td>No</td>
  <td><code>INFO</code></td>
  <td>Logging level (DEBUG, INFO, WARN, ERROR)</td>
</tr>
<tr>
  <td><code>MCP_SERVICE_PORT</code></td>
  <td>No</td>
  <td><code>8001</code></td>
  <td>FastAPI service port</td>
</tr>
</table>

*Required only for Enterprise plan deployments

---

## Troubleshooting

### Common Issues

#### 1. Backend Won't Start

**Error**: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**:
```bash
cd AtlasForge
source venv/bin/activate
pip install -r requirements.txt
```

#### 2. UI Can't Connect to Backend

**Error**: `Network Error` in browser console

**Solution**:
- Check backend is running: `curl http://localhost:8001/docs`
- Verify `VITE_API_BASE_URL` in `.env` matches backend URL
- Check CORS is enabled in FastAPI (already configured)

#### 3. Deployment Stuck in "Pending"

**Check Kubernetes**:
```bash
kubectl get mongodb <deployment-id> -n mdb-<tenant-id> -o yaml
kubectl describe mongodb <deployment-id> -n mdb-<tenant-id>
kubectl get events -n mdb-<tenant-id> --sort-by='.lastTimestamp'
```

**Common Causes**:
- Ops Manager unreachable
- Insufficient node resources
- Missing secrets (MongoDB Enterprise ConfigMap/Secret)

#### 4. Backup Job Fails

**Check Logs**:
```bash
kubectl logs job/<deployment>-backup-<timestamp> -n mdb-<tenant> -c mongodump
kubectl logs job/<deployment>-backup-<timestamp> -n mdb-<tenant> -c s3-upload
```

**Common Causes**:
- AWS credentials missing/invalid
- S3 bucket doesn't exist or no permissions
- MongoDB connection failed (check user credentials)
- NFS/EFS not reachable (filesystem backups)

#### 5. DB User Creation Fails (Community)

**Error**: `Authentication required`

**Solution**:
- Admin credentials auto-discovered from secret `<deployment>-admin-admin`
- Verify secret exists: `kubectl get secret -n mdb-<tenant> | grep admin`
- Check mongosh is available in pod:
  ```bash
  kubectl exec -it <pod> -n mdb-<tenant> -c mongod -- mongosh --version
  ```

---

## Support & Documentation

- **API Documentation**: `http://localhost:8001/docs` (FastAPI Swagger UI)
- **Architecture Diagrams**: See `ARCHITECTURE.md`
- **API Changes Log**: See `AtlasForge/API_CHANGES.md`
- **UI Guide**: See `AtlasForge-UI-Vite/README.md`

---

## License

[Add your license information here]

---

## Contributing

[Add contribution guidelines here]

---

**Built with ❤️ for MongoDB-as-a-Service providers worldwide**
