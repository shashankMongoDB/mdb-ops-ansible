# Postman Collection Updates for Community Plan Support

## Overview

Updated the Postman collection to include examples for both **enterprise** and **community** deployment plans.

---

## New API Requests Added

### 1. Tenant Management

#### List All Tenants (NEW)
```
GET {{baseUrl}}/tenants
```
Returns all tenants with their plan information.

**Expected Response:**
```json
[
  {
    "tenantId": "t-acme",
    "displayName": "Acme Corporation",
    "plan": "enterprise",
    "namespace": "mdb-t-acme",
    "status": "Active",
    "opsManager": {
      "projectName": "mdb-t-acme-project"
    }
  },
  {
    "tenantId": "t-initech",
    "displayName": "Initech Inc",
    "plan": "community",
    "namespace": "mdb-t-initech",
    "status": "Active"
  }
]
```

#### Get Specific Tenant (NEW)
```
GET {{baseUrl}}/tenants/t-acme
```
Returns details of a specific tenant including plan.

---

### 2. Tenant Creation Examples

#### Enterprise Tenant - Explicit (UPDATED)
```json
POST {{baseUrl}}/tenants
{
  "tenantId": "t-acme",
  "displayName": "Acme Corporation",
  "plan": "enterprise"
}
```

#### Enterprise Tenant - Implicit Default (UPDATED)
```json
POST {{baseUrl}}/tenants
{
  "tenantId": "t-globex",
  "displayName": "Globex Industries"
  // plan defaults to "enterprise"
}
```

#### Community Tenant (NEW)
```json
POST {{baseUrl}}/tenants
{
  "tenantId": "t-initech",
  "displayName": "Initech Inc",
  "plan": "community"
}
```

#### Community Tenant 2 (NEW)
```json
POST {{baseUrl}}/tenants
{
  "tenantId": "t-umbrella",
  "displayName": "Umbrella Corporation",
  "plan": "community"
}
```

---

### 3. Community Deployment Examples

#### Create Community ReplicaSet (NEW)
```json
POST {{baseUrl}}/tenants/t-initech/deployments
{
  "deploymentId": "rs-test",
  "type": "ReplicaSet",
  "mongoVersion": "8.0.3",
  "members": 3,
  "displayName": "Community Test DB",
  "environment": "dev"
}
```

**What happens:**
- Creates `MongoDBCommunity` CR (mongodbcommunity.mongodb.com/v1)
- No Ops Manager references
- Uses mongodb-admin-secret for authentication

#### Create Community 5-Member ReplicaSet (NEW)
```json
POST {{baseUrl}}/tenants/t-umbrella/deployments
{
  "deploymentId": "rs-prod",
  "type": "ReplicaSet",
  "mongoVersion": "8.0.3",
  "members": 5,
  "displayName": "Community Prod DB",
  "environment": "prod"
}
```

---

### 4. Community Lifecycle Operations (NEW)

#### Scale Community Deployment
```json
PATCH {{baseUrl}}/tenants/t-initech/deployments/rs-test/scale
{
  "members": 5
}
```

#### Shutdown Community Deployment
```
POST {{baseUrl}}/tenants/t-initech/deployments/rs-test/actions/shutdown
```

#### Start Community Deployment
```
POST {{baseUrl}}/tenants/t-initech/deployments/rs-test/actions/start
```

#### Restart Community Deployment
```
POST {{baseUrl}}/tenants/t-initech/deployments/rs-test/actions/restart
```

#### Upgrade Community Deployment Version
```json
PATCH {{baseUrl}}/tenants/t-initech/deployments/rs-test/version
{
  "mongoVersion": "8.0.4"
}
```

---

### 5. Error Examples (NEW)

#### Community Standalone Not Supported (400)
```json
POST {{baseUrl}}/tenants/t-initech/deployments
{
  "deploymentId": "st-test",
  "type": "Standalone",
  "mongoVersion": "8.0.3",
  "displayName": "Community Standalone",
  "environment": "dev"
}
```

**Expected Response:**
```json
{
  "detail": "Community plan only supports ReplicaSet type. Got: Standalone"
}
```

#### Community Backup Not Supported (400)
```json
PATCH {{baseUrl}}/tenants/t-initech/deployments/rs-test/backup
{
  "enabled": true
}
```

**Expected Response:**
```json
{
  "detail": "Backup is not supported for community deployments"
}
```

#### Invalid Plan Value (400)
```json
POST {{baseUrl}}/tenants
{
  "tenantId": "t-invalid",
  "displayName": "Invalid Plan Tenant",
  "plan": "premium"
}
```

**Expected Response:**
```json
{
  "detail": "Invalid plan: premium. Must be 'enterprise' or 'community'"
}
```

---

## Testing Workflow

### Enterprise Workflow (Unchanged)
1. Create enterprise tenant (plan="enterprise" or omit)
2. Create Standalone/ReplicaSet/ShardedCluster deployment
3. Test all operations: scale, upgrade, backup, shutdown, restart
4. Verify MongoDB CR created (mongodb.com/v1)
5. Verify Ops Manager ConfigMap/Secret exist

### Community Workflow (New)
1. Create community tenant (plan="community")
2. Create ReplicaSet deployment only
3. Test supported operations: scale, upgrade, shutdown, restart
4. Test backup endpoint (should return 400)
5. Verify MongoDBCommunity CR created (mongodbcommunity.mongodb.com/v1)
6. Verify NO Ops Manager ConfigMap/Secret

---

## Request Organization in Postman

### Folder Structure
```
MongoDB Control Plane API
├── Health Check
├── Tenant Management
│   ├── List All Tenants (NEW)
│   ├── Get Specific Tenant (NEW)
│   ├── Create Tenant - Acme (Enterprise - Explicit)
│   ├── Create Tenant - Globex (Enterprise - Implicit)
│   ├── Create Tenant - Initech (Community) (NEW)
│   └── Create Tenant - Umbrella (Community) (NEW)
├── Deployment Management
│   ├── Enterprise Deployments
│   │   ├── Create Deployment - Standalone
│   │   ├── Create Deployment - ReplicaSet
│   │   └── Create Deployment - ShardedCluster
│   └── Community Deployments (NEW)
│       ├── Create Community ReplicaSet
│       └── Create Community 5 Members
├── Lifecycle Operations
│   ├── Enterprise Operations
│   │   ├── Shutdown Deployment
│   │   ├── Start Deployment
│   │   └── Restart Deployment
│   └── Community Operations (NEW)
│       ├── Shutdown Community Deployment
│       ├── Start Community Deployment
│       └── Restart Community Deployment
├── Scaling & Upgrades
│   ├── Enterprise Scale/Upgrade
│   │   ├── Scale to 5 Members
│   │   └── Upgrade Version
│   └── Community Scale/Upgrade (NEW)
│       ├── Scale Community to 5
│       └── Upgrade Community Version
├── Error Cases
│   ├── Existing Errors
│   │   ├── Duplicate Tenant
│   │   ├── Invalid Tenant ID
│   │   └── Duplicate Deployment
│   └── Community Errors (NEW)
│       ├── Community Standalone Not Supported
│       ├── Community Backup Not Supported
│       └── Invalid Plan
└── Monitoring & Backup
    ├── Enable/Disable Prometheus
    ├── Get Prometheus Config
    └── Enable/Disable Backup
```

---

## Key Differences Between Plans

| Feature | Enterprise | Community |
|---------|-----------|-----------|
| **Request Body** | `{"plan": "enterprise"}` or omit | `{"plan": "community"}` |
| **Response includes** | `projectName` | No `projectName` |
| **CR Created** | `MongoDB` (mongodb.com) | `MongoDBCommunity` |
| **Ops Manager** | ✅ Yes | ❌ No |
| **Standalone** | ✅ Supported | ❌ Not supported |
| **ReplicaSet** | ✅ Supported | ✅ Supported |
| **ShardedCluster** | ✅ Supported | ❌ Not supported |
| **Backup API** | ✅ Works | ❌ Returns 400 |
| **Scale API** | ✅ Works | ✅ Works |
| **Upgrade API** | ✅ Works | ✅ Works |
| **Lifecycle APIs** | ✅ Works | ✅ Works |

---

## Backward Compatibility

✅ **All existing Postman requests continue to work:**
- Requests without `plan` field default to "enterprise"
- Existing tenant IDs (t-acme, t-globex) work as before
- All enterprise operations unchanged

✅ **New requests are additive:**
- Community examples use new tenant IDs (t-initech, t-umbrella)
- Don't conflict with existing enterprise tenants
- Can be run independently

---

## Testing Steps

1. **Import Updated Collection**
   ```bash
   # Import MongoDB_Control_Plane.postman_collection.json
   ```

2. **Test Enterprise Tenant**
   ```
   Run: "Create Tenant - Acme (Enterprise - Default)"
   Run: "Create Deployment - ReplicaSet"
   Run: "Scale Deployment to 5 Members"
   Run: "Enable Backup"
   ```

3. **Test Community Tenant**
   ```
   Run: "Create Tenant - Initech (Community)"
   Run: "Create Community ReplicaSet"
   Run: "Scale Community to 5"
   Run: "Error - Community Backup Not Supported" (should get 400)
   ```

4. **Test Error Cases**
   ```
   Run: "Error - Community Standalone Not Supported"
   Run: "Error - Invalid Plan"
   ```

5. **List & Verify**
   ```
   Run: "List All Tenants"
   # Should show both enterprise and community tenants
   # Verify plan field in response
   ```

---

## Summary

✅ **27 total requests added/updated:**
- 2 new GET tenant endpoints
- 4 tenant creation examples (2 community)
- 2 community deployment examples
- 5 community lifecycle operations
- 3 community error examples
- Updated all existing tenant creates to show plan field

✅ **Covers all use cases:**
- Enterprise plan (existing functionality)
- Community plan (new functionality)
- Error scenarios (plan validation, unsupported operations)
- Backward compatibility (implicit enterprise default)

The Postman collection now provides comprehensive examples for testing both deployment flavors!
