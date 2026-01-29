# Version Management Quick Reference

One-page quick reference for MongoDB version management.

---

## 🚀 Quick Commands

### Check Version
```bash
source ../.env
ansible-playbook -i ../replica_set/inventory.ini 95_check_version.yml
```

### Upgrade
```bash
export TARGET_MONGODB_VERSION="8.0.18-ent"
ansible-playbook -i ../replica_set/inventory.ini 90_upgrade_mongodb_version.yml
```

### Downgrade (requires FCV change first!)
```bash
# 1. Set FCV via mongosh
mongosh --host <hostname> --port 27017
db.adminCommand({ setFeatureCompatibilityVersion: "8.0" })

# 2. Run downgrade
export TARGET_MONGODB_VERSION="8.0.15-ent"
ansible-playbook -i ../replica_set/inventory.ini 91_downgrade_mongodb_version.yml
```

---

## 📋 Environment Variables

```bash
# Required for all operations
export OPS_MANAGER_URL="https://your-ops-manager.com"
export OPS_MANAGER_PROJECT_ID="project-id"
export OPS_MANAGER_PUBLIC_KEY="public-key"
export OPS_MANAGER_PRIVATE_KEY="private-key"

# Required for upgrade/downgrade
export TARGET_MONGODB_VERSION="8.0.18-ent"

# Optional for downgrade (bypass FCV check - NOT RECOMMENDED)
export SKIP_FCV_WARNING=true
```

---

## 🎯 Common Scenarios

### Scenario 1: Patch Update (8.0.15 → 8.0.18)
```bash
export TARGET_MONGODB_VERSION="8.0.18-ent"
ansible-playbook -i ../replica_set/inventory.ini 90_upgrade_mongodb_version.yml
```
**Duration**: 10-15 minutes  
**FCV**: Auto-updated, no manual change needed

---

### Scenario 2: Major Upgrade (8.0 → 9.0)
```bash
export TARGET_MONGODB_VERSION="9.0.0-ent"
ansible-playbook -i ../replica_set/inventory.ini 90_upgrade_mongodb_version.yml
```
**Duration**: 15-20 minutes  
**FCV**: Auto-updated from 8.0 to 9.0

---

### Scenario 3: Patch Downgrade (8.0.18 → 8.0.15)
```bash
# FCV already 8.0, no change needed
export TARGET_MONGODB_VERSION="8.0.15-ent"
ansible-playbook -i ../replica_set/inventory.ini 91_downgrade_mongodb_version.yml
```
**Duration**: 10-15 minutes  
**FCV**: Already compatible (8.0)

---

### Scenario 4: Major Downgrade (9.0 → 8.0)
```bash
# MUST set FCV first!
mongosh --host <hostname> --port 27017
db.adminCommand({ setFeatureCompatibilityVersion: "8.0" })
# Wait 5-10 minutes

# Then downgrade
export TARGET_MONGODB_VERSION="8.0.18-ent"
ansible-playbook -i ../replica_set/inventory.ini 91_downgrade_mongodb_version.yml
```
**Duration**: 15-20 minutes  
**FCV**: Must change from 9.0 to 8.0 first

---

## ⚠️ Safety Checklist

### Before Upgrade
- [ ] Backup data
- [ ] Check current version: `95_check_version.yml`
- [ ] Review MongoDB release notes
- [ ] Schedule maintenance window

### Before Downgrade
- [ ] **CRITICAL**: Set FCV to target version first
- [ ] Backup data (mandatory)
- [ ] Review features that will be lost
- [ ] Get team approval
- [ ] Test in non-production first

---

## 🔍 Troubleshooting Quick Fixes

| Error | Quick Fix |
|-------|-----------|
| "Target version must be newer" | Check current version, use newer target |
| "FCV mismatch detected" | Set FCV via mongosh first |
| "Goal not reached" (timeout) | Normal! Check again in 5 minutes |
| "Invalid version format" | Use format: `X.Y.Z-ent` (e.g., `8.0.18-ent`) |
| "Authentication failed" | Re-source `.env`: `source ../.env` |

---

## 📊 Version Format

```bash
# ✅ Correct
8.0.18-ent
7.0.15-ent
9.0.0-ent
8.0.18

# ❌ Incorrect
8.0           # Missing patch
v8.0.18-ent   # Extra prefix
8.0.18-ent-ubuntu  # Extra suffix
```

---

## 🕒 Typical Durations

| Operation | Replica Set (3 nodes) | Sharded Cluster (8 processes) |
|-----------|----------------------|-------------------------------|
| Patch Upgrade | 10-15 min | 20-30 min |
| Major Upgrade | 15-20 min | 30-40 min |
| Patch Downgrade | 10-15 min | 20-30 min |
| Major Downgrade | 15-20 min | 30-40 min |
| FCV Change | 5-10 min | 10-15 min |

---

## 📁 Inventory Files

```bash
# Replica Set
-i ../replica_set/inventory.ini

# Sharded Cluster
-i ../sharded_cluster/inventory_sharded.yml

# Standalone
-i ../standalone/inventory_standalone.yml
```

---

## 🎓 FCV (Feature Compatibility Version)

### What is FCV?
Controls which MongoDB features are available. Prevents incompatible features during downgrade.

### Check FCV
```bash
mongosh --host <hostname> --port 27017
db.adminCommand({ getParameter: 1, featureCompatibilityVersion: 1 })
```

### Set FCV
```bash
# Set to 8.0
db.adminCommand({ setFeatureCompatibilityVersion: "8.0" })

# Set to 7.0
db.adminCommand({ setFeatureCompatibilityVersion: "7.0" })

# Set to 9.0
db.adminCommand({ setFeatureCompatibilityVersion: "9.0" })
```

### FCV Rules
- **Upgrade**: FCV auto-updated by playbook ✅
- **Downgrade**: Must manually set FCV BEFORE downgrade 🛑
- **Wait Time**: 5-10 minutes after setting FCV

---

## 🔗 Related Commands

```bash
# Check Ops Manager status
curl -u "$OPS_MANAGER_PUBLIC_KEY:$OPS_MANAGER_PRIVATE_KEY" \
  "$OPS_MANAGER_URL/api/public/v1.0/groups/$OPS_MANAGER_PROJECT_ID/automationStatus"

# Get deployment config
curl -u "$OPS_MANAGER_PUBLIC_KEY:$OPS_MANAGER_PRIVATE_KEY" \
  "$OPS_MANAGER_URL/api/public/v1.0/groups/$OPS_MANAGER_PROJECT_ID/automationConfig"

# Check MongoDB process status
ssh <hostname> "ps aux | grep mongod"

# View MongoDB logs
ssh <hostname> "tail -f /var/log/mongodb/mongod.log"
```

---

## 💡 Pro Tips

1. **Always check version first**: `95_check_version.yml`
2. **Backup before downgrade**: Mandatory!
3. **Monitor in UI**: Keep Ops Manager UI open during changes
4. **Wait for goals**: Let automation complete before making more changes
5. **Test in dev first**: Never test in production
6. **FCV is critical**: For downgrades, FCV must be set correctly
7. **Rolling upgrades**: Ops Manager does one node at a time (minimal downtime)
8. **Abort window**: 15-20 seconds to press Ctrl+C if needed

---

## 📚 Full Documentation

For detailed information, see: [README.md](./README.md)
