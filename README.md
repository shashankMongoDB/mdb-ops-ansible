# MongoDB Control Plane (MDBaaS)

Production-ready, self-service platform for managing MongoDB deployments on Kubernetes with automated backup, monitoring, and lifecycle management.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Kubernetes](https://img.shields.io/badge/kubernetes-1.23%2B-326CE5.svg)](https://kubernetes.io/)
[![MongoDB](https://img.shields.io/badge/mongodb-6.0%2B-47A248.svg)](https://www.mongodb.com/)

---

## 🚀 Quick Start

### Prerequisites

**You only need:**
- ✅ Kubernetes cluster (1.23+)
- ✅ kubectl access with admin permissions
- ✅ That's it!

Our deployment script installs everything else automatically.

---

### Installation (3 Steps)

#### **1. Clone Repository**

```bash
git clone https://github.com/your-org/mdb-ops-ansible.git
cd mdb-ops-ansible
```

---

#### **2. Configure Environment**

```bash
cp config/production.env.example config/production.env
vi config/production.env
```

**Minimum required configuration:**

```bash
# Kubernetes
KUBECONFIG_PATH="/home/ubuntu/.kube/config"

# Ops Manager (Enterprise) - Or skip for Community-only
OPS_MANAGER_URL="https://ops-manager.example.com:8080"
OPS_MANAGER_PUBLIC_KEY="your-public-key"
OPS_MANAGER_PRIVATE_KEY="your-private-key"

# AWS (for Community backups)
AWS_S3_BUCKET="mdbaas-backups"
AWS_ACCESS_KEY_ID="your-access-key"
AWS_SECRET_ACCESS_KEY="your-secret-key"
```

---

#### **3. Deploy in Phases**

```bash
# Phase 1: Install operators (3-5 min)
./scripts/deploy.sh --config config/production.env --phase operator

# Phase 2: Install backup infrastructure (2-3 min)
./scripts/deploy.sh --config config/production.env --phase appdb-backup

# Phase 3: Install monitoring (5-7 min) - Optional
./scripts/deploy.sh --config config/production.env --phase monitoring

# Phase 4: Install control plane (5-7 min)
./scripts/deploy.sh --config config/production.env --phase control-plane

# Verify installation (1 min)
./scripts/deploy.sh --config config/production.env --phase verify
```

**Total time: ~15-20 minutes**

---

### Access the UI

```bash
# Get UI URL
kubectl get svc mdbaas-frontend-svc -n mdbaas-system

# Example output:
# NAME                   TYPE           EXTERNAL-IP      PORT(S)
# mdbaas-frontend-svc    LoadBalancer   34.213.34.102    3000:30002/TCP

# Open browser:
# http://34.213.34.102:3000
```

---

## ✨ Features

### **Multi-Tenant Management**
- ✅ Enterprise and Community MongoDB support
- ✅ Isolated namespaces per tenant
- ✅ Plan-based feature access
- ✅ Self-service tenant creation

### **Deployment Types**
- ✅ Standalone
- ✅ ReplicaSet (3, 5, 7 members)
- ✅ Sharded Cluster (configurable shards)

### **Automated Backup**
- ✅ **Enterprise:** Ops Manager continuous backup
- ✅ **Community:** S3 + Filesystem snapshots
- ✅ Point-in-time restore
- ✅ Automated schedules (every 4 hours)
- ✅ Configurable retention (7 days default)

### **Monitoring**
- ✅ Prometheus metrics auto-enabled
- ✅ Grafana dashboards
- ✅ Per-deployment metrics
- ✅ Password reveal (one-time) + rotation

### **Lifecycle Management**
- ✅ Shutdown/Start/Restart
- ✅ Scale up/down (odd member counts)
- ✅ Version upgrades (no downgrades)
- ✅ Progressive status disclosure

### **DB User Management**
- ✅ Create users with custom roles
- ✅ Multi-database access
- ✅ Update roles dynamically
- ✅ Connection strings per user
- ✅ Delete users

### **External Connectivity**
- ✅ NodePort services auto-created
- ✅ Connection strings with worker IPs
- ✅ Multi-node support

---

## 📁 Project Structure

```
mdb-ops-ansible/
├── scripts/
│   └── deploy.sh                    # Automated deployment script
├── config/
│   └── production.env.example       # Configuration template
├── AtlasForge/                      # Control Plane backend
│   ├── app/
│   │   ├── main.py                  # FastAPI application
│   │   ├── services/                # Business logic
│   │   └── models/                  # Data models
│   └── MongoDB_Control_Plane.postman_collection.json
├── AtlasForge-UI/                   # Control Plane frontend
│   ├── pages/                       # React pages
│   ├── components/                  # UI components
│   └── lib/                         # API client
├── k8s/                             # Kubernetes manifests
│   ├── operators/                   # Operator deployments
│   ├── control-plane/               # Backend + Frontend
│   ├── monitoring/                  # Prometheus + Grafana
│   └── backup/                      # Backup CronJobs
└── docs/
    ├── DEPLOYMENT_GUIDE.md          # This guide
    ├── UI_GUIDE.md                  # User interface guide
    ├── API_DOCUMENTATION_AUDIT.md   # API reference
    └── ARCHITECTURE.md              # Architecture details
```

---

## 📚 Documentation

### **Deployment & Operations**
- **[Deployment Guide](DEPLOYMENT_GUIDE.md)** - Complete deployment instructions
- **[Configuration Reference](DEPLOYMENT_GUIDE.md#configuration-file-reference)** - All configuration options
- **[Troubleshooting](DEPLOYMENT_GUIDE.md#troubleshooting)** - Common issues and solutions

### **User Guides**
- **[UI Guide](AtlasForge-UI/UI_GUIDE.md)** - Step-by-step UI walkthrough
- **[Quick Start](AtlasForge-UI/QUICKSTART.md)** - Fast-track guide

### **API Documentation**
- **[API Audit](API_DOCUMENTATION_AUDIT.md)** - Complete API reference
- **[Postman Collection](AtlasForge/MongoDB_Control_Plane.postman_collection.json)** - Import and test
- **[Swagger UI](http://localhost:8001/docs)** - Interactive API docs

### **Architecture**
- **[Architecture Overview](ARCHITECTURE.md)** - System design
- **[File Structure](AtlasForge-UI/FILE_STRUCTURE.txt)** - Codebase organization

---

## 🎯 Use Cases

### **Multi-Tenant SaaS Platforms**
- Provide MongoDB-as-a-Service to customers
- Automated provisioning and billing
- Self-service portal
- Isolated tenant resources

### **Internal Developer Platform**
- Self-service MongoDB for development teams
- Automated backup and recovery
- Monitoring and alerting
- Cost tracking per team

### **Enterprise MongoDB Management**
- Centralized Ops Manager control
- Standardized deployment templates
- Compliance and audit trails
- Disaster recovery automation

### **Testing & Staging Environments**
- Rapid deployment for testing
- Clean environments on-demand
- Cost-effective Community edition
- Easy teardown

---

## 🔧 Deployment Phases Explained

### **Phase 1: Operators**
Installs MongoDB Enterprise and Community operators that manage MongoDB lifecycle on Kubernetes.

```bash
./scripts/deploy.sh --config config/production.env --phase operator
```

**What it does:**
- Creates `mongodb-operator` namespace
- Installs MongoDB Enterprise Operator
- Installs MongoDB Community Operator
- Installs Custom Resource Definitions (CRDs)
- Configures RBAC

---

### **Phase 2: Ops Manager** (Optional)
Installs or configures Ops Manager for Enterprise deployments.

```bash
./scripts/deploy.sh --config config/production.env --phase ops-manager
```

**What it does:**
- Deploys Ops Manager (if INSTALL_OPS_MANAGER=true)
- Configures SSL/TLS
- Creates initial organization
- Generates API keys

**Skip if:** Using existing Ops Manager or Community-only

---

### **Phase 3: Backup Infrastructure**
Sets up automated backup for Community deployments.

```bash
./scripts/deploy.sh --config config/production.env --phase appdb-backup
```

**What it does:**
- Creates/verifies S3 bucket
- Configures IAM roles (IRSA for EKS)
- Creates backup CronJob templates
- Configures retention policies

---

### **Phase 4: Monitoring** (Optional)
Installs Prometheus and Grafana for metrics visualization.

```bash
./scripts/deploy.sh --config config/production.env --phase monitoring
```

**What it does:**
- Deploys Prometheus
- Deploys Grafana
- Imports MongoDB dashboards
- Configures ServiceMonitors

---

### **Phase 5: Control Plane**
Installs the backend API and frontend UI.

```bash
./scripts/deploy.sh --config config/production.env --phase control-plane
```

**What it does:**
- Creates `mdbaas-system` namespace
- Deploys metadata MongoDB database
- Deploys FastAPI backend
- Deploys React frontend
- Creates LoadBalancer services
- Exposes UI and API

**After this phase:** System is ready to use! 🎉

---

## 🌟 Key Capabilities

### **Progressive Status Disclosure**
- Access deployments as soon as 1 replica is ready (PRIMARY available)
- Real-time replica status with progress indicators
- Disabled operations until fully ready

### **Smart Version Management**
- Dropdown with MongoDB versions from `mongodb_versions.json`
- Grouped by major version (8.0, 7.0, etc.)
- Labels for Latest and LTS versions
- Prevents downgrades

### **One-Time Password Reveal**
- Prometheus password can be revealed once
- After reveal, only masked version shown
- Password rotation available anytime
- Security-first design

### **Multi-Plan Support**
- **Enterprise:** Ops Manager integration, continuous backup, advanced monitoring
- **Community:** S3/Filesystem backup, basic monitoring, cost-effective

### **Terminology Alignment**
- "Replicas" instead of "Pods" (MongoDB-native terminology)
- "Deployment" for MongoDB instances
- "Tenant" for isolated environments

---

## 📊 API Endpoints

### **Tenant Management**
```
POST   /tenants                      Create tenant
GET    /tenants                      List tenants
GET    /tenants/{id}                 Get tenant details
DELETE /tenants/{id}                 Delete tenant
```

### **Deployment Management**
```
POST   /tenants/{tid}/deployments              Create deployment
GET    /tenants/{tid}/deployments              List deployments
GET    /tenants/{tid}/deployments/{id}         Get deployment
DELETE /tenants/{tid}/deployments/{id}         Delete deployment
GET    /tenants/{tid}/deployments/{id}/connection-info
```

### **Lifecycle Operations**
```
POST /tenants/{tid}/deployments/{id}/shutdown   Shutdown
POST /tenants/{tid}/deployments/{id}/start      Start
POST /tenants/{tid}/deployments/{id}/restart    Restart
PATCH /tenants/{tid}/deployments/{id}/scale     Scale
PATCH /tenants/{tid}/deployments/{id}/version   Upgrade
```

### **Backup Operations**
```
# Enterprise
PATCH /tenants/{tid}/deployments/{id}/backup           Enable/disable
GET   /tenants/{tid}/deployments/{id}/backup/status
GET   /tenants/{tid}/deployments/{id}/backup/policies
PATCH /tenants/{tid}/deployments/{id}/backup/policy
POST  /tenants/{tid}/deployments/{id}/backup/snapshot
GET   /tenants/{tid}/deployments/{id}/backup/snapshots
POST  /tenants/{tid}/deployments/{id}/backup/restore

# Community
PATCH /tenants/{tid}/deployments/{id}/community-backup          Enable/disable
GET   /tenants/{tid}/deployments/{id}/community-backup/status
POST  /tenants/{tid}/deployments/{id}/community-backup/restore
GET   /tenants/{tid}/deployments/{id}/community-backup/restore-status
```

### **Monitoring**
```
PATCH /tenants/{tid}/deployments/{id}/monitoring              Enable/disable
GET   /tenants/{tid}/deployments/{id}/prometheus/config
GET   /tenants/{tid}/deployments/{id}/prometheus/scrape-config
POST  /tenants/{tid}/deployments/{id}/prometheus/reveal-password
POST  /tenants/{tid}/deployments/{id}/prometheus/rotate-password
```

### **DB User Management**
```
POST   /tenants/{tid}/deployments/{id}/db-users                    Create user
GET    /tenants/{tid}/deployments/{id}/db-users                    List users
GET    /tenants/{tid}/deployments/{id}/db-users/{user}/connection  Get connection
PATCH  /tenants/{tid}/deployments/{id}/db-users/{user}             Update roles
DELETE /tenants/{tid}/deployments/{id}/db-users/{user}             Delete user
```

**Full API documentation:** http://localhost:8001/docs

---

## 🛠️ Production Deployment

### **Prerequisites Checklist**

- [ ] Kubernetes cluster with 3+ worker nodes
- [ ] Storage class configured (gp3, ebs-csi, etc.)
- [ ] LoadBalancer support (or Ingress controller)
- [ ] S3 bucket for backups
- [ ] Ops Manager deployed (for Enterprise)
- [ ] SSL certificates (optional)

### **Recommended Configuration**

```bash
# Multi-node cluster
NODE_COUNT=3
NODE_TYPE="t3.xlarge"  # 4 CPU, 16GB RAM

# Storage
STORAGE_CLASS="gp3"
STORAGE_SIZE="100Gi"

# Backup
BACKUP_RETENTION_DAYS="30"
BACKUP_SCHEDULE="0 2 * * *"  # Daily at 2 AM

# Monitoring
PROMETHEUS_RETENTION="30d"
PROMETHEUS_STORAGE="200Gi"
```

### **Security Best Practices**

✅ Enable Pod Security Standards  
✅ Use Network Policies for tenant isolation  
✅ Configure SSL/TLS for Ops Manager  
✅ Use IRSA for AWS access (EKS)  
✅ Rotate credentials regularly  
✅ Enable audit logging  
✅ Restrict API access with authentication  

---

## 🔍 Monitoring & Observability

### **Metrics Available**
- MongoDB connections
- Query operations (read/write)
- Replication lag
- Disk usage
- CPU and memory utilization
- Backup status
- API request latency

### **Access Grafana**

```bash
kubectl get svc grafana -n monitoring

# Open http://<EXTERNAL-IP>:3000
# Login: admin / <GRAFANA_ADMIN_PASSWORD>
```

### **Pre-configured Dashboards**
- MongoDB Cluster Overview
- Ops Manager Metrics
- Control Plane API Performance
- Tenant Resource Usage

---

## 🆘 Support & Troubleshooting

### **Common Issues**

#### **Operators not starting**
```bash
kubectl logs -n mongodb-operator deployment/mongodb-enterprise-operator
kubectl get crd | grep mongodb
```

#### **Backend cannot connect to metadata DB**
```bash
kubectl logs -n mdbaas-system deployment/mdbaas-backend
kubectl exec -it deployment/mdbaas-backend -n mdbaas-system -- \
  python3 -c "from app.services.mongo_repo import get_repo; print(get_repo().list_tenants())"
```

#### **UI not loading**
```bash
kubectl logs -n mdbaas-system deployment/mdbaas-frontend
kubectl get svc -n mdbaas-system
```

### **Get Help**
- 📖 [Troubleshooting Guide](DEPLOYMENT_GUIDE.md#troubleshooting)
- 🐛 [Open GitHub Issue](https://github.com/your-org/mdb-ops-ansible/issues)
- 📧 Email: support@example.com

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details

---

## 🙏 Acknowledgments

Built with:
- [MongoDB Enterprise Kubernetes Operator](https://docs.mongodb.com/kubernetes-operator/)
- [MongoDB Community Kubernetes Operator](https://github.com/mongodb/mongodb-kubernetes-operator)
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [Prometheus](https://prometheus.io/)
- [Grafana](https://grafana.com/)

---

## 🚀 Getting Started Now

```bash
# 1. Clone
git clone https://github.com/your-org/mdb-ops-ansible.git
cd mdb-ops-ansible

# 2. Configure
cp config/production.env.example config/production.env
vi config/production.env

# 3. Deploy
./scripts/deploy.sh --config config/production.env --phase operator
./scripts/deploy.sh --config config/production.env --phase control-plane

# 4. Access UI
kubectl get svc mdbaas-frontend-svc -n mdbaas-system
# Open http://<EXTERNAL-IP>:3000 in browser

# 5. Create your first MongoDB deployment! 🎉
```

---

**Questions? Issues? Suggestions?**

Open an issue on GitHub or check our comprehensive documentation!

Happy deploying! 🚀
