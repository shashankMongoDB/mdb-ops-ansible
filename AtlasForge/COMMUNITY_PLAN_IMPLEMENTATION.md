# Community Plan Implementation Summary

## Overview

Extended the FastAPI control-plane microservice to support **two deployment flavors**:
- **"enterprise"** → uses Ops Manager + `MongoDB` CR (group `mongodb.com`)
- **"community"** → uses `MongoDBCommunity` CR (group `mongodbcommunity.mongodb.com`), NO Ops Manager

## Key Principles

1. ✅ **Separation of Concerns**: Enterprise and community logic are in separate service modules
2. ✅ **Backward Compatibility**: Existing enterprise behavior works as-is (default plan)
3. ✅ **Clean Routing**: Main services route based on tenant `plan` field
4. ✅ **No Mixing**: Each deployment belongs to one plan only

---

## 1. Changes to Tenant Model

### DTO Updates (`app/models/dto.py`)

```python
from typing import Literal

class TenantCreateRequest(BaseModel):
    tenantId: str
    displayName: str
    plan: Literal["enterprise", "community"] = "enterprise"  # NEW

class TenantCreateResponse(BaseModel):
    tenantId: str
    namespace: str
    projectName: Optional[str] = None  # None for community
    status: str
    plan: str  # NEW
```

### Service Updates (`app/services/tenants_service.py`)

**`onboard_tenant()` function**:
- Validates `plan` parameter (must be "enterprise" or "community")
- Stores `plan` in tenant MongoDB document
- Only creates Ops Manager resources (ConfigMap, Secret) for `plan == "enterprise"`
- Creates admin password secret for both plans
- Creates ServiceAccount for both plans

**`delete_tenant()` function**:
- Routes CR deletion based on tenant plan
- Enterprise: deletes `MongoDB` CRs (mongodb.com)
- Community: deletes `MongoDBCommunity` CRs (mongodbcommunity.mongodb.com)

---

## 2. New Service Modules

### Enterprise Service (`app/services/deployments_enterprise_service.py`)

Thin wrapper that delegates to existing `deployments_service.py` for backward compatibility.

**Key function**:
```python
def create_deployment_enterprise(...)
    # Delegates to existing create_deployment() 
    # which already handles Ops Manager integration
```

### Community Service (`app/services/deployments_community_service.py`)

Complete implementation for community deployments **without Ops Manager**.

**Key functions**:

#### Create Deployment
```python
def create_deployment_community(
    tenant_id, deployment_id, namespace, 
    deployment_type, mongo_version, 
    display_name, environment, members
)
```
- Creates `MongoDBCommunity` CR (apiVersion: mongodbcommunity.mongodb.com/v1)
- Only supports `ReplicaSet` type
- Uses SCRAM authentication with mongodb-admin-secret
- No Ops Manager references
- Returns (deployment_doc, response) tuple

#### Lifecycle Operations
```python
def shutdown_deployment_community(namespace, deployment_id)
    # Scales StatefulSet to 0 replicas

def start_deployment_community(namespace, deployment_id, target_members)
    # Restores StatefulSet replicas

def restart_deployment_community(namespace, deployment_id)
    # Annotates StatefulSet for rolling restart
```

#### Scaling & Upgrades
```python
def scale_deployment_community(namespace, deployment_id, new_members)
    # Patches MongoDBCommunity CR spec.members

def upgrade_version_community(namespace, deployment_id, new_version)
    # Patches MongoDBCommunity CR spec.version
```

#### Status
```python
def get_community_deployment_status(namespace, deployment_id)
    # Reads MongoDBCommunity CR status
```

#### Delete
```python
def delete_deployment_community(namespace, deployment_id)
    # Deletes MongoDBCommunity CR
```

---

## 3. K8s Client Updates (`app/services/k8s_client.py`)

Added separate helper methods for enterprise and community CRs:

### Enterprise Helpers (mongodb.com/v1)
```python
def create_mongodb_enterprise_cr(namespace, body)
def get_mongodb_enterprise_cr(namespace, name)
def list_mongodb_enterprise_crs(namespace)
def delete_mongodb_enterprise_cr(namespace, name)
def patch_mongodb_enterprise_cr(namespace, name, patch)
```

### Community Helpers (mongodbcommunity.mongodb.com/v1)
```python
def create_mongodb_community_cr(namespace, body)
def get_mongodb_community_cr(namespace, name)
def list_mongodb_community_crs(namespace)
def delete_mongodb_community_cr(namespace, name)
def patch_mongodb_community_cr(namespace, name, patch)
```

### Legacy Methods
Existing methods now delegate to enterprise versions for backward compatibility:
```python
def create_mongodb_cr(...)  → calls create_mongodb_enterprise_cr()
def get_mongodb_cr(...)     → calls get_mongodb_enterprise_cr()
def list_mongodb_crs(...)   → calls list_mongodb_enterprise_crs()
def delete_mongodb_cr(...)  → calls delete_mongodb_enterprise_cr()
def patch_mongodb_cr(...)   → calls patch_mongodb_enterprise_cr()
```

---

## 4. Routing Logic in Main Services

### Deployments Service (`app/services/deployments_service.py`)

**`create_deployment()`**:
```python
def create_deployment(...):
    tenant = repo.get_tenant(tenant_id)
    plan = tenant.get("plan", "enterprise")  # Default for existing tenants
    
    if plan == "community":
        # Route to community service
        deployment_doc, response = deployments_community_service.create_deployment_community(...)
        repo.insert_deployment(deployment_doc)
        return response
    
    # Continue with enterprise logic (existing code)
```

**`delete_deployment()`**:
```python
def delete_deployment(...):
    tenant = repo.get_tenant(tenant_id)
    plan = tenant.get("plan", "enterprise")
    
    if plan == "community":
        k8s_deleted = deployments_community_service.delete_deployment_community(...)
    else:
        k8s_deleted = k8s.delete_mongodb_enterprise_cr(...)
    
    db_deleted = repo.delete_deployment(...)
    return k8s_deleted or db_deleted
```

**`get_deployment_details()`**:
```python
def get_deployment_details(...):
    deployment = repo.get_deployment(...)
    plan = deployment.get("plan", "enterprise")
    
    if plan == "community":
        cr = k8s.get_mongodb_community_cr(...)
    else:
        cr = k8s.get_mongodb_enterprise_cr(...)
    
    # Extract status from CR
```

### Lifecycle Service (`app/services/lifecycle_service.py`)

**`shutdown_deployment()`**:
```python
def shutdown_deployment(...):
    tenant = repo.get_tenant(tenant_id)
    plan = tenant.get("plan", "enterprise")
    
    if plan == "community":
        result = deployments_community_service.shutdown_deployment_community(...)
        # Store shutdown info in DB
        return result
    
    # Continue with enterprise logic
```

**`start_deployment()`**:
```python
def start_deployment(...):
    tenant = repo.get_tenant(tenant_id)
    plan = tenant.get("plan", "enterprise")
    
    if plan == "community":
        result = deployments_community_service.start_deployment_community(...)
        return result
    
    # Continue with enterprise logic
```

**`restart_deployment()`**:
```python
def restart_deployment(...):
    tenant = repo.get_tenant(tenant_id)
    plan = tenant.get("plan", "enterprise")
    
    if plan == "community":
        result = deployments_community_service.restart_deployment_community(...)
        return result
    
    # Continue with enterprise logic
```

**`update_backup_setting()`**:
```python
def update_backup_setting(...):
    tenant = repo.get_tenant(tenant_id)
    plan = tenant.get("plan", "enterprise")
    
    if plan == "community":
        raise ValueError("Backup is not supported for community deployments")
    
    # Continue with enterprise Ops Manager backup logic
```

### Scaling Service (`app/services/scaling_service.py`)

**`scale_deployment()`**:
```python
def scale_deployment(...):
    tenant = repo.get_tenant(tenant_id)
    plan = tenant.get("plan", "enterprise")
    
    # Validate members count (both plans)
    if members < 3:
        raise ValueError("Replica set must have at least 3 members")
    
    if plan == "community":
        deployments_community_service.scale_deployment_community(...)
        repo.update_deployment(...)  # Update DB
        return result
    
    # Continue with enterprise logic (patch MongoDB CR)
```

**`upgrade_version()`**:
```python
def upgrade_version(...):
    tenant = repo.get_tenant(tenant_id)
    plan = tenant.get("plan", "enterprise")
    
    # Get current version and validate (both plans)
    current_version = deployment.get("lastRequestedSpec", {}).get("mongoVersion")
    comparison = compare_versions(mongo_version, current_version)
    
    if comparison < 0:
        raise ValueError("Downgrades not supported")
    
    if plan == "community":
        deployments_community_service.upgrade_version_community(...)
    else:
        k8s.patch_mongodb_enterprise_cr(...)  # Enterprise
    
    repo.update_deployment(...)  # Update DB for both
```

---

## 5. API Behavior

### Same REST Endpoints
All existing REST endpoints remain unchanged:
- `POST /tenants` (now accepts `plan` field)
- `DELETE /tenants/{tenantId}`
- `POST /tenants/{tenantId}/deployments`
- `GET /tenants/{tenantId}/deployments`
- `GET /tenants/{tenantId}/deployments/{deploymentId}`
- `DELETE /tenants/{tenantId}/deployments/{deploymentId}`
- `POST /.../actions/shutdown`
- `POST /.../actions/start`
- `POST /.../actions/restart`
- `PATCH /.../scale`
- `PATCH /.../version`
- `PATCH /.../backup` (returns 400 for community)
- `PATCH /.../monitoring/prometheus`

### Plan-Specific Behavior

#### Enterprise Plan (Ops Manager)
✅ All features supported:
- Standalone, ReplicaSet, ShardedCluster
- Ops Manager integration
- Backup enable/disable
- Prometheus monitoring
- Scale, upgrade, lifecycle operations

#### Community Plan (No Ops Manager)
✅ Supported:
- ReplicaSet only
- Scale members
- Upgrade MongoDB version
- Shutdown/start/restart
- Connection info
- Prometheus monitoring (via Service annotation)
- Delete deployment

❌ Not Supported:
- Standalone deployments
- ShardedCluster deployments
- Backup (returns HTTP 400 with message: "Backup is not supported for community deployments")

---

## 6. MongoDB Document Structure

### Tenant Document
```json
{
  "_id": "t-acme",
  "tenantId": "t-acme",
  "namespace": "mdb-t-acme",
  "displayName": "Acme Corp",
  "plan": "enterprise",  // NEW: "enterprise" or "community"
  "createdAt": "2026-02-10T...",
  "status": "Active",
  "opsManager": {  // Only present for enterprise
    "projectName": "mdb-t-acme-project"
  }
}
```

### Deployment Document
```json
{
  "_id": "t-acme:rs-orders",
  "tenantId": "t-acme",
  "deploymentId": "rs-orders",
  "namespace": "mdb-t-acme",
  "k8sName": "rs-orders",
  "type": "ReplicaSet",
  "plan": "enterprise",  // NEW: inherited from tenant or set during creation
  "displayName": "Orders Database",
  "environment": "prod",
  "createdAt": "2026-02-10T...",
  "lastRequestedSpec": {
    "mongoVersion": "8.0.3",
    "members": 3
  },
  "lastKnownStatus": {
    "phase": "Running"
  }
}
```

---

## 7. Testing

### Test Enterprise Tenant (Backward Compatibility)
```bash
# Create enterprise tenant (default)
curl -X POST http://localhost:8001/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "tenantId": "t-enterprise",
    "displayName": "Enterprise Tenant"
  }'

# Create ReplicaSet deployment
curl -X POST http://localhost:8001/tenants/t-enterprise/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentId": "rs-prod",
    "type": "ReplicaSet",
    "mongoVersion": "8.0.3",
    "members": 3,
    "displayName": "Production DB",
    "environment": "prod"
  }'

# Verify MongoDB CR created (mongodb.com/v1)
kubectl get mongodb -n mdb-t-enterprise

# Test backup (should work)
curl -X PATCH http://localhost:8001/tenants/t-enterprise/deployments/rs-prod/backup \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

### Test Community Tenant
```bash
# Create community tenant
curl -X POST http://localhost:8001/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "tenantId": "t-community",
    "displayName": "Community Tenant",
    "plan": "community"
  }'

# Verify no Ops Manager ConfigMap/Secret created
kubectl get configmap -n mdb-t-community | grep om-
kubectl get secret -n mdb-t-community | grep om-

# Create ReplicaSet deployment
curl -X POST http://localhost:8001/tenants/t-community/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentId": "rs-test",
    "type": "ReplicaSet",
    "mongoVersion": "8.0.3",
    "members": 3,
    "displayName": "Test DB",
    "environment": "dev"
  }'

# Verify MongoDBCommunity CR created (mongodbcommunity.mongodb.com/v1)
kubectl get mongodbcommunity -n mdb-t-community

# Test backup (should return 400 error)
curl -X PATCH http://localhost:8001/tenants/t-community/deployments/rs-test/backup \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
# Expected: {"error": "Backup is not supported for community deployments"}

# Test scale (should work)
curl -X PATCH http://localhost:8001/tenants/t-community/deployments/rs-test/scale \
  -H "Content-Type: application/json" \
  -d '{"members": 5}'

# Test shutdown (should work)
curl -X POST http://localhost:8001/tenants/t-community/deployments/rs-test/actions/shutdown
```

---

## 8. File Summary

### Modified Files
1. ✅ `app/models/dto.py` - Added `plan` field to tenant DTOs
2. ✅ `app/services/tenants_service.py` - Added plan handling, routing in delete
3. ✅ `app/services/k8s_client.py` - Added enterprise/community CR helpers
4. ✅ `app/services/deployments_service.py` - Added routing based on tenant plan
5. ✅ `app/services/lifecycle_service.py` - Added routing, blocked backup for community
6. ✅ `app/services/scaling_service.py` - Added routing for scale/upgrade
7. ✅ `app/main.py` - Pass plan parameter to onboard_tenant

### New Files
1. ✅ `app/services/deployments_community_service.py` - Complete community implementation
2. ✅ `app/services/deployments_enterprise_service.py` - Enterprise wrapper

---

## 9. Migration Notes

### Existing Tenants
- Tenants created before this update will not have a `plan` field
- Default to `"enterprise"` via: `tenant.get("plan", "enterprise")`
- No migration script needed - backward compatible

### Kubernetes Prerequisites

#### For Community Deployments
Requires MongoDB Community Operator installed in cluster:
```bash
# Install MongoDB Community Operator
kubectl apply -f https://raw.githubusercontent.com/mongodb/mongodb-kubernetes-operator/master/config/crd/bases/mongodbcommunity.mongodb.com_mongodbcommunity.yaml
kubectl apply -f https://raw.githubusercontent.com/mongodb/mongodb-kubernetes-operator/master/config/manager/manager.yaml
```

#### For Enterprise Deployments (Existing)
Requires MongoDB Enterprise Operator + Ops Manager connection.

---

## 10. Future Enhancements

### Potential Additions
1. **Standalone support for community** - Currently only ReplicaSet
2. **ShardedCluster support for community** - If operator supports it
3. **Per-deployment plan override** - Currently plan is tenant-level only
4. **Community backup via S3** - Alternative to Ops Manager backup
5. **Mixed tenants** - Allow both plans in same tenant (requires separate logic)

---

## Summary

✅ **Clean separation** between enterprise (Ops Manager) and community (no Ops Manager) logic  
✅ **Backward compatible** - existing enterprise deployments work as-is  
✅ **Flexible routing** - services dispatch based on tenant plan  
✅ **Feature parity where possible** - lifecycle operations work for both  
✅ **Clear limitations** - backup blocked for community with meaningful error  

The implementation follows the specification exactly while maintaining clean code architecture and backward compatibility.
