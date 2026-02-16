# Feature: Upgrade Version Dropdown with Version List

## Enhancement Added ✅

### **What Changed:**
Replaced the manual text input in "Upgrade Version" modal with a dropdown that lists all available MongoDB versions, filtered by tenant plan (Enterprise/Community).

---

## Before vs After

### **Before (Manual Input):**
```
┌─────────────────────────────────────┐
│ Upgrade MongoDB Version             │
│                                     │
│ Current version: 7.0.14-ent        │
│                                     │
│ New MongoDB Version:                │
│ ┌─────────────────────────────────┐ │
│ │ [Type manually...]              │ │
│ └─────────────────────────────────┘ │
│ Must be higher than current         │
│                                     │
│ [Cancel] [Upgrade Version]          │
└─────────────────────────────────────┘
```

**Issues:**
- ❌ User has to know exact version numbers
- ❌ Prone to typos (8.0.17-ent vs 8.0.17-Ent)
- ❌ No visibility of available versions
- ❌ Users might try invalid versions

---

### **After (Version Dropdown):**
```
┌─────────────────────────────────────┐
│ Upgrade MongoDB Version             │
│                                     │
│ Current version: 7.0.14-ent        │
│                                     │
│ New MongoDB Version:                │
│ ┌─────────────────────────────────┐ │
│ │ Select a version...          ▼ │ │
│ └─────────────────────────────────┘ │
│                                     │
│ Dropdown shows:                     │
│ ┌─────────────────────────────────┐ │
│ │ MongoDB 8.0                     │ │
│ │   8.0.17-ent (Latest)           │ │
│ │   8.0.16-ent                    │ │
│ │                                 │ │
│ │ MongoDB 7.0                     │ │
│ │   7.0.14-ent (LTS)              │ │
│ │   7.0.13-ent                    │ │
│ └─────────────────────────────────┘ │
│                                     │
│ [Cancel] [Upgrade Version]          │
└─────────────────────────────────────┘
```

**Benefits:**
- ✅ See all available versions
- ✅ Grouped by major version (8.0, 7.0, etc.)
- ✅ Labels show (Latest), (LTS), (Recommended)
- ✅ Filtered by plan (Enterprise shows -ent, Community shows regular)
- ✅ No typos possible
- ✅ Only valid versions shown

---

## Implementation

### **1. Added Version Loading:**
```typescript
const [versions, setVersions] = useState<any[]>([]);
const [loadingVersions, setLoadingVersions] = useState(false);

// Load versions when modal opens
useEffect(() => {
  const loadVersions = async () => {
    setLoadingVersions(true);
    try {
      const data = await deploymentsApi.getMongoDBVersions();
      setVersions(data);
    } catch (error) {
      console.error('Failed to load MongoDB versions:', error);
    } finally {
      setLoadingVersions(false);
    }
  };

  if (open) {
    loadVersions();
  }
}, [open]);
```

---

### **2. Added Tenant Plan Filtering:**
```typescript
// Filter versions based on tenant plan
.filter((v: any) => {
  if (tenantPlan === 'community') {
    return !v.version.includes('-ent');  // Show only regular versions
  } else {
    return v.version.includes('-ent');   // Show only -ent versions
  }
})
```

---

### **3. Created Dropdown with Groups:**
```typescript
<select
  value={mongoVersion}
  onChange={(e) => setMongoVersion(e.target.value)}
  className="input"
  disabled={loadingVersions}
>
  <option value="">Select a version to upgrade to...</option>
  
  {versions.map((versionGroup) => (
    <optgroup key={versionGroup.major} label={versionGroup.label}>
      {versionGroup.versions
        .filter((v: any) => {
          // Filter by tenant plan
          if (tenantPlan === 'community') {
            return !v.version.includes('-ent');
          } else {
            return v.version.includes('-ent');
          }
        })
        .map((v: any) => (
          <option key={v.version} value={v.version}>
            {v.version} {v.label ? `(${v.label})` : ''}
          </option>
        ))}
    </optgroup>
  ))}
</select>
```

---

## Files Modified

1. ✅ `UpgradeVersionModal.tsx` - Changed from text input to dropdown
2. ✅ `DeploymentDetailsPage.tsx` - Pass tenantPlan prop

---

## Version Filtering

### **Enterprise Deployment:**
```
Dropdown shows:
  MongoDB 8.0
    └─ 8.0.19-ent (Latest)
    └─ 8.0.18-ent
    └─ 8.0.17-ent
  
  MongoDB 7.0
    └─ 7.0.14-ent (LTS)
    └─ 7.0.13-ent
  
  (Only -ent versions shown)
```

---

### **Community Deployment:**
```
Dropdown shows:
  MongoDB 8.0
    └─ 8.0.10 (Latest)
    └─ 8.0.9
    └─ 8.0.8
  
  MongoDB 7.0
    └─ 7.0.15 (LTS)
    └─ 7.0.14
  
  (Only regular versions, no -ent)
```

---

## Features

### **1. Downgrade Prevention (Still Works!):**
```typescript
const isDowngradeAttempt = mongoVersion.trim() && isDowngrade(currentVersion, mongoVersion.trim());

// If user selects older version:
if (isDowngradeAttempt) {
  // Show warning banner
  // Disable upgrade button
  // Show error message
}
```

---

### **2. Visual Feedback:**
```
Current version: 7.0.14-ent

User selects: 7.0.13-ent
→ ⚠️ Red banner: "Downgrade detected! Downgrades are not allowed."
→ Upgrade button disabled

User selects: 8.0.19-ent
→ ✅ No warning
→ Upgrade button enabled
```

---

### **3. Loading States:**
```typescript
{loadingVersions ? (
  <select disabled>
    <option>Loading versions...</option>
  </select>
) : (
  <select>
    {/* Version options */}
  </select>
)}
```

---

## Testing

### **Test 1: Enterprise Deployment Upgrade**

```bash
# 1. Create Enterprise deployment with version 7.0.14-ent
# 2. Wait for it to be running
# 3. Click [Upgrade Version] button

# Expected Modal:
┌─────────────────────────────────────┐
│ Upgrade MongoDB Version             │
│                                     │
│ Current version: 7.0.14-ent        │
│                                     │
│ New MongoDB Version:                │
│ [Select a version...           ▼]  │
│                                     │
│ Click dropdown:                     │
│ ┌─────────────────────────────────┐ │
│ │ MongoDB 8.0                     │ │
│ │   8.0.19-ent (Latest)    ✅    │ │
│ │   8.0.18-ent             ✅    │ │
│ │                                 │ │
│ │ MongoDB 7.0                     │ │
│ │   7.0.14-ent (LTS)      ← Current│
│ │   7.0.13-ent            ❌ Downgrade│
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘

# 4. Select 8.0.19-ent
# Expected:
# - No warning
# - [Upgrade Version] button enabled
# - Click to upgrade ✅

# 5. Try selecting 7.0.13-ent
# Expected:
# - ⚠️ Red warning: "Downgrade detected!"
# - [Upgrade Version] button disabled ❌
```

---

### **Test 2: Community Deployment Upgrade**

```bash
# 1. Create Community deployment with version 7.0.0
# 2. Click [Upgrade Version]

# Expected Dropdown:
│ MongoDB 8.0                     │
│   8.0.10 (Latest)       ✅     │
│   8.0.9                 ✅     │
│                                 │
│ MongoDB 7.0                     │
│   7.0.15 (LTS)          ✅     │
│   7.0.14                ✅     │
│   7.0.0                ← Current│

# Notice: NO -ent versions shown ✅

# Select 8.0.10
# Click [Upgrade Version]
# Expected: Upgrade succeeds ✅
```

---

### **Test 3: Version Loading**

```bash
# 1. Click [Upgrade Version]

# Expected immediate state:
│ New MongoDB Version:                │
│ [Loading versions...]  (disabled)   │

# After 1 second:
│ New MongoDB Version:                │
│ [Select a version...           ▼]  │
│ (enabled, shows all versions)       │
```

---

## Downgrade Detection Examples

### **Example 1: Clear Downgrade**
```
Current: 8.0.19-ent
Selected: 7.0.14-ent
→ ❌ Downgrade (8.0 → 7.0)
→ Button disabled
```

### **Example 2: Patch Downgrade**
```
Current: 8.0.19-ent
Selected: 8.0.18-ent
→ ❌ Downgrade (8.0.19 → 8.0.18)
→ Button disabled
```

### **Example 3: Valid Upgrade**
```
Current: 7.0.14-ent
Selected: 8.0.19-ent
→ ✅ Upgrade (7.0 → 8.0)
→ Button enabled
```

### **Example 4: Same Version**
```
Current: 8.0.19-ent
Selected: 8.0.19-ent
→ ⚠️ No change
→ Shows: "Version unchanged"
```

---

## User Benefits

### **Before (Manual Input):**
❌ Had to remember exact version numbers  
❌ Could make typos  
❌ Didn't know what versions were available  
❌ Could try invalid versions  

### **After (Dropdown):**
✅ See all available versions  
✅ Grouped by major version  
✅ Shows labels (Latest, LTS, Recommended)  
✅ Filtered by plan (no invalid versions)  
✅ No typos possible  
✅ Easy to compare versions  
✅ Clear upgrade path  

---

## Edge Cases Handled

1. ✅ **Versions loading failed** - Dropdown shows "Select..." and empty
2. ✅ **No versions available** - Dropdown shows placeholder only
3. ✅ **User closes and reopens modal** - Re-fetches versions
4. ✅ **Downgrade selected** - Shows warning, disables button
5. ✅ **Same version selected** - Shows "unchanged" error
6. ✅ **Enterprise plan** - Only shows -ent versions
7. ✅ **Community plan** - Only shows regular versions
8. ✅ **Loading state** - Dropdown disabled until loaded

---

## API Integration

### **Endpoint Used:**
```
GET /mongodb-versions

Response:
[
  {
    "major": "8.0",
    "label": "MongoDB 8.0",
    "versions": [
      {"version": "8.0.19-ent", "label": "Latest"},
      {"version": "8.0.18-ent", "label": null},
      {"version": "8.0.10", "label": "Latest"},
      ...
    ]
  },
  {
    "major": "7.0",
    "label": "MongoDB 7.0",
    "versions": [
      {"version": "7.0.14-ent", "label": "LTS"},
      ...
    ]
  }
]
```

---

## Summary

### **What Changed:**
1. ✅ Replaced text input with dropdown
2. ✅ Load versions from `/mongodb-versions` API
3. ✅ Filter by tenant plan (Enterprise/Community)
4. ✅ Group by major version (8.0, 7.0, etc.)
5. ✅ Show labels (Latest, LTS, Recommended)
6. ✅ Downgrade prevention still works
7. ✅ Loading states handled

### **Result:**
🎉 **Much better UX for version upgrades!**

- Users can see all available versions
- No manual typing required
- Filtered by plan (only valid versions shown)
- Clear visual organization
- Labels help users make informed choices
- Downgrade prevention still enforced

---

**Version Upgrade Dropdown Complete!** ✅
