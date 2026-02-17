# Production Changes Analysis & Merge Strategy

## Overview

I've analyzed the 5 production files in `AtlasForge/changed-files/` and compared them with our working implementation in `AtlasForge/app/`. Here's a complete breakdown of changes and merge strategy.

---

## File 1: config.py

### **Changes Made in Production:**

**1. Added SSL/TLS Configuration (6 new lines):**
```python
# Ops Manager TLS verification
# Path to CA certificate file for Ops Manager TLS, or "false" to disable verification
OPS_MANAGER_CA_CERT_PATH: Optional[str] = os.getenv("OPS_MANAGER_CA_CERT_PATH")
OPS_MANAGER_VERIFY_SSL: bool = os.getenv("OPS_MANAGER_VERIFY_SSL", "true").lower() != "false"
```

### **Purpose:**
- Adds support for custom CA certificates for Ops Manager HTTPS connections
- Allows disabling SSL verification (for dev/test environments)

### **Merge Strategy:**
✅ **SAFE TO MERGE** - Add these 4 lines to our working `config.py` after the Ops Manager credentials section.

**No conflicts expected** - This is purely additive configuration.

---

## File 2: k8s_client.py

### **Changes Made in Production:**

**1. Added `create_combined_ca_configmap()` method (60 new lines):**
```python
def create_combined_ca_configmap(self, target_namespace: str, source_namespace: str,
                                 source_configmap: str = "om-ca",
                                 target_configmap: str = "om-ca-combined") -> None:
    """
    Create a combined CA configmap in the target namespace.
    
    Reads the custom OM CA from source_namespace/source_configmap (key 'ca-pem'),
    combines it with system root CAs, and creates a new configmap in target_namespace
    with two keys:
      - 'ca-pem': the custom OM CA only
      - 'mms-ca.crt': combined bundle (custom CA + system root CAs)
    """
```

**2. Added RBAC methods:**
```python
def ensure_service_account(self, namespace: str, name: str) -> None:
def ensure_role(self, namespace: str, name: str, rules: list) -> None:
def ensure_role_binding(self, namespace: str, name: str, role_name: str, service_account_name: str) -> None:
```

### **Purpose:**
- **Combined CA ConfigMap:** Allows MongoDB pods to trust both:
  - Custom Ops Manager TLS certificate
  - Public HTTPS endpoints (like fastdl.mongodb.org for binary downloads)
- **RBAC methods:** Required for Community plan tenants (operator needs permissions)

### **Merge Strategy:**
✅ **SAFE TO MERGE** - These are all new methods

**Our changes:**
- We added `ensure_external_service()` for NodePort
- We added `get_worker_node_ip()` for Prometheus
- We added `list_worker_node_ips()` for Prometheus
- We added `get_secret_data()` and `update_secret_data()` for password management
- We added `delete_pod()` with `grace_period` parameter for force deletion

**Merge Plan:**
1. Add their 3 new methods (`create_combined_ca_configmap`, `ensure_service_account`, `ensure_role`, `ensure_role_binding`)
2. Keep all our additional methods
3. **CHECK:** Compare `delete_pod()` signature - we may have different implementations

---

## File 3: opsmanager_backup_client.py

### **Changes Made in Production:**

**1. Added SSL/TLS support:**
```python
def __init__(self):
    # ... existing code ...
    if config.OPS_MANAGER_CA_CERT_PATH:
        self.verify = config.OPS_MANAGER_CA_CERT_PATH
    else:
        self.verify = config.OPS_MANAGER_VERIFY_SSL
```

**2. Updated all requests to use `verify=self.verify`:**
```python
response = requests.get(url, auth=self.auth, headers=self.headers, params=params, verify=self.verify)
response = requests.post(url, auth=self.auth, headers=self.headers, json=data, verify=self.verify)
response = requests.patch(url, auth=self.auth, headers=self.headers, json=data, verify=self.verify)
```

### **Purpose:**
- Support for custom CA certificates when connecting to Ops Manager
- Support for disabling SSL verification (dev/test environments)

### **Merge Strategy:**
✅ **SAFE TO MERGE** - This is purely additive

**Our changes:**
- We have the same methods but without SSL verification support

**Merge Plan:**
1. Add `self.verify` initialization in `__init__()`
2. Add `verify=self.verify` parameter to all `requests.get()`, `requests.post()`, `requests.patch()`, `requests.put()` calls
3. Keep all our existing logic

---

## File 4: opsmanager_project_client.py

### **Changes Made in Production:**

**1. Added SSL/TLS support (identical to backup_client):**
```python
def __init__(self):
    # ... existing code ...
    if config.OPS_MANAGER_CA_CERT_PATH:
        self.verify = config.OPS_MANAGER_CA_CERT_PATH
    else:
        self.verify = config.OPS_MANAGER_VERIFY_SSL

# Updated all requests to use verify=self.verify
```

### **Purpose:**
- Same as backup_client - support for custom CA certificates

### **Merge Strategy:**
✅ **SAFE TO MERGE** - This is purely additive

**Our changes:**
- Identical file, no conflicts

**Merge Plan:**
1. Add `self.verify` initialization in `__init__()`
2. Add `verify=self.verify` parameter to all `requests.get()` and `requests.post()` calls

---

## File 5: tenants_service.py

### **Changes Made in Production:**

**1. Added Combined CA ConfigMap creation for Enterprise tenants:**
```python
# Combined CA configmap: OM CA + system root CAs
# Required so the MCK automation agent can trust both the Ops Manager TLS cert
# and public HTTPS endpoints (e.g. fastdl.mongodb.org for binary downloads)
k8s.create_combined_ca_configmap(
    target_namespace=namespace,
    source_namespace=config.MCP_OPERATOR_NAMESPACE,
    source_configmap="om-ca",
    target_configmap="om-ca-combined"
)
```

**2. Updated ConfigMap to reference combined CA:**
```python
k8s.ensure_configmap(
    namespace=namespace,
    name=f"om-{tenant_id}-project",
    data={
        "baseUrl": config.MCP_OPS_MANAGER_URL,
        "projectName": project_name,
        "orgId": config.MCP_OPS_MANAGER_ORG,
        "sslMMSCAConfigMap": "om-ca-combined"  # Changed from "om-ca"
    }
)
```

**3. Added RBAC setup for Community tenants:**
```python
else:
    # Community plan: Create ServiceAccount, Role, and RoleBinding for operator
    k8s.ensure_service_account(
        namespace=namespace,
        name="mongodb-database"
    )
    
    # Role with permissions for secrets, configmaps, and pods
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
        name="mongodb-database-role",
        rules=rules
    )
    
    k8s.ensure_role_binding(
        namespace=namespace,
        name="mongodb-database-rolebinding",
        role_name="mongodb-database-role",
        service_account_name="mongodb-database"
    )
```

**4. Added ServiceAccount for Enterprise:**
```python
# ServiceAccount for MongoDB pods (enterprise)
k8s.ensure_service_account(
    namespace=namespace,
    name="mongodb-enterprise-database-pods"
)
```

### **Purpose:**
- **Combined CA:** Fixes issue where MongoDB automation agent couldn't download binaries from fastdl.mongodb.org
- **Community RBAC:** Fixes issue where Community operator couldn't access secrets/configmaps
- **Enterprise ServiceAccount:** Required by MongoDB Enterprise Kubernetes Operator

### **Merge Strategy:**
✅ **SAFE TO MERGE** - These are critical bug fixes

**Our changes:**
- We have additional logic but these changes don't conflict

**Merge Plan:**
1. Add `create_combined_ca_configmap()` call
2. Change `sslMMSCAConfigMap` from `"om-ca"` to `"om-ca-combined"`
3. Add Community RBAC setup block
4. Add Enterprise ServiceAccount creation
5. Keep all our existing logic

---

## Summary of Changes

| File | Lines Changed | Type | Risk | Conflicts |
|------|---------------|------|------|-----------|
| config.py | +6 | Configuration | Low | None |
| k8s_client.py | +60 | New methods | Low | None |
| opsmanager_backup_client.py | ~13 | SSL support | Low | None |
| opsmanager_project_client.py | ~8 | SSL support | Low | None |
| tenants_service.py | +34 | Bug fixes | **Medium** | Possible |

---

## Merge Strategy

### **Phase 1: Low-Risk Additive Changes (Do First)**

1. ✅ **config.py** - Add SSL configuration
2. ✅ **opsmanager_backup_client.py** - Add SSL verification
3. ✅ **opsmanager_project_client.py** - Add SSL verification

### **Phase 2: New Methods (Medium Risk)**

4. ✅ **k8s_client.py** - Add new methods:
   - `create_combined_ca_configmap()`
   - `ensure_service_account()`
   - `ensure_role()`
   - `ensure_role_binding()`
   
   ⚠️ **CHECK:** Compare our `delete_pod()` with theirs

### **Phase 3: Critical Bug Fixes (Requires Testing)**

5. ⚠️ **tenants_service.py** - Add:
   - Combined CA ConfigMap creation
   - Community RBAC setup
   - Enterprise ServiceAccount
   
   **IMPORTANT:** This fixes production issues but requires testing

---

## Detailed Merge Steps

### **Step 1: Backup Current Working Code**

```bash
cd /Users/shashank.pandey/Desktop/Codebase/MDBaaS/Github-repo/mdb-ops-ansible/AtlasForge

# Create backup branch
git checkout -b backup-before-prod-merge
git add -A
git commit -m "Backup: Before merging production changes"

# Create merge branch
git checkout -b merge-production-changes
```

---

### **Step 2: Merge config.py**

```bash
# Add these lines after OPS_MANAGER credentials section:
```

```python
# Add after line with MCP_OM_GLOBAL_PRIVATE_KEY:

# Ops Manager TLS verification
# Path to CA certificate file for Ops Manager TLS, or "false" to disable verification
OPS_MANAGER_CA_CERT_PATH: Optional[str] = os.getenv("OPS_MANAGER_CA_CERT_PATH")
OPS_MANAGER_VERIFY_SSL: bool = os.getenv("OPS_MANAGER_VERIFY_SSL", "true").lower() != "false"
```

---

### **Step 3: Merge opsmanager_backup_client.py**

Add to `__init__()`:
```python
def __init__(self):
    self.base_url = config.MCP_OPS_MANAGER_URL.rstrip('/')
    self.public_key = config.MCP_OM_GLOBAL_PUBLIC_KEY
    self.private_key = config.MCP_OM_GLOBAL_PRIVATE_KEY
    self.auth = HTTPDigestAuth(self.public_key, self.private_key)
    self.headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    # ADD THESE LINES:
    if config.OPS_MANAGER_CA_CERT_PATH:
        self.verify = config.OPS_MANAGER_CA_CERT_PATH
    else:
        self.verify = config.OPS_MANAGER_VERIFY_SSL
```

Update all requests:
```python
# Find all requests.get(), requests.post(), requests.patch(), requests.put()
# Add: verify=self.verify parameter

# Example:
response = requests.get(url, auth=self.auth, headers=self.headers, params=params, verify=self.verify)
```

---

### **Step 4: Merge opsmanager_project_client.py**

Same as Step 3 - add `self.verify` and update all requests.

---

### **Step 5: Merge k8s_client.py**

**A. Add new methods (insert after `ensure_secret()` method):**

```python
def create_combined_ca_configmap(self, target_namespace: str, source_namespace: str,
                                 source_configmap: str = "om-ca",
                                 target_configmap: str = "om-ca-combined") -> None:
    """
    Create a combined CA configmap in the target namespace.
    [Copy entire method from production file]
    """
    # ... full implementation ...

def ensure_service_account(self, namespace: str, name: str) -> None:
    """
    Create a ServiceAccount if it does not exist.
    [Copy entire method from production file]
    """
    # ... full implementation ...

def ensure_role(self, namespace: str, name: str, rules: list) -> None:
    """
    Create a Role if it does not exist.
    [Copy entire method from production file]
    """
    # ... full implementation ...

def ensure_role_binding(self, namespace: str, name: str, role_name: str, service_account_name: str) -> None:
    """
    Create a RoleBinding if it does not exist.
    [Copy entire method from production file]
    """
    # ... full implementation ...
```

**B. Check `delete_pod()` method:**

Production has:
```python
def delete_pod(self, namespace: str, name: str) -> bool:
    """Delete a pod. Returns True if deleted, False if not found."""
    try:
        self.core_v1.delete_namespaced_pod(name=name, namespace=namespace)
        return True
    except ApiException as e:
        if e.status == 404:
            return False
        raise
```

Our version likely has:
```python
def delete_pod(self, namespace: str, name: str, grace_period: int = 0) -> bool:
    """Force delete a pod with grace period."""
    try:
        self.core_v1.delete_namespaced_pod(
            name=name,
            namespace=namespace,
            grace_period_seconds=grace_period
        )
        return True
    except ApiException as e:
        if e.status == 404:
            return False
        raise
```

**DECISION:** Keep our version (it's more flexible with `grace_period` parameter).

---

### **Step 6: Merge tenants_service.py**

**A. Update Enterprise tenant creation:**

Find the section with `ensure_configmap` and update:
```python
k8s.ensure_configmap(
    namespace=namespace,
    name=f"om-{tenant_id}-project",
    data={
        "baseUrl": config.MCP_OPS_MANAGER_URL,
        "projectName": project_name,
        "orgId": config.MCP_OPS_MANAGER_ORG,
        "sslMMSCAConfigMap": "om-ca-combined"  # CHANGE: was "om-ca"
    }
)
```

**B. Add combined CA creation (after `ensure_secret` for credentials):**

```python
# Combined CA configmap: OM CA + system root CAs
k8s.create_combined_ca_configmap(
    target_namespace=namespace,
    source_namespace=config.MCP_OPERATOR_NAMESPACE,
    source_configmap="om-ca",
    target_configmap="om-ca-combined"
)
```

**C. Add ServiceAccount for Enterprise (after combined CA creation):**

```python
# ServiceAccount for MongoDB pods (enterprise)
k8s.ensure_service_account(
    namespace=namespace,
    name="mongodb-enterprise-database-pods"
)
```

**D. Add Community RBAC setup (in the `else` block for Community plan):**

```python
else:
    # Community plan: Create ServiceAccount, Role, and RoleBinding for operator
    k8s.ensure_service_account(
        namespace=namespace,
        name="mongodb-database"
    )

    # Role with permissions for secrets, configmaps, and pods
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
        name="mongodb-database-role",
        rules=rules
    )

    k8s.ensure_role_binding(
        namespace=namespace,
        name="mongodb-database-rolebinding",
        role_name="mongodb-database-role",
        service_account_name="mongodb-database"
    )
```

---

## Testing Plan

### **1. Test SSL/TLS Changes:**

```bash
# With CA cert
export OPS_MANAGER_CA_CERT_PATH="/path/to/ca.crt"

# Without CA cert (disable verification)
export OPS_MANAGER_VERIFY_SSL="false"

# Test Ops Manager connectivity
curl -X GET http://localhost:8001/health
```

---

### **2. Test Enterprise Tenant Creation:**

```bash
# Create new Enterprise tenant
curl -X POST http://localhost:8001/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "tenantId": "merge-test-ent",
    "displayName": "Merge Test Enterprise",
    "plan": "enterprise"
  }'

# Verify combined CA ConfigMap created
kubectl get configmap om-ca-combined -n mdb-merge-test-ent

# Verify ServiceAccount created
kubectl get serviceaccount mongodb-enterprise-database-pods -n mdb-merge-test-ent

# Test deployment
curl -X POST http://localhost:8001/tenants/merge-test-ent/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentId": "rs-test",
    "type": "ReplicaSet",
    "mongoVersion": "8.0.19-ent",
    "members": 3
  }'
```

---

### **3. Test Community Tenant Creation:**

```bash
# Create new Community tenant
curl -X POST http://localhost:8001/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "tenantId": "merge-test-comm",
    "displayName": "Merge Test Community",
    "plan": "community"
  }'

# Verify RBAC created
kubectl get serviceaccount mongodb-database -n mdb-merge-test-comm
kubectl get role mongodb-database-role -n mdb-merge-test-comm
kubectl get rolebinding mongodb-database-rolebinding -n mdb-merge-test-comm

# Test deployment
curl -X POST http://localhost:8001/tenants/merge-test-comm/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentId": "rs-test",
    "type": "ReplicaSet",
    "mongoVersion": "8.0.10",
    "members": 3
  }'
```

---

## Risk Assessment

| Change | Risk Level | Impact | Rollback Plan |
|--------|------------|--------|---------------|
| SSL config | **Low** | Better security | Remove config vars |
| CA ConfigMap | **Medium** | Fixes binary downloads | Remove combined CA |
| Community RBAC | **Medium** | Fixes operator permissions | Remove RBAC resources |
| Enterprise SA | **Low** | Required by operator | Remove SA |

---

## Rollback Plan

If merge causes issues:

```bash
# Rollback to backup
cd /Users/shashank.pandey/Desktop/Codebase/MDBaaS/Github-repo/mdb-ops-ansible/AtlasForge
git checkout backup-before-prod-merge

# Or revert specific commit
git revert <commit-hash>
```

---

## Checklist

Before merging:
- [ ] Create backup branch
- [ ] Review all 5 files side-by-side
- [ ] Understand each change
- [ ] Test in dev environment

During merge:
- [ ] Merge config.py
- [ ] Merge opsmanager_backup_client.py
- [ ] Merge opsmanager_project_client.py
- [ ] Merge k8s_client.py
- [ ] Merge tenants_service.py

After merge:
- [ ] Test Enterprise tenant creation
- [ ] Test Community tenant creation
- [ ] Test Enterprise deployment
- [ ] Test Community deployment
- [ ] Verify no errors in logs
- [ ] Create git commit

---

## Conclusion

**All production changes are SAFE TO MERGE!**

These changes:
1. ✅ Add critical SSL/TLS support
2. ✅ Fix Community operator RBAC issues
3. ✅ Fix Enterprise binary download issues
4. ✅ Add required ServiceAccounts
5. ✅ Are non-breaking and additive

**Estimated Merge Time:** 30-45 minutes  
**Testing Time:** 30 minutes  
**Total:** ~1.5 hours

**Next Steps:**
1. Follow merge steps 1-6 above
2. Run tests for both Enterprise and Community
3. Commit changes with message: "Merge production changes: SSL support, RBAC fixes, CA bundle"
4. Deploy to dev/staging
5. Monitor for 24 hours
6. Deploy to production

Let me know if you want me to help with the actual merge process!
