# MDBaaS Control Plane - Complete API Reference

## Base URL

```
http://localhost:8001
```

For production, replace with your deployed backend URL.

---

## API Categories

1. [Health & System](#health--system)
2. [Tenants](#tenants)
3. [Deployments](#deployments)
4. [Lifecycle Management](#lifecycle-management)
5. [Scaling & Versioning](#scaling--versioning)
6. [Monitoring (Prometheus)](#monitoring-prometheus)
7. [Backup (Enterprise)](#backup-enterprise)
8. [Backup (Community)](#backup-community)
9. [Database Users](#database-users)
10. [Connection Info](#connection-info)

---

## Health & System

### Health Check
```
GET /health
```

**Response:**
```json
{
  "status": "healthy"
}
```

---

## Tenants

### List All Tenants
```
GET /tenants
```

**Response:**
```json
[
  {
    "tenantId": "t-acme",
    "displayName": "Acme Corporation",
    "plan": "enterprise",
    "namespace": "mdb-t-acme",
    "createdAt": "2026-02-15T10:00:00Z"
  }
]
```

### Get Tenant by ID
```
GET /tenants/{tenantId}
```

**Response:**
```json
{
  "tenantId": "t-acme",
  "displayName": "Acme Corporation",
  "plan": "enterprise",
  "namespace": "mdb-t-acme",
  "createdAt": "2026-02-15T10:00:00Z"
}
```

### Create Tenant
```
POST /tenants
```

**Request Body:**
```json
{
  "tenantId": "t-acme",
  "displayName": "Acme Corporation",
  "plan": "enterprise"
}
```

**Plan Options:** `enterprise` | `community`

**Response:**
```json
{
  "tenantId": "t-acme",
  "displayName": "Acme Corporation",
  "plan": "enterprise",
  "namespace": "mdb-t-acme",
  "message": "Tenant created successfully"
}
```

### Delete Tenant
```
DELETE /tenants/{tenantId}
```

**Response:** `204 No Content`

---

## Deployments

### List Deployments for Tenant
```
GET /tenants/{tenantId}/deployments
```

**Response:**
```json
[
  {
    "deploymentId": "rs-orders",
    "type": "ReplicaSet",
    "mongoVersion": "8.0.3",
    "members": 3,
    "status": "Running",
    "environment": "prod"
  }
]
```

### Get Deployment Details
```
GET /tenants/{tenantId}/deployments/{deploymentId}
```

**Response:**
```json
{
  "deploymentId": "rs-orders",
  "type": "ReplicaSet",
  "mongoVersion": "8.0.3",
  "members": 3,
  "status": "Running",
  "environment": "prod",
  "displayName": "Orders Database",
  "createdAt": "2026-02-15T10:30:00Z"
}
```

### Create Deployment - ReplicaSet
```
POST /tenants/{tenantId}/deployments
```

**Request Body (Enterprise):**
```json
{
  "deploymentId": "rs-orders",
  "type": "ReplicaSet",
  "mongoVersion": "8.0.3",
  "members": 3,
  "displayName": "Orders Database",
  "environment": "prod"
}
```

**Request Body (Community):**
```json
{
  "deploymentId": "rs-test",
  "type": "ReplicaSet",
  "mongoVersion": "8.0.3",
  "members": 3,
  "displayName": "Community Test DB",
  "environment": "dev"
}
```

**Type Options:** `ReplicaSet` | `ShardedCluster` | `Standalone` (Enterprise only)

**Members:** `3`, `5`, `7` (odd numbers recommended)

**Environment:** `dev` | `test` | `staging` | `prod`

### Create Deployment - Sharded Cluster
```
POST /tenants/{tenantId}/deployments
```

**Request Body:**
```json
{
  "deploymentId": "sc-orders",
  "type": "ShardedCluster",
  "mongoVersion": "8.0.3",
  "shardCount": 2,
  "mongodsPerShardCount": 3,
  "mongosCount": 2,
  "configServerCount": 3,
  "displayName": "Orders Sharded Cluster",
  "environment": "prod"
}
```

### Delete Deployment
```
DELETE /tenants/{tenantId}/deployments/{deploymentId}
```

**Response:** `204 No Content`

---

## Lifecycle Management

### Shutdown Deployment
```
POST /tenants/{tenantId}/deployments/{deploymentId}/actions/shutdown
```

**Response:**
```json
{
  "message": "Shutdown initiated",
  "deploymentId": "rs-orders"
}
```

### Start Deployment
```
POST /tenants/{tenantId}/deployments/{deploymentId}/actions/start
```

**Response:**
```json
{
  "message": "Start initiated",
  "deploymentId": "rs-orders"
}
```

### Restart Deployment
```
POST /tenants/{tenantId}/deployments/{deploymentId}/actions/restart
```

**Response:**
```json
{
  "message": "Restart initiated",
  "deploymentId": "rs-orders"
}
```

---

## Scaling & Versioning

### Scale Deployment
```
PATCH /tenants/{tenantId}/deployments/{deploymentId}/scale
```

**Request Body:**
```json
{
  "members": 5
}
```

**Valid Members:** `3`, `5`, `7` (odd numbers for proper election quorum)

**Response:**
```json
{
  "message": "Scaling to 5 members",
  "deploymentId": "rs-orders",
  "previousMembers": 3,
  "newMembers": 5
}
```

### Upgrade MongoDB Version
```
PATCH /tenants/{tenantId}/deployments/{deploymentId}/version
```

**Request Body:**
```json
{
  "mongoVersion": "8.0.4"
}
```

**Response:**
```json
{
  "message": "Version upgrade initiated",
  "deploymentId": "rs-orders",
  "previousVersion": "8.0.3",
  "newVersion": "8.0.4"
}
```

---

## Monitoring (Prometheus)

### Enable Prometheus Monitoring
```
PATCH /tenants/{tenantId}/deployments/{deploymentId}/monitoring/prometheus
```

**Request Body:**
```json
{
  "enabled": true
}
```

**Response:**
```json
{
  "enabled": true,
  "message": "Prometheus monitoring enabled"
}
```

### Get Prometheus Config
```
GET /tenants/{tenantId}/deployments/{deploymentId}/monitoring/prometheus
```

**Response:**
```json
{
  "enabled": true,
  "prometheusUser": "prometheus"
}
```

### Get Prometheus Scrape Config
```
GET /tenants/{tenantId}/deployments/{deploymentId}/monitoring/prometheus/config
```

**Response:**
```json
{
  "jobName": "mongo-rs-orders",
  "metricsPath": "/metrics",
  "username": "prometheus-user",
  "passwordMasked": "***************123",
  "targets": ["172.31.23.201:31586"],
  "labels": {
    "app": "mongo-rs-orders"
  },
  "workerNodeIps": [
    "172.31.23.201",
    "172.31.22.150",
    "172.31.25.88"
  ],
  "nodePort": 31586,
  "canRevealPassword": true
}
```

### Reveal Prometheus Password (One-Time)
```
POST /tenants/{tenantId}/deployments/{deploymentId}/monitoring/prometheus/reveal
```

**Response:**
```json
{
  "username": "prometheus-user",
  "password": "SuperSecretPass123"
}
```

**Note:** Password can only be revealed once. After revealing, `canRevealPassword` becomes `false`.

### Rotate Prometheus Password
```
POST /tenants/{tenantId}/deployments/{deploymentId}/monitoring/prometheus/rotate
```

**Response:**
```json
{
  "message": "Password rotated successfully. You can now reveal the new password once.",
  "passwordVersion": 2
}
```

---

## Backup (Enterprise)

### Enable/Disable Backup
```
PATCH /tenants/{tenantId}/deployments/{deploymentId}/backup
```

**Request Body:**
```json
{
  "enabled": true
}
```

**Response:**
```json
{
  "enabled": true,
  "message": "Backup enabled successfully"
}
```

### Get Backup Status
```
GET /tenants/{tenantId}/deployments/{deploymentId}/backup/status
```

**Response:**
```json
{
  "enabled": true,
  "status": "ACTIVE",
  "lastBackupTime": "2026-02-15T12:00:00Z"
}
```

### List Backup Snapshots
```
GET /tenants/{tenantId}/deployments/{deploymentId}/backup/snapshots
```

**Response:**
```json
{
  "snapshots": [
    {
      "id": "snapshot-123",
      "timestamp": "2026-02-15T12:00:00Z",
      "size": "2.3 GB",
      "type": "SCHEDULED"
    }
  ]
}
```

### Trigger Backup Snapshot
```
POST /tenants/{tenantId}/deployments/{deploymentId}/backup/snapshotNow
```

**Response:**
```json
{
  "message": "Snapshot triggered",
  "snapshotId": "snapshot-124"
}
```

---

## Backup (Community)

### Get Community Backup Status
```
GET /tenants/{tenantId}/deployments/{deploymentId}/community-backup/status
```

**Response (S3):**
```json
{
  "enabled": true,
  "type": "s3",
  "status": "ACTIVE",
  "schedule": "0 */4 * * *",
  "lastSuccessfulTime": "2026-02-15T12:00:00Z",
  "s3Bucket": "mdbaas-community-mongodb-backups",
  "s3Prefix": "community-mongodb-backup",
  "s3Region": "us-east-1",
  "s3Path": "s3://mdbaas-community-mongodb-backups/community-mongodb-backup/snapshots",
  "retentionDays": 7,
  "snapshots": [
    {
      "filename": "dump-20260215-120000.tar.gz",
      "size": 2412345,
      "sizeFormatted": "2.3 MB",
      "lastModified": "2026-02-15T12:00:00Z",
      "timestamp": "2026-02-15 12:00:00",
      "s3Key": "community-mongodb-backup/snapshots/dump-20260215-120000.tar.gz",
      "s3Uri": "s3://mdbaas-community-mongodb-backups/community-mongodb-backup/snapshots/dump-20260215-120000.tar.gz"
    }
  ]
}
```

**Response (Filesystem):**
```json
{
  "enabled": true,
  "type": "filesystem",
  "status": "ACTIVE",
  "schedule": "0 2 * * *",
  "lastSuccessfulTime": "2026-02-15T02:00:00Z",
  "target": "10.0.0.10:/mnt/backups/rs-test",
  "retentionDays": 14,
  "snapshots": []
}
```

### Enable Community Backup - S3
```
PATCH /tenants/{tenantId}/deployments/{deploymentId}/community-backup
```

**Request Body:**
```json
{
  "enabled": true,
  "type": "s3",
  "s3Bucket": "mdbaas-community-mongodb-backups",
  "s3Prefix": "community-mongodb-backup",
  "s3Region": "us-east-1",
  "schedule": "0 */4 * * *",
  "retentionDays": 7
}
```

**Cron Schedule Examples:**
- `0 */4 * * *` - Every 4 hours
- `0 2 * * *` - Daily at 2 AM
- `0 0 * * 0` - Weekly on Sunday

**Response:**
```json
{
  "message": "Community backup enabled successfully",
  "type": "s3",
  "schedule": "0 */4 * * *",
  "s3Path": "s3://mdbaas-community-mongodb-backups/community-mongodb-backup/snapshots"
}
```

### Enable Community Backup - Filesystem
```
PATCH /tenants/{tenantId}/deployments/{deploymentId}/community-backup
```

**Request Body:**
```json
{
  "enabled": true,
  "type": "filesystem",
  "filesystem": {
    "backupHost": "10.0.0.10",
    "backupPath": "/mnt/backups",
    "subDirectory": "rs-test"
  },
  "schedule": "0 2 * * *",
  "retentionDays": 14
}
```

**Response:**
```json
{
  "message": "Community backup enabled successfully",
  "type": "filesystem",
  "schedule": "0 2 * * *",
  "target": "10.0.0.10:/mnt/backups/rs-test"
}
```

### Disable Community Backup
```
PATCH /tenants/{tenantId}/deployments/{deploymentId}/community-backup
```

**Request Body:**
```json
{
  "enabled": false
}
```

**Response:**
```json
{
  "message": "Community backup disabled successfully"
}
```

### Restore Community Backup
```
POST /tenants/{tenantId}/deployments/{deploymentId}/community-backup/restore
```

**Request Body:**
```json
{
  "snapshotFilename": "dump-20260215-120000.tar.gz",
  "dropExisting": true
}
```

**Parameters:**
- `snapshotFilename` (required): Filename from snapshot list
- `dropExisting` (optional, default: `true`): Drop existing collections before restore

**Response:**
```json
{
  "message": "Restore job created successfully",
  "jobName": "rs-test-restore-20260215143022",
  "namespace": "mdb-test-community",
  "snapshot": "dump-20260215-120000.tar.gz",
  "dropExisting": true,
  "status": "RUNNING",
  "checkStatusCommand": "kubectl logs -f job/rs-test-restore-20260215143022 -n mdb-test-community"
}
```

### Get Restore Job Status
```
GET /tenants/{tenantId}/deployments/{deploymentId}/community-backup/restore/{jobName}
```

**Response:**
```json
{
  "jobName": "rs-test-restore-20260215143022",
  "namespace": "mdb-test-community",
  "status": "COMPLETED",
  "succeeded": 1,
  "failed": 0,
  "active": 0,
  "startTime": "2026-02-15T14:30:22Z",
  "completionTime": "2026-02-15T14:35:10Z",
  "logs": "[RESTORE] Starting restore from S3...\n[RESTORE] Downloading backup...\n[RESTORE] Running mongorestore...\n[RESTORE] Restore completed successfully!"
}
```

**Status Values:**
- `PENDING`: Job created, not started
- `RUNNING`: Restore in progress
- `COMPLETED`: Restore successful
- `FAILED`: Restore failed (check logs)

---

## Database Users

### Create Database User
```
POST /tenants/{tenantId}/deployments/{deploymentId}/users
```

**Request Body:**
```json
{
  "username": "appUser",
  "db": "appdb",
  "roles": [
    {"db": "appdb", "name": "readWrite"},
    {"db": "admin", "name": "clusterMonitor"}
  ]
}
```

**Database Roles:**
- `read`, `readWrite`, `dbAdmin`, `userAdmin`, `dbOwner`

**Admin Roles (admin db only):**
- `readAnyDatabase`, `readWriteAnyDatabase`, `userAdminAnyDatabase`
- `dbAdminAnyDatabase`, `clusterAdmin`, `clusterMonitor`
- `backup`, `restore`, `root`

**Response:**
```json
{
  "username": "appUser",
  "db": "appdb",
  "password": "auto-generated-password",
  "roles": [
    {"db": "appdb", "name": "readWrite"},
    {"db": "admin", "name": "clusterMonitor"}
  ],
  "createdAt": "2026-02-15T10:30:00Z",
  "connectionUri": "mongodb://appUser:password@host:port/appdb"
}
```

**Note:** Password is only returned on creation. Store it securely.

### List Database Users
```
GET /tenants/{tenantId}/deployments/{deploymentId}/users
```

**Response:**
```json
[
  {
    "username": "appUser",
    "db": "appdb",
    "roles": [
      {"db": "appdb", "name": "readWrite"},
      {"db": "admin", "name": "clusterMonitor"}
    ],
    "createdAt": "2026-02-15T10:30:00Z"
  }
]
```

### Get User Connection Info
```
GET /tenants/{tenantId}/deployments/{deploymentId}/users/{username}/connection
```

**Response:**
```json
{
  "username": "appUser",
  "db": "appdb",
  "roles": [
    {"db": "appdb", "name": "readWrite"},
    {"db": "admin", "name": "clusterMonitor"}
  ],
  "externalUri": "mongodb://appUser:password@external-ip:32456/appdb",
  "internalUri": "mongodb://appUser:password@rs-orders-svc.mdb-t-acme.svc.cluster.local:27017/appdb"
}
```

### Update User Roles
```
PATCH /tenants/{tenantId}/deployments/{deploymentId}/users/{username}
```

**Request Body:**
```json
{
  "roles": [
    {"db": "appdb", "name": "readWrite"},
    {"db": "appdb", "name": "dbAdmin"},
    {"db": "admin", "name": "clusterMonitor"}
  ]
}
```

**Response:**
```json
{
  "username": "appUser",
  "db": "appdb",
  "roles": [
    {"db": "appdb", "name": "readWrite"},
    {"db": "appdb", "name": "dbAdmin"},
    {"db": "admin", "name": "clusterMonitor"}
  ],
  "updatedAt": "2026-02-15T11:00:00Z"
}
```

### Delete Database User
```
DELETE /tenants/{tenantId}/deployments/{deploymentId}/users/{username}
```

**Response:**
```json
{
  "message": "User deleted successfully",
  "username": "appUser"
}
```

---

## Connection Info

### Get Deployment Connection Info
```
GET /tenants/{tenantId}/deployments/{deploymentId}/connection
```

**Response:**
```json
{
  "deploymentId": "rs-orders",
  "externalUri": "mongodb://external-ip:32456/?replicaSet=rs-orders",
  "internalUri": "mongodb://rs-orders-svc.mdb-t-acme.svc.cluster.local:27017/?replicaSet=rs-orders",
  "hosts": [
    "external-ip:32456"
  ],
  "nodePort": 32456
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid tenant ID format"
}
```

### 404 Not Found
```json
{
  "detail": "Tenant t-nonexistent not found"
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
  "detail": "Internal error: Connection to MongoDB failed"
}
```

---

## Postman Collection

Import the complete Postman collection:
```
AtlasForge/MongoDB_Control_Plane.postman_collection.json
```

**Collection includes:**
- 65+ API endpoints
- Example requests for all operations
- Environment variable setup (baseUrl)
- Request bodies with examples
- Enterprise and Community examples

**Quick Import:**
1. Open Postman
2. Click Import
3. Select `MongoDB_Control_Plane.postman_collection.json`
4. Set `baseUrl` variable to your backend URL

---

## Rate Limits

Currently no rate limits enforced. For production, consider implementing:
- Rate limiting middleware
- API key authentication
- Request throttling

---

## Authentication

Currently no authentication required. For production, implement:
- JWT tokens
- OAuth2
- API keys
- RBAC (Role-Based Access Control)

---

## API Versioning

Current version: `v1` (implicit)

Future versions will use URL prefix:
- `v1`: `/tenants`
- `v2`: `/v2/tenants`

---

**Built with ❤️ for MongoDB-as-a-Service providers**
