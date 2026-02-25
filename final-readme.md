# MongoDB MDBaaS Control Plane

## 1) Project Overview

This project is a production-oriented **MongoDB MDBaaS control plane** that lets end customer provision and operate MongoDB on Kubernetes through a single UI and API layer.

It supports two operating models:

- **Enterprise Advanced (EA)**: MCK (MongoDB Controllers for Kubernetes Operator) + Ops Manager integration
- **Community Edition**: MCK (`MongoDBCommunity` CRDs), without Ops Manager

### What problem it solves

- Standardizes MongoDB provisioning for multiple teams/tenants
- Eliminates manual CR creation, backup wiring, and lifecycle operations
- Unifies Day-2 operations (scale, restart, version upgrade, monitoring, backup/restore)
- Provides tenant-level isolation and auditable metadata state

### Business value

- Faster database onboarding and lower platform toil
- Consistent, policy-driven operations across environments
- Reduced operational risk via automated reconciliation and state tracking
- Clear EA vs Community path while keeping one control plane UX

---

## 2) High-Level Architecture (who talks to whom)

```text
┌───────────────────────────┐        HTTPS         ┌─────────────────────────────┐
│  Control Plane UI (Vite)  │ ───────────────────▶ │ FastAPI Backend (backend)   │
└───────────────────────────┘                      └──────────────┬──────────────┘
                                                                  │
                                               ┌──────────────────┴──────────────────┐
                                               │                                     │
                                  MongoDB (metadata DB)                 Kubernetes API Server
                               (tenants/deployments/users state)          (CRDs, Services, Jobs)
                                               │                                     │
                                               │                          ┌──────────┴──────────┐
                                               │                          │                     │
                                               │                Enterprise path         Community path
                                               │                mongodb.com/v1 CRs      mongodbcommunity CRs
                                               │                          │                     │
                                               │                  Enterprise Operator    Community Operator
                                               │                          │                     │
                                               │                     StatefulSets + Pods + PVCs
                                               │
                                               └───────────── Ops Manager API (EA backup/monitoring)
```

---

## 3) Detailed Components

## Frontend 

- React + TypeScript + Vite SPA
- Primary routes:
  - `/` tenants
  - `/tenants/:tenantId`
  - `/tenants/:tenantId/deployments/:deploymentId`
- Calls backend APIs for:
  - tenant/deployment CRUD
  - lifecycle ops (start/shutdown/restart)
  - scale/version upgrade
  - monitoring/prometheus config
  - backup/restore (EA and Community flows)

## Backend 

- Orchestrates all platform operations
- Main services:
  - `tenants_service` (onboarding, namespace + RBAC/bootstrap)
  - `deployments_service` (EA + Community routing)
  - `deployments_community_service` (MongoDBCommunity CR path)
  - `lifecycle_service`, `scaling_service`, `deployment_status_service`
  - `monitoring_service` (Prometheus wiring)
  - `backup_service` (EA Ops Manager backup APIs)
  - `community_backup_service` (community backup/restore jobs)
- Persists source-of-record metadata in control plane MongoDB

## MCK (MongoDB Controllers for Kubernetes Operator)

- Backend **does not create StatefulSets directly** for MongoDB clusters.
- Backend creates/patches CRDs; operators reconcile and create runtime resources.

### Enterprise path

- CRD group: `mongodb.com/v1` (`MongoDB`)
- Operator consumes Ops Manager config/credentials configmaps+secrets
- Operator creates/updates StatefulSets, Services, PVC-backed pods
- Automation/agent behavior is driven by Operator + Ops Manager integration

### Community path

- CRD group: `mongodbcommunity.mongodb.com/v1` (`MongoDBCommunity`)
- Community CR includes auth mode, users, members, version, config
- Operator creates StatefulSet/pods/PVCs and reconciles scale/version changes

## Ops Manager (EA only)

- Backend uses API clients for:
  - project lookup (read-only discovery)
  - backup config/policy/snapshot/restore job operations
- Project IDs are lazily discovered and cached in metadata DB

## Metadata DB

- Stores:
  - tenant docs (`tenants`)
  - deployment docs (`deployments`)
  - db user metadata (`db_users`)
- Captures requested spec, status fields, operational metadata (backup/restore/progress)
- Used for UI state, orchestration continuity, and reconciliation hints

## StatefulSets and data plane

- Created by Operators from CRDs
- MongoDB data durability via PVCs
- Control plane may create additional K8s resources around the data plane:
  - NodePort services (external primary/secondary access)
  - Metrics service
  - Backup CronJobs / Restore Jobs (community)

---

## 4) Deployment Flow (EA vs Community branching)

## Tenant onboarding

```text
POST /tenants
  └─ validate tenantId + plan
  └─ ensure namespace exists
  └─ if EA:
       ensure OM project configmap + credentials secret + combined CA + SA
     if Community:
       ensure SA + Role + RoleBinding for community operator
  └─ ensure mongodb-admin-secret
  └─ persist tenant metadata
```

## Deployment create flow

```text
POST /tenants/{tenantId}/deployments
  └─ load tenant plan
  └─ if Community:
       create MongoDBCommunity CR (ReplicaSet path)
       persist deployment doc
     else EA:
       create MongoDB CR (Standalone/ReplicaSet/ShardedCluster)
       persist deployment doc
       auto-enable Prometheus integration
```

## Where StatefulSets are created

```text
Backend creates CR  ──▶  Kubernetes API stores CR  ──▶  Operator reconcile loop
                                                     └─▶ creates StatefulSet + Pods + PVCs + Services
```

## Existing component validation / skip behavior

- Uses idempotent `ensure_*` patterns for namespace/configmaps/secrets/SA/RBAC/services
- Checks for existing tenant/deployment documents before insert
- Checks for existing CRs before create
- If resources already exist, operation skips creation or returns clear conflict

---

## 5) EA vs Community Comparison

| Capability | Enterprise Advanced (EA) | Community Edition |
|---|---|---|
| CRD/API group | `mongodb.com/v1` (`MongoDB`) | `mongodbcommunity.mongodb.com/v1` (`MongoDBCommunity`) |
| Control dependency | Operator + Ops Manager | Community Operator only |
| Topologies | Standalone, ReplicaSet, ShardedCluster | ReplicaSet (current implementation path) |
| Backup system | Ops Manager backup APIs/policies/snapshots | CronJob + S3/filesystem snapshots + restore Jobs |
| Restore model | Ops Manager restore jobs | K8s restore job (`mongorestore`) |
| Monitoring | Prometheus wiring via CR + metrics service | Same pattern via community CR |
| Project/org context | Ops Manager org/project lookup and caching | Not required |
| Operational complexity | Higher (OM integration) | Lower (K8s-native path) |

---

## 6) Multi-tenancy Model (Namespace Isolation)

- Each tenant is mapped to namespace: `MCP_NAMESPACE_PREFIX + tenantId` (default `mdb-<tenantId>`)
- Namespace labels include tenant and plan identifiers
- Tenant resources (CRs, secrets, services, jobs) are isolated per namespace
- Metadata documents are keyed with tenant-scoped IDs (e.g., `tenant:deployment`)
- Community path explicitly creates namespace-local RBAC for operator-required access

```text
Tenant A -> namespace mdb-tenant-a -> CRs/Pods/Secrets/Jobs for A only
Tenant B -> namespace mdb-tenant-b -> CRs/Pods/Secrets/Jobs for B only
```

---

## 7) Security & Scalability Considerations

## Security

- Secret-backed credentials for MongoDB admin, Ops Manager keys, backup access
- Optional TLS verification controls for Ops Manager and S3-compatible endpoints
- Namespace-level isolation + RBAC boundaries
- Password masking/reveal controls in monitoring endpoints
- Production recommendation: remove default hardcoded secrets/env fallbacks and use vault/secret manager
- Restrict CORS origins in production (currently permissive)

## Scalability

- Operator-based reconciliation scales cluster lifecycle management better than imperative pod control
- StatefulSet + PVC model supports predictable scaling for replica sets/sharded components
- API/backend remains stateless; metadata DB is persistence anchor
- Background polling/state monitors support long-running operations (upgrade/scale/restore)
- NodePort exposure can be replaced by ingress/LB patterns for large-scale multi-cluster deployments

## Operational reliability

- Control plane tracks requested vs observed state and supports sync actions
- Community restore/backup workflows include job status tracking and terminal-state history
- Idempotent resource creation reduces failed re-runs during retries/partial setup

---

## End-to-End Runtime Interaction Diagram

```text
[User]
  │
  ▼
[UI: Tenants/Deployment pages]
  │ REST
  ▼
[FastAPI Control Plane]
  ├─ Read/write metadata ───────────────▶ [Metadata MongoDB]
  ├─ Create/Patch CRs/Services/Jobs ────▶ [Kubernetes API]
  │                                        │
  │                                        ├─ Enterprise Operator ─▶ MongoDB StatefulSets/Pods/PVCs
  │                                        │                          + Ops/automation agent behavior
  │                                        └─ Community Operator ───▶ MongoDB StatefulSet/Pods/PVCs
  │
  └─ EA backup/restore/policy APIs ──────▶ [Ops Manager]

Result status/connection/progress
  ▲
  └────────────────────────────────────── [UI polls backend endpoints]
```

---

