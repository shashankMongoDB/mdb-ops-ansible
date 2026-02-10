# Community Tenant Bootstrap and Deployment Status Implementation

## Overview

Implemented the missing pieces for community tenant support:
1. **Namespace-scoped RBAC setup** for community tenants
2. **Plan-based CR lookup** in all deployment status/monitoring paths

---

## 1. Community Tenant K8s Bootstrap

### New K8s Client Helpers (`k8s_client.py`)

Added namespace-scoped RBAC helpers:

#### `ensure_role(namespace, name, rules)`
```python
def ensure_role(self, namespace: str, name: str, rules: list) -> None:
    """
    Create a Role if it does not exist.
    If it already exists, do nothing (no error).
    
    Used for community tenant RBAC setup.
    """
    from kubernetes import client as k8s_client
    
    try:
        rbac_v1 = k8s_client.RbacAuthorizationV1Api(self.core_v1.api_client)
        rbac_v1.read_namespaced_role(name=name, namespace=namespace)
    except ApiException as e:
        if e.status == 404:
            role = k8s_client.V1Role(
                metadata=k8s_client.V1ObjectMeta(name=name, namespace=namespace),
                rules=rules
            )
            rbac_v1.create_namespaced_role(namespace=namespace, body=role)
        else:
            raise
```

#### `ensure_role_binding(namespace, name, role_name, service_account_name)`
```python
def ensure_role_binding(self, namespace: str, name: str, role_name: str, 
                       service_account_name: str) -> None:
    """
    Create a RoleBinding if it does not exist.
    Binds a ServiceAccount to a Role in the same namespace.
    """
    from kubernetes import client as k8s_client
    
    try:
        rbac_v1 = k8s_client.RbacAuthorizationV1Api(self.core_v1.api_client)
        rbac_v1.read_namespaced_role_binding(name=name, namespace=namespace)
    except ApiException as e:
        if e.status == 404:
            role_binding = k8s_client.V1RoleBinding(
                metadata=k8s_client.V1ObjectMeta(name=name, namespace=namespace),
                role_ref=k8s_client.V1RoleRef(
                    api_group="rbac.authorization.k8s.io",
                    kind="Role",
                    name=role_name
                ),
                subjects=[
                    k8s_client.V1Subject(
                        kind="ServiceAccount",
                        name=service_account_name,
                        namespace=namespace
                    )
                ]
            )
            rbac_v1.create_namespaced_role_binding(namespace=namespace, body=role_binding)
        else:
            raise
```

**Key Features:**
- ✅ Idempotent (check-if-exists-then-create)
- ✅ Namespace-scoped only (no cluster-wide RBAC)
- ✅ Proper error handling

---

### Updated Tenant Onboarding (`tenants_service.py`)

#### Enterprise Plan (Unchanged)
```python
if plan == "enterprise":
    project_name = f"mdb-{tenant_id}-project"
    
    # Create Ops Manager ConfigMap
    k8s.ensure_configmap(
        namespace=namespace,
        name=f"om-{tenant_id}-project",
        data={
            "baseUrl": config.MCP_OPS_MANAGER_URL,
            "projectName": project_name,
            "orgId": config.MCP_OPS_MANAGER_ORG
        }
    )
    
    # Create Ops Manager credentials Secret
    k8s.ensure_secret(
        namespace=namespace,
        name=f"om-{tenant_id}-credentials",
        string_data={
            "user": config.MCP_OM_GLOBAL_PUBLIC_KEY,
            "publicApiKey": config.MCP_OM_GLOBAL_PRIVATE_KEY
        }
    )
    
    # ServiceAccount for MongoDB pods
    k8s.ensure_service_account(
        namespace=namespace,
        name="mongodb-kubernetes-database-pods"
    )
```

#### Community Plan (New RBAC Setup)
```python
else:  # plan == "community"
    # ServiceAccount for community operator
    k8s.ensure_service_account(
        namespace=namespace,
        name="mongodb-kubernetes-appdb"
    )
    
    # Role with permissions for operator
    rules = [
        k8s_client.V1PolicyRule(
            api_groups=[""],
            resources=["secrets", "configmaps"],
            verbs=["get", "list", "watch"]
        ),
        k8s_client.V1PolicyRule(
            api_groups=[""],
            resources=["pods"],
            verbs=["get", "list", "watch", "update", "patch"]
        )
    ]
    
    k8s.ensure_role(
        namespace=namespace,
        name="mongodb-kubernetes-appdb-role",
        rules=rules
    )
    
    # RoleBinding to bind SA to Role
    k8s.ensure_role_binding(
        namespace=namespace,
        name="mongodb-kubernetes-appdb-rolebinding",
        role_name="mongodb-kubernetes-appdb-role",
        service_account_name="mongodb-kubernetes-appdb"
    )

# Admin password secret for BOTH plans
admin_password = generate_password()
k8s.ensure_secret(
    namespace=namespace,
    name="mongodb-admin-secret",
    string_data={"password": admin_password}
)
```

### Community Namespace Resources Created

For a community tenant `t-initech`:

**1. ServiceAccount:**
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: mongodb-kubernetes-appdb
  namespace: mdb-t-initech
```

**2. Role:**
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: mongodb-kubernetes-appdb-role
  namespace: mdb-t-initech
rules:
  - apiGroups: [""]
    resources: ["secrets", "configmaps"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch", "update", "patch"]
```

**3. RoleBinding:**
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: mongodb-kubernetes-appdb-rolebinding
  namespace: mdb-t-initech
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: mongodb-kubernetes-appdb-role
subjects:
  - kind: ServiceAccount
    name: mongodb-kubernetes-appdb
    namespace: mdb-t-initech
```

**4. Secret (both plans):**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mongodb-admin-secret
  namespace: mdb-t-initech
type: Opaque
stringData:
  password: <generated>
```

---

## 2. Plan-Based CR Lookup in Status Paths

### Pattern Applied to All Functions

**Before (single CR type):**
```python
cr = k8s.get_mongodb_cr(namespace, deployment_id)
if not cr:
    raise ValueError(f"MongoDB CR {deployment_id} not found")
```

**After (plan-based branching):**
```python
plan = tenant.get("plan", "enterprise")

# Get CR based on plan
if plan == "community":
    cr = k8s.get_mongodb_community_cr(namespace, deployment_id)
else:
    cr = k8s.get_mongodb_enterprise_cr(namespace, deployment_id)

if not cr:
    raise ValueError(f"MongoDB CR {deployment_id} not found")
```

---

### Updated Functions

#### 1. `deployments_service.py` - `get_deployment_details()`
**Status:** ✅ Already updated (previous implementation)

```python
# Get CR status based on plan
plan = deployment.get("plan", "enterprise")
if plan == "community":
    cr = k8s.get_mongodb_community_cr(deployment["namespace"], deployment_id)
else:
    cr = k8s.get_mongodb_enterprise_cr(deployment["namespace"], deployment_id)

if cr and "status" in cr:
    result["k8sPhase"] = cr["status"].get("phase", "Unknown")
```

#### 2. `lifecycle_service.py` - `get_connection_info()`
**Status:** ✅ Updated

```python
plan = tenant.get("plan", "enterprise")

# Get CR based on plan
if plan == "community":
    cr = k8s.get_mongodb_community_cr(namespace, deployment_id)
else:
    cr = k8s.get_mongodb_enterprise_cr(namespace, deployment_id)

if not cr:
    raise ValueError(f"MongoDB CR {deployment_id} not found in namespace {namespace}")

# Build connection string (same for both plans)
service_name = f"{deployment_id}-svc"
mongo_uri = f"mongodb://{service_name}.{namespace}.svc.cluster.local:27017"
```

#### 3. `lifecycle_service.py` - Lifecycle Operations
**Status:** ✅ Already routed (previous implementation)

Functions like `shutdown_deployment()`, `start_deployment()`, `restart_deployment()` already route to community service functions before accessing CRs:

```python
plan = tenant.get("plan", "enterprise")

if plan == "community":
    result = deployments_community_service.shutdown_deployment_community(namespace, deployment_id)
    return {
        "tenantId": tenant_id,
        "deploymentId": deployment_id,
        **result
    }

# Enterprise logic continues with k8s.get_mongodb_enterprise_cr(...)
```

#### 4. `lifecycle_service.py` - `update_backup_setting()`
**Status:** ✅ Already blocks community (previous implementation)

```python
plan = tenant.get("plan", "enterprise")
if plan == "community":
    raise ValueError("Backup is not supported for community deployments")

# Enterprise backup logic continues
```

#### 5. `monitoring_service.py` - `enable_prometheus_metrics()`
**Status:** ✅ Updated

```python
plan = tenant.get("plan", "enterprise")

# Get CR based on plan
if plan == "community":
    cr = k8s.get_mongodb_community_cr(namespace, deployment_id)
else:
    cr = k8s.get_mongodb_enterprise_cr(namespace, deployment_id)

if not cr:
    raise ValueError(f"MongoDB CR {deployment_id} not found")

patch = {
    "spec": {
        "prometheus": {
            "username": "prometheus-user",
            "passwordSecretRef": {"name": "mongodb-admin-secret"}
        }
    }
}

# Patch CR based on plan
if plan == "community":
    k8s.patch_mongodb_community_cr(namespace, deployment_id, patch)
else:
    k8s.patch_mongodb_enterprise_cr(namespace, deployment_id, patch)
```

#### 6. `monitoring_service.py` - `disable_prometheus_metrics()`
**Status:** ✅ Updated

```python
plan = tenant.get("plan", "enterprise")

# Get CR based on plan
if plan == "community":
    cr = k8s.get_mongodb_community_cr(namespace, deployment_id)
else:
    cr = k8s.get_mongodb_enterprise_cr(namespace, deployment_id)

if cr:
    patch = {"spec": {"prometheus": None}}
    
    # Patch based on plan
    if plan == "community":
        k8s.patch_mongodb_community_cr(namespace, deployment_id, patch)
    else:
        k8s.patch_mongodb_enterprise_cr(namespace, deployment_id, patch)
```

#### 7. `monitoring_service.py` - `get_prometheus_config()`
**Status:** ✅ Updated

```python
plan = tenant.get("plan", "enterprise")

# Get CR based on plan
if plan == "community":
    cr = k8s.get_mongodb_community_cr(namespace, deployment_id)
else:
    cr = k8s.get_mongodb_enterprise_cr(namespace, deployment_id)

if not cr:
    raise ValueError(f"MongoDB CR {deployment_id} not found")

prometheus_enabled = cr.get("spec", {}).get("prometheus") is not None
# ... rest of config logic
```

#### 8. `scaling_service.py` - Scale and Upgrade
**Status:** ✅ Already routed (previous implementation)

These functions already route to community service functions before CR access.

---

## 3. Scope and Limitations

### What We DO Manage (Namespace-Scoped)
✅ ServiceAccount in tenant namespace  
✅ Role in tenant namespace  
✅ RoleBinding in tenant namespace  
✅ Secrets (admin password) in tenant namespace  
✅ ConfigMaps (Ops Manager - enterprise only)  

### What We DON'T Manage (Cluster-Wide)
❌ ClusterRole (handled by operator installation)  
❌ ClusterRoleBinding (handled by operator installation)  
❌ CRD installation (mongodbcommunity.mongodb.com)  
❌ Operator deployment itself  

**Assumption:** The MongoDB Community Operator is already installed cluster-wide with proper ClusterRole/ClusterRoleBinding for the `mongodbcommunity.mongodb.com` API group.

---

## 4. Testing Checklist

### Enterprise Tenant (Unchanged Behavior)
```bash
# Create enterprise tenant
POST /tenants
{
  "tenantId": "t-acme",
  "displayName": "Acme Corp",
  "plan": "enterprise"
}

# Verify K8s resources created
kubectl get namespace mdb-t-acme
kubectl get configmap -n mdb-t-acme om-t-acme-project
kubectl get secret -n mdb-t-acme om-t-acme-credentials
kubectl get secret -n mdb-t-acme mongodb-admin-secret
kubectl get serviceaccount -n mdb-t-acme mongodb-kubernetes-database-pods

# Create deployment
POST /tenants/t-acme/deployments
{
  "deploymentId": "rs-orders",
  "type": "ReplicaSet",
  "mongoVersion": "8.0.3",
  "members": 3
}

# Verify MongoDB CR created (mongodb.com)
kubectl get mongodb -n mdb-t-acme rs-orders

# Test status endpoints
GET /tenants/t-acme/deployments/rs-orders
# Should return status from Enterprise CR
```

### Community Tenant (New RBAC Setup)
```bash
# Create community tenant
POST /tenants
{
  "tenantId": "t-initech",
  "displayName": "Initech Inc",
  "plan": "community"
}

# Verify K8s resources created
kubectl get namespace mdb-t-initech
kubectl get serviceaccount -n mdb-t-initech mongodb-kubernetes-appdb
kubectl get role -n mdb-t-initech mongodb-kubernetes-appdb-role
kubectl get rolebinding -n mdb-t-initech mongodb-kubernetes-appdb-rolebinding
kubectl get secret -n mdb-t-initech mongodb-admin-secret

# Verify NO Ops Manager resources
kubectl get configmap -n mdb-t-initech | grep om-
# Should return nothing

kubectl get secret -n mdb-t-initech | grep om-
# Should return nothing

# Create deployment
POST /tenants/t-initech/deployments
{
  "deploymentId": "rs-test",
  "type": "ReplicaSet",
  "mongoVersion": "8.0.3",
  "members": 3
}

# Verify MongoDBCommunity CR created (mongodbcommunity.mongodb.com)
kubectl get mongodbcommunity -n mdb-t-initech rs-test

# Test status endpoints
GET /tenants/t-initech/deployments/rs-test
# Should return status from Community CR

# Test connection info
GET /tenants/t-initech/deployments/rs-test/connection
# Should work with community CR

# Test Prometheus
PATCH /tenants/t-initech/deployments/rs-test/monitoring/prometheus
{"enabled": true}
# Should patch community CR

# Test backup (should fail)
PATCH /tenants/t-initech/deployments/rs-test/backup
{"enabled": true}
# Expected: 400 "Backup is not supported for community deployments"
```

---

## 5. Files Modified

1. ✅ `app/services/k8s_client.py`
   - Added `ensure_role()` helper
   - Added `ensure_role_binding()` helper

2. ✅ `app/services/tenants_service.py`
   - Updated `onboard_tenant()` to create RBAC for community tenants
   - Kept enterprise behavior unchanged

3. ✅ `app/services/deployments_service.py`
   - Already has plan-based CR lookup in `get_deployment_details()`

4. ✅ `app/services/lifecycle_service.py`
   - Updated `get_connection_info()` for plan-based CR lookup
   - Lifecycle operations already route to community service

5. ✅ `app/services/monitoring_service.py`
   - Updated `enable_prometheus_metrics()` for plan-based CR lookup
   - Updated `disable_prometheus_metrics()` for plan-based CR lookup
   - Updated `get_prometheus_config()` for plan-based CR lookup

6. ✅ `app/services/scaling_service.py`
   - Already routes to community service for scale/upgrade

---

## 6. Summary

### What Was Implemented

**1. Community Tenant Bootstrap**
- ✅ ServiceAccount: `mongodb-kubernetes-appdb`
- ✅ Role: `mongodb-kubernetes-appdb-role` with secrets/configmaps/pods permissions
- ✅ RoleBinding: Binds SA to Role in namespace
- ✅ Secret: `mongodb-admin-secret` for admin password (both plans)
- ✅ No Ops Manager resources for community

**2. Plan-Based CR Lookup**
- ✅ All status/monitoring functions check tenant plan
- ✅ Enterprise: uses `get_mongodb_enterprise_cr()` (mongodb.com)
- ✅ Community: uses `get_mongodb_community_cr()` (mongodbcommunity.mongodb.com)
- ✅ Consistent error messages for both plans

**3. Scope Boundaries**
- ✅ Only namespace-scoped RBAC created
- ✅ No cluster-wide resources managed
- ✅ Assumes community operator already installed
- ✅ Enterprise behavior completely unchanged

---

## 7. Implementation Complete!

✅ **Community tenant K8s bootstrap** - ServiceAccount, Role, RoleBinding created per namespace  
✅ **Plan-based CR lookup** - All status paths check plan and use correct CR type  
✅ **Backward compatibility** - Enterprise tenants work exactly as before  
✅ **Clean separation** - No cluster-wide RBAC, only namespace-scoped  
✅ **Proper error handling** - Clear messages for missing CRs per plan  

**Ready for testing with both enterprise and community tenants!** 🎉
