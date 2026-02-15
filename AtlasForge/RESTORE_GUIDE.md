# Community MongoDB Backup Restore Guide

## Overview

The MDBaaS Control Plane provides automated restore functionality for Community MongoDB deployments. Users can select any snapshot and restore their database with a single click.

---

## How Restore Works

### Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  User       │────▶│  Backend API │────▶│  Kubernetes Job │
│  (UI/API)   │     │  (FastAPI)   │     │  (Restore Pod)  │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                    │
                    ┌───────────────────────────────┤
                    │                               │
              ┌─────▼─────┐                  ┌──────▼──────┐
              │  S3 or    │                  │   MongoDB   │
              │  NFS/EFS  │                  │  Deployment │
              │  Storage  │                  │             │
              └───────────┘                  └─────────────┘
```

### Restore Flow

1. **User Selection**
   - User browses snapshots in UI
   - Clicks "Restore" button on desired snapshot
   - Confirms restore operation (warning about data loss)

2. **Job Creation**
   - Backend creates Kubernetes Job with unique name: `{deployment}-restore-{timestamp}`
   - Job configured with:
     - Backup credentials (from existing backup user)
     - MongoDB connection URI (NodePort external access)
     - Snapshot filename
     - Drop existing flag (optional)

3. **Download Backup**
   - **S3**: Downloads `.tar.gz` from S3, extracts to `/tmp`
   - **Filesystem**: Uses mounted NFS/EFS volume

4. **Restore Execution**
   - Runs `mongorestore` with discovered dump directory
   - Optional `--drop` flag to remove existing collections
   - Connects via external NodePort URI

5. **Completion**
   - Job succeeds or fails
   - Logs available via `kubectl logs`
   - Metadata stored in deployment record

---

## API Endpoints

### 1. Restore Backup

**POST** `/tenants/{tenantId}/deployments/{deploymentId}/community-backup/restore`

Creates a Kubernetes Job to restore from a snapshot.

**Request Body:**
```json
{
  "snapshotFilename": "dump-20260215-120000.tar.gz",
  "dropExisting": true
}
```

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

**Parameters:**
- `snapshotFilename` (required): Exact filename from snapshot list
- `dropExisting` (optional, default: `true`): Drop existing collections before restore

### 2. Get Restore Job Status

**GET** `/tenants/{tenantId}/deployments/{deploymentId}/community-backup/restore/{jobName}`

Returns status and logs of a restore job.

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
- `PENDING`: Job created but pod not started yet
- `RUNNING`: Restore in progress
- `COMPLETED`: Restore successful
- `FAILED`: Restore failed (check logs)

---

## Restore Options

### Drop Existing Collections (`dropExisting`)

#### `dropExisting: true` (Recommended)
- **What happens**: Removes existing collections before restore
- **Use case**: Clean restore, ensure data consistency
- **Behavior**: `mongorestore --drop ...`
- **Risk**: Data loss if not backed up

#### `dropExisting: false`
- **What happens**: Merges with existing data
- **Use case**: Partial restore, data merge
- **Behavior**: `mongorestore ...` (no --drop)
- **Risk**: Duplicate keys, conflicts

---

## Usage Examples

### Via UI

1. **Navigate to Backup Tab**
   - Go to deployment details
   - Click "Backup" tab

2. **View Snapshots**
   - Scroll to "Backup Snapshots" section
   - Snapshots listed with timestamp and size

3. **Restore Snapshot**
   - Click "Restore" button on desired snapshot
   - Review warning modal
   - Confirm drop existing (or uncheck)
   - Click "Restore Backup"

4. **Monitor Progress**
   - Refresh page to see updated status
   - Or check Kubernetes logs:
     ```bash
     kubectl logs -f job/{job-name} -n {namespace}
     ```

### Via API (Postman/Curl)

```bash
# 1. List snapshots
curl -X GET http://localhost:8001/tenants/test-community/deployments/rs-test/community-backup/status

# Response includes snapshots array:
# "snapshots": [
#   {
#     "filename": "dump-20260215-120000.tar.gz",
#     "timestamp": "2026-02-15 12:00:00",
#     "sizeFormatted": "2.3 MB"
#   }
# ]

# 2. Start restore
curl -X POST http://localhost:8001/tenants/test-community/deployments/rs-test/community-backup/restore \
  -H "Content-Type: application/json" \
  -d '{
    "snapshotFilename": "dump-20260215-120000.tar.gz",
    "dropExisting": true
  }'

# Response:
# {
#   "jobName": "rs-test-restore-20260215143022",
#   "status": "RUNNING",
#   "checkStatusCommand": "kubectl logs -f job/rs-test-restore-20260215143022 -n mdb-test-community"
# }

# 3. Check job status
curl -X GET http://localhost:8001/tenants/test-community/deployments/rs-test/community-backup/restore/rs-test-restore-20260215143022

# 4. Monitor via kubectl
kubectl logs -f job/rs-test-restore-20260215143022 -n mdb-test-community
```

---

## Kubernetes Job Details

### S3 Restore Job

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: rs-test-restore-20260215143022
  namespace: mdb-test-community
spec:
  template:
    spec:
      serviceAccountName: rs-test-backup
      restartPolicy: Never
      containers:
      - name: restore
        image: mongo:8.0
        command:
        - /bin/sh
        - -c
        - |
          set -e
          echo "[RESTORE] Starting restore from S3..."
          
          # Download from S3
          aws s3 cp s3://bucket/prefix/snapshots/dump-20260215-120000.tar.gz /tmp/
          
          # Extract
          cd /tmp && tar -xzf dump-20260215-120000.tar.gz
          
          # Find dump directory
          DUMP_DIR=$(find /tmp -type d -name "dump-*" | head -n 1)
          
          # Restore
          mongorestore --uri="mongodb://user:pass@host:port/admin" --drop --dir="$DUMP_DIR"
          
          echo "[RESTORE] Restore completed successfully!"
        env:
        - name: AWS_ACCESS_KEY_ID
          valueFrom:
            secretKeyRef:
              name: aws-backup-credentials
              key: AWS_ACCESS_KEY_ID
        - name: AWS_SECRET_ACCESS_KEY
          valueFrom:
            secretKeyRef:
              name: aws-backup-credentials
              key: AWS_SECRET_ACCESS_KEY
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 2
            memory: 2Gi
  backoffLimit: 2
  ttlSecondsAfterFinished: 86400  # Clean up after 24 hours
```

### Filesystem Restore Job

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: rs-prod-restore-20260215143022
  namespace: mdb-umbrella
spec:
  template:
    spec:
      serviceAccountName: rs-prod-backup
      restartPolicy: Never
      containers:
      - name: restore
        image: mongo:8.0
        command:
        - /bin/sh
        - -c
        - |
          set -e
          echo "[RESTORE] Starting restore from filesystem..."
          
          BACKUP_FILE="/backup/dump-20260215-020000.gz"
          
          mongorestore --uri="mongodb://user:pass@host:port/admin" --drop --gzip --archive="$BACKUP_FILE"
          
          echo "[RESTORE] Restore completed successfully!"
        volumeMounts:
        - name: backup-volume
          mountPath: /backup
      volumes:
      - name: backup-volume
        nfs:
          server: 10.0.0.10
          path: /mnt/backups/rs-prod
  backoffLimit: 2
  ttlSecondsAfterFinished: 86400
```

---

## Monitoring Restore Progress

### Check Job Status

```bash
# List restore jobs
kubectl get jobs -n mdb-test-community | grep restore

# Get job details
kubectl describe job rs-test-restore-20260215143022 -n mdb-test-community

# Check pod status
kubectl get pods -n mdb-test-community | grep restore
```

### View Logs

```bash
# Follow logs (live)
kubectl logs -f job/rs-test-restore-20260215143022 -n mdb-test-community

# Get last 100 lines
kubectl logs job/rs-test-restore-20260215143022 -n mdb-test-community --tail=100

# Get logs from failed job
kubectl logs job/rs-test-restore-20260215143022 -n mdb-test-community --previous
```

### Example Log Output

```
[RESTORE] Starting restore from S3: s3://mdbaas-backups/community/snapshots/dump-20260215-120000.tar.gz
[RESTORE] Downloading backup...
download: s3://mdbaas-backups/community/snapshots/dump-20260215-120000.tar.gz to ./dump-20260215-120000.tar.gz
[RESTORE] Extracting backup...
[RESTORE] Found dump directory: /tmp/dump-20260215-120000
[RESTORE] Running mongorestore...
2026-02-15T14:32:15.123+0000	preparing collections to restore from
2026-02-15T14:32:15.456+0000	reading metadata for appdb.users from /tmp/dump-20260215-120000/appdb/users.metadata.json
2026-02-15T14:32:15.789+0000	restoring appdb.users from /tmp/dump-20260215-120000/appdb/users.bson
2026-02-15T14:32:18.234+0000	finished restoring appdb.users (15234 documents, 0 failures)
2026-02-15T14:32:18.567+0000	restoring indexes for collection appdb.users from metadata
2026-02-15T14:32:19.123+0000	15234 document(s) restored successfully. 0 document(s) failed to restore.
[RESTORE] Restore completed successfully!
```

---

## Troubleshooting

### Job Fails to Start

**Symptom**: Job stays in PENDING state

**Causes**:
- ServiceAccount missing: `rs-test-backup` not found
- Backup credentials secret missing: `rs-test-backup-credentials`
- Insufficient resources on cluster

**Solution**:
```bash
# Check if backup is enabled
curl http://localhost:8001/tenants/{tenant}/deployments/{deployment}/community-backup/status

# Verify ServiceAccount exists
kubectl get sa rs-test-backup -n mdb-test-community

# Verify secret exists
kubectl get secret rs-test-backup-credentials -n mdb-test-community
```

### Download Fails (S3)

**Symptom**: `NoSuchKey` or `Access Denied` in logs

**Causes**:
- Snapshot file doesn't exist
- AWS credentials invalid
- S3 bucket permissions incorrect

**Solution**:
```bash
# Verify snapshot exists
aws s3 ls s3://bucket/prefix/snapshots/

# Test AWS credentials from pod
kubectl run test --rm -it --image=amazon/aws-cli:latest \
  --overrides='{"spec":{"serviceAccountName":"rs-test-backup"}}' \
  -- s3 ls s3://bucket/prefix/snapshots/
```

### mongorestore Fails

**Symptom**: `connection refused` or `authentication failed`

**Causes**:
- MongoDB connection URI incorrect
- Backup user credentials expired
- NodePort service not accessible

**Solution**:
```bash
# Get backup credentials
kubectl get secret rs-test-backup-credentials -n mdb-test-community -o yaml

# Decode MongoDB URI
kubectl get secret rs-test-backup-credentials -n mdb-test-community \
  -o jsonpath='{.data.mongodbUri}' | base64 -d

# Test connection
kubectl run test --rm -it --image=mongo:8.0 -- \
  mongosh "mongodb://user:pass@external-ip:nodeport/admin"
```

### Duplicate Key Errors

**Symptom**: `E11000 duplicate key error` in logs

**Causes**:
- `dropExisting: false` and data already exists
- Restoring to wrong database

**Solution**:
- Re-run with `dropExisting: true`
- Or manually clear collections before restore

---

## Best Practices

### Before Restore

1. **Create Fresh Backup**: Always backup current state before restoring
2. **Verify Snapshot**: Ensure snapshot is from correct point-in-time
3. **Check Disk Space**: Verify sufficient space for extraction
4. **Stop Application Writes**: Prevent data conflicts during restore

### During Restore

1. **Monitor Logs**: Watch job logs for errors
2. **Check Resource Usage**: Ensure cluster has capacity
3. **Wait for Completion**: Don't interrupt restore job

### After Restore

1. **Verify Data**: Check database contents are correct
2. **Test Application**: Ensure application works with restored data
3. **Clean Up**: Job auto-deletes after 24 hours
4. **Update Documentation**: Record restore event for audit

---

## Security Considerations

1. **Backup User Permissions**: Restore uses backup user with admin roles
2. **Secret Management**: MongoDB URI stored in Kubernetes Secret
3. **Network Access**: Restore pod needs NodePort access to MongoDB
4. **Audit Trail**: Restore metadata stored in control plane database

---

## Limitations

1. **Community Only**: Restore only available for Community deployments
2. **S3 Snapshots Only**: Snapshot listing only works for S3 backups
3. **No Point-in-Time**: Snapshot-based, not continuous backup
4. **Downtime**: Brief application downtime during restore
5. **No Rollback**: Restore is destructive if `dropExisting: true`

---

## Future Enhancements

- [ ] Point-in-time restore
- [ ] Restore to different deployment
- [ ] Dry-run mode
- [ ] Restore validation before commit
- [ ] Automatic rollback on failure
- [ ] Restore progress percentage
- [ ] Email notifications on completion

---

**Built with ❤️ for MongoDB-as-a-Service providers**
