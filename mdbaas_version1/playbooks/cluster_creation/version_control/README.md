# MongoDB Version Management Playbooks

Ansible playbooks for upgrading and downgrading MongoDB versions using Ops Manager automation.

---

## 📋 Table of Contents

1. [Playbooks Overview](#playbooks-overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Upgrade Process](#upgrade-process)
5. [Downgrade Process](#downgrade-process)
6. [Safety Features](#safety-features)
7. [Troubleshooting](#troubleshooting)
8. [Examples](#examples)

---

## Playbooks Overview

| Playbook | Purpose | Safety Level |
|----------|---------|--------------|
| `95_check_version.yml` | Check current version and FCV | ✅ Safe (read-only) |
| `90_upgrade_mongodb_version.yml` | Upgrade MongoDB version | ⚠️ Modifies deployment |
| `91_downgrade_mongodb_version.yml` | Downgrade MongoDB version | 🛑 High risk |

---

## Prerequisites

### 1. Environment Variables

All playbooks require these environment variables (from `.env` file):

```bash
# Ops Manager Configuration
export OPS_MANAGER_URL="https://your-ops-manager.com"
export OPS_MANAGER_PROJECT_ID="your-project-id"
export OPS_MANAGER_PUBLIC_KEY="your-public-key"
export OPS_MANAGER_PRIVATE_KEY="your-private-key"

# Version Management (for upgrade/downgrade)
export TARGET_MONGODB_VERSION="8.0.18-ent"  # Target version
```

### 2. Source Environment Variables

```bash
# From cluster_creation directory
source ../.env

# Or use absolute path
source /path/to/cluster_creation/.env
```

### 3. Inventory File

Use the inventory file from your deployment:

```bash
# For replica set
-i ../replica_set/inventory.ini

# For sharded cluster
-i ../sharded_cluster/inventory_sharded.yml

# For standalone
-i ../standalone/inventory_standalone.yml
```

---

## Quick Start

### Check Current Version

```bash
# 1. Source environment variables
cd /path/to/cluster_creation
source .env

# 2. Check version
cd version_control
ansible-playbook -i ../replica_set/inventory.ini 95_check_version.yml
```

### Upgrade MongoDB

```bash
# 1. Set target version
export TARGET_MONGODB_VERSION="8.0.18-ent"

# 2. Run upgrade
ansible-playbook -i ../replica_set/inventory.ini 90_upgrade_mongodb_version.yml

# 3. Monitor progress (wait 10-15 minutes)
ansible-playbook -i ../replica_set/inventory.ini 95_check_version.yml
```

### Downgrade MongoDB

```bash
# 1. Set FCV first (connect via mongosh)
mongosh --host <hostname> --port 27017
db.adminCommand({ setFeatureCompatibilityVersion: "8.0" })

# 2. Set target version
export TARGET_MONGODB_VERSION="8.0.15-ent"

# 3. Run downgrade
ansible-playbook -i ../replica_set/inventory.ini 91_downgrade_mongodb_version.yml

# 4. Monitor progress
ansible-playbook -i ../replica_set/inventory.ini 95_check_version.yml
```

---

## Upgrade Process

### Step-by-Step Upgrade

#### 1. Check Current Version

```bash
ansible-playbook -i ../replica_set/inventory.ini 95_check_version.yml
```

**Output Example:**
```
MongoDB Version Status
===========================================
Processes (3 total):
  1. rs0-01 (mongod)
     Version: 8.0.15-ent
     FCV:     8.0
```

#### 2. Set Target Version

```bash
# Choose target version (must be newer)
export TARGET_MONGODB_VERSION="8.0.18-ent"

# Or for major version upgrade
export TARGET_MONGODB_VERSION="9.0.0-ent"
```

#### 3. Run Upgrade Playbook

```bash
ansible-playbook -i ../replica_set/inventory.ini 90_upgrade_mongodb_version.yml
```

**What Happens:**
1. ✅ Validates version format
2. ✅ Checks current version
3. ✅ Confirms target is newer
4. ✅ Displays upgrade plan
5. ⏸️ Waits 15 seconds (Ctrl+C to abort)
6. 🚀 Submits upgrade to Ops Manager
7. ⏳ Monitors progress (10 minutes timeout)

#### 4. Monitor Progress

```bash
# Check every few minutes
ansible-playbook -i ../replica_set/inventory.ini 95_check_version.yml

# Or monitor in Ops Manager UI
# https://your-ops-manager.com/v2/project-id#/deployment
```

#### 5. Verify Completion

```bash
# All processes should show new version
ansible-playbook -i ../replica_set/inventory.ini 95_check_version.yml
```

**Expected Output:**
```
Automation Status:
  Goal Reached: ✅ Yes

Processes (3 total):
  1. rs0-01 (mongod)
     Version: 8.0.18-ent  ← Updated
     FCV:     8.0
```

---

## Downgrade Process

### ⚠️ Critical Pre-Downgrade Steps

**IMPORTANT**: Downgrade requires compatible Feature Compatibility Version (FCV)

#### 1. Check Current Version and FCV

```bash
ansible-playbook -i ../replica_set/inventory.ini 95_check_version.yml
```

#### 2. Set FCV to Target Version (REQUIRED)

```bash
# Connect to MongoDB
mongosh --host <hostname> --port 27017

# Check current FCV
db.adminCommand({ getParameter: 1, featureCompatibilityVersion: 1 })

# Set FCV to target version
db.adminCommand({ setFeatureCompatibilityVersion: "8.0" })

# Wait for FCV to be set (may take 5-10 minutes)
# Keep checking until FCV is updated
db.adminCommand({ getParameter: 1, featureCompatibilityVersion: 1 })
```

#### 3. Set Target Version

```bash
# Target version must be older than current
export TARGET_MONGODB_VERSION="8.0.15-ent"
```

#### 4. Run Downgrade Playbook

```bash
ansible-playbook -i ../replica_set/inventory.ini 91_downgrade_mongodb_version.yml
```

**What Happens:**
1. ✅ Validates version format
2. ✅ Checks current version and FCV
3. ✅ Confirms target is older
4. ⚠️ Warns about FCV compatibility
5. 🛑 Fails if FCV mismatch (unless skipped)
6. ⏸️ Waits 20 seconds (Ctrl+C to abort)
7. 🚀 Submits downgrade to Ops Manager
8. ⏳ Monitors progress (10 minutes timeout)

#### 5. Bypass FCV Check (NOT RECOMMENDED)

```bash
# Only if you're absolutely sure FCV is compatible
export SKIP_FCV_WARNING=true
ansible-playbook -i ../replica_set/inventory.ini 91_downgrade_mongodb_version.yml
```

---

## Safety Features

### Upgrade Safety

✅ **Version Validation**: Ensures target is newer  
✅ **Format Validation**: Checks version format (X.Y.Z-ent)  
✅ **Rolling Upgrade**: One node at a time  
✅ **Goal Monitoring**: Waits for stability  
✅ **FCV Auto-Update**: Updates to match target version  
✅ **15-Second Abort Window**: Press Ctrl+C to cancel  

### Downgrade Safety

🛑 **FCV Validation**: Requires compatible FCV  
🛑 **Direction Check**: Ensures target is older  
🛑 **Explicit Warnings**: Multiple warnings about risks  
🛑 **Rolling Downgrade**: One node at a time  
🛑 **20-Second Abort Window**: Longer time to cancel  
🛑 **FCV Bypass Option**: Requires explicit flag  

---

## Troubleshooting

### Issue: "Target version must be newer"

**Problem**: Trying to upgrade to older or same version

**Solution**:
```bash
# Check current version
ansible-playbook -i ../replica_set/inventory.ini 95_check_version.yml

# Use correct target version (must be newer)
export TARGET_MONGODB_VERSION="8.0.20-ent"
```

---

### Issue: "FCV mismatch detected"

**Problem**: FCV doesn't match target version for downgrade

**Solution**:
```bash
# 1. Connect to MongoDB
mongosh --host <hostname> --port 27017

# 2. Set FCV to match target version
db.adminCommand({ setFeatureCompatibilityVersion: "8.0" })

# 3. Wait for FCV update (5-10 minutes)

# 4. Verify FCV
db.adminCommand({ getParameter: 1, featureCompatibilityVersion: 1 })

# 5. Run downgrade again
ansible-playbook -i ../replica_set/inventory.ini 91_downgrade_mongodb_version.yml
```

---

### Issue: "Goal not reached" (timeout)

**Problem**: Upgrade/downgrade takes longer than 10 minutes

**Solution**:
```bash
# This is normal! The operation continues in background

# Check Ops Manager UI for real-time status
# https://your-ops-manager.com/v2/project-id#/deployment

# Wait 5 more minutes, then check version
ansible-playbook -i ../replica_set/inventory.ini 95_check_version.yml
```

---

### Issue: "Invalid version format"

**Problem**: Version string doesn't match expected format

**Solution**:
```bash
# ✅ Correct formats:
export TARGET_MONGODB_VERSION="8.0.18-ent"
export TARGET_MONGODB_VERSION="7.0.15-ent"
export TARGET_MONGODB_VERSION="8.0.18"

# ❌ Incorrect formats:
export TARGET_MONGODB_VERSION="8.0"          # Missing patch version
export TARGET_MONGODB_VERSION="v8.0.18-ent"  # Extra 'v' prefix
export TARGET_MONGODB_VERSION="8.0.18-ent-ubuntu"  # Extra suffixes
```

---

### Issue: "Authentication failed"

**Problem**: Ops Manager credentials invalid or expired

**Solution**:
```bash
# 1. Check .env file
cat ../.env | grep OPS_MANAGER

# 2. Re-source environment variables
source ../.env

# 3. Test API access
curl -u "$OPS_MANAGER_PUBLIC_KEY:$OPS_MANAGER_PRIVATE_KEY" \
  "$OPS_MANAGER_URL/api/public/v1.0/groups/$OPS_MANAGER_PROJECT_ID"

# 4. If still failing, regenerate API keys in Ops Manager
```

---

## Examples

### Example 1: Minor Version Upgrade (8.0.15 → 8.0.18)

```bash
# Check current version
ansible-playbook -i ../replica_set/inventory.ini 95_check_version.yml
# Output: Version 8.0.15-ent, FCV 8.0

# Set target version
export TARGET_MONGODB_VERSION="8.0.18-ent"

# Run upgrade
ansible-playbook -i ../replica_set/inventory.ini 90_upgrade_mongodb_version.yml
# Wait 10-15 minutes

# Verify completion
ansible-playbook -i ../replica_set/inventory.ini 95_check_version.yml
# Output: Version 8.0.18-ent, FCV 8.0
```

---

### Example 2: Major Version Upgrade (8.0.18 → 9.0.0)

```bash
# Check current version
ansible-playbook -i ../replica_set/inventory.ini 95_check_version.yml
# Output: Version 8.0.18-ent, FCV 8.0

# Set target version (major upgrade)
export TARGET_MONGODB_VERSION="9.0.0-ent"

# Run upgrade
ansible-playbook -i ../replica_set/inventory.ini 90_upgrade_mongodb_version.yml
# Wait 15-20 minutes (major upgrades take longer)

# Verify completion
ansible-playbook -i ../replica_set/inventory.ini 95_check_version.yml
# Output: Version 9.0.0-ent, FCV 9.0

# Note: FCV automatically updated to 9.0
```

---

### Example 3: Downgrade with FCV Change (8.0.18 → 8.0.15)

```bash
# Check current version
ansible-playbook -i ../replica_set/inventory.ini 95_check_version.yml
# Output: Version 8.0.18-ent, FCV 8.0

# FCV already matches (8.0), no need to change

# Set target version (older)
export TARGET_MONGODB_VERSION="8.0.15-ent"

# Run downgrade
ansible-playbook -i ../replica_set/inventory.ini 91_downgrade_mongodb_version.yml
# Wait 10-15 minutes

# Verify completion
ansible-playbook -i ../replica_set/inventory.ini 95_check_version.yml
# Output: Version 8.0.15-ent, FCV 8.0
```

---

### Example 4: Downgrade Requires FCV Change (9.0.0 → 8.0.18)

```bash
# Check current version
ansible-playbook -i ../replica_set/inventory.ini 95_check_version.yml
# Output: Version 9.0.0-ent, FCV 9.0

# FCV mismatch! Must change to 8.0 first

# 1. Connect to MongoDB
mongosh --host ip-172-31-16-76 --port 27017

# 2. Set FCV to 8.0
db.adminCommand({ setFeatureCompatibilityVersion: "8.0" })
# { ok: 1 }

# 3. Wait 5-10 minutes for FCV update

# 4. Verify FCV changed
ansible-playbook -i ../replica_set/inventory.ini 95_check_version.yml
# Output: Version 9.0.0-ent, FCV 8.0 ✅

# 5. Set target version
export TARGET_MONGODB_VERSION="8.0.18-ent"

# 6. Run downgrade
ansible-playbook -i ../replica_set/inventory.ini 91_downgrade_mongodb_version.yml
# Wait 15-20 minutes

# 7. Verify completion
ansible-playbook -i ../replica_set/inventory.ini 95_check_version.yml
# Output: Version 8.0.18-ent, FCV 8.0
```

---

### Example 5: Upgrade Sharded Cluster

```bash
# Use sharded cluster inventory
export TARGET_MONGODB_VERSION="8.0.18-ent"

ansible-playbook -i ../sharded_cluster/inventory_sharded.yml 90_upgrade_mongodb_version.yml

# This will upgrade:
# - All config servers (3)
# - All shard nodes (3)
# - All mongos routers (2)
# Total: 8 processes upgraded

# Wait 20-30 minutes for completion
```

---

## Version Compatibility Matrix

| Current | Target Upgrade | Supported | FCV Change Required |
|---------|----------------|-----------|---------------------|
| 8.0.15  | 8.0.18        | ✅ Yes    | No (auto-updated)   |
| 8.0.15  | 9.0.0         | ✅ Yes    | No (auto-updated)   |
| 9.0.0   | 8.0.18        | ⚠️ Downgrade | Yes (set to 8.0 first) |
| 8.0.18  | 8.0.15        | ⚠️ Downgrade | No (already 8.0)    |
| 8.0.18  | 7.0.15        | ⚠️ Downgrade | Yes (set to 7.0 first) |

---

## Best Practices

### Before Upgrade
1. ✅ Backup your data
2. ✅ Check current version and FCV
3. ✅ Review MongoDB release notes
4. ✅ Test in non-production environment first
5. ✅ Schedule during maintenance window

### Before Downgrade
1. 🛑 **Critical**: Set FCV to target version first
2. 🛑 Backup your data (mandatory!)
3. 🛑 Review features used (may be lost)
4. 🛑 Test in non-production environment
5. 🛑 Get approval from team/management

### During Upgrade/Downgrade
- Monitor Ops Manager UI
- Check application connections remain stable
- Watch for errors in MongoDB logs
- Keep terminal open to see progress

### After Upgrade/Downgrade
- Verify all processes show correct version
- Test application functionality
- Check MongoDB logs for errors
- Update documentation with new version

---

## Related Documentation

- **Replica Set Operations**: `../replica_set/OPERATIONS_GUIDE.md`
- **Deployment Guide**: `../replica_set/DEPLOYMENT_GUIDE.md`
- **Sharded Cluster**: `../sharded_cluster/README.md`
- **Monitoring**: `../monitoring/80_configure_prometheus.yml`

---

## Support

For issues or questions:
1. Check Ops Manager UI for deployment status
2. Review MongoDB logs on VMs
3. Check Ops Manager agent logs
4. Refer to MongoDB documentation for version-specific issues

---

**Remember**: Always test version changes in non-production environments first! 🚀
