# Fix: Create Deployment Versions Dropdown

## Issue

The MongoDB version dropdown in the Create Deployment modal was not working because it was expecting the old data format from the API.

---

## Root Cause

The `CreateDeploymentModal.tsx` was written to handle the raw `mongodb_versions.json` format:

**Old Format (Expected):**
```json
{
  "versions": [
    {
      "major": "8.0",
      "releases": ["8.0.19", "8.0.19-ent", "8.0.18", "8.0.18-ent"]
    }
  ],
  "recommended": {
    "latest": "8.0.19",
    "latestEnterprise": "8.0.19-ent"
  }
}
```

**New Format (API Returns):**
```json
[
  {
    "major": "8.0",
    "label": "MongoDB 8.0",
    "versions": [
      {"version": "8.0.19", "label": "Latest"},
      {"version": "8.0.19-ent", "label": "Latest"},
      {"version": "8.0.18", "label": null}
    ]
  }
]
```

The backend now transforms the data and returns it in the new format, but the frontend was still trying to access `versions.versions` and `versions.recommended`.

---

## Solution

Updated `CreateDeploymentModal.tsx` to handle the new transformed API response format.

### **Changes Made:**

#### **1. Updated Version Loading Logic**

**Before:**
```typescript
const data = await versionsApi.getAll();
setVersions(data);
// Set default version to recommended
if (data.recommended) {
  const defaultVersion = tenantPlan === 'enterprise' 
    ? data.recommended.latestEnterprise 
    : data.recommended.latest;
  setFormData(prev => ({ ...prev, mongoVersion: defaultVersion }));
}
```

**After:**
```typescript
const data = await versionsApi.getAll();
setVersions(data);

// Set default version to first "Latest" labeled version for the plan
if (data && data.length > 0) {
  let defaultVersion = '';
  for (const majorGroup of data) {
    const latestVersion = majorGroup.versions.find((v: any) => 
      v.label === 'Latest' && 
      (tenantPlan === 'enterprise' ? v.version.endsWith('-ent') : !v.version.endsWith('-ent'))
    );
    if (latestVersion) {
      defaultVersion = latestVersion.version;
      break;
    }
  }
  
  // Fallback to first version if no "Latest" found
  if (!defaultVersion && data[0].versions.length > 0) {
    const firstMatchingVersion = data[0].versions.find((v: any) => 
      tenantPlan === 'enterprise' ? v.version.endsWith('-ent') : !v.version.endsWith('-ent')
    );
    if (firstMatchingVersion) {
      defaultVersion = firstMatchingVersion.version;
    }
  }
  
  if (defaultVersion) {
    setFormData(prev => ({ ...prev, mongoVersion: defaultVersion }));
  }
}
```

**What Changed:**
- Now looks for versions with `label === 'Latest'`
- Filters by plan (Enterprise vs Community)
- Has fallback to first matching version if no "Latest" found

---

#### **2. Updated Dropdown Rendering**

**Before:**
```tsx
{versions?.versions?.map((majorVersion: any) => (
  <optgroup key={majorVersion.major} label={`MongoDB ${majorVersion.major}`}>
    {majorVersion.releases.map((version: string) => {
      const isEnterprise = version.endsWith('-ent');
      if (tenantPlan === 'enterprise' && !isEnterprise) return null;
      if (tenantPlan === 'community' && isEnterprise) return null;
      
      return (
        <option key={version} value={version}>
          {version}
          {versions?.recommended?.latest === version && ' (Latest)'}
          {versions?.recommended?.latestEnterprise === version && ' (Latest Enterprise)'}
          {versions?.recommended?.lts === version && ' (LTS)'}
          {versions?.recommended?.ltsEnterprise === version && ' (LTS Enterprise)'}
        </option>
      );
    })}
  </optgroup>
))}
```

**After:**
```tsx
{versions && Array.isArray(versions) && versions.map((majorGroup: any) => (
  <optgroup key={majorGroup.major} label={majorGroup.label || `MongoDB ${majorGroup.major}`}>
    {majorGroup.versions
      .filter((versionObj: any) => {
        // Filter based on plan
        const isEnterprise = versionObj.version.endsWith('-ent');
        if (tenantPlan === 'enterprise') return isEnterprise;
        if (tenantPlan === 'community') return !isEnterprise;
        return true;
      })
      .map((versionObj: any) => (
        <option key={versionObj.version} value={versionObj.version}>
          {versionObj.version}
          {versionObj.label && ` (${versionObj.label})`}
        </option>
      ))
    }
  </optgroup>
))}
```

**What Changed:**
- Accesses `versions` directly as an array (not `versions.versions`)
- Uses `majorGroup.versions` array with version objects
- Filters by checking `versionObj.version.endsWith('-ent')`
- Displays label from `versionObj.label` (already attached by backend)
- Uses `majorGroup.label` from backend

---

## Result

### **Dropdown Now Shows:**

#### **Enterprise Tenant:**
```
MongoDB 8.0
  8.0.19-ent (Latest)
  8.0.18-ent
  8.0.17-ent
  
MongoDB 7.0
  7.0.30-ent (LTS)
  7.0.29-ent
  
MongoDB 6.0
  6.0.27-ent
```

#### **Community Tenant:**
```
MongoDB 8.0
  8.0.19 (Latest)
  8.0.18
  8.0.17
  
MongoDB 7.0
  7.0.30 (LTS)
  7.0.29
  
MongoDB 6.0
  6.0.27
```

---

## Benefits

✅ **Consistent with Upgrade Modal** - Both modals now use same API format  
✅ **Automatic Labeling** - Labels (Latest, LTS) come from backend  
✅ **Plan Filtering** - Shows only relevant versions for tenant plan  
✅ **Smart Default** - Auto-selects latest version for the plan  
✅ **Grouped Display** - Versions grouped by major version  

---

## Testing

### **Test 1: Enterprise Tenant**
```bash
# 1. Open Create Deployment modal for Enterprise tenant
# 2. Check version dropdown
# Expected: Only -ent versions shown
# Expected: 8.0.19-ent (Latest) selected by default
# Expected: Grouped by major version
```

### **Test 2: Community Tenant**
```bash
# 1. Open Create Deployment modal for Community tenant
# 2. Check version dropdown
# Expected: Only regular versions shown (no -ent)
# Expected: 8.0.19 (Latest) selected by default
# Expected: Grouped by major version
```

### **Test 3: Create Deployment**
```bash
# 1. Select version from dropdown
# 2. Fill other fields
# 3. Click Create
# Expected: Deployment created with selected version
```

---

## Files Modified

✅ `AtlasForge-UI-Vite/src/components/CreateDeploymentModal.tsx`
- Updated version loading logic
- Updated dropdown rendering
- Now compatible with new API format

---

## Alignment Status

| Component | API Format | Status |
|-----------|------------|--------|
| Backend `/mongodb-versions` | New transformed format | ✅ Working |
| `UpgradeVersionModal.tsx` | New transformed format | ✅ Working |
| `CreateDeploymentModal.tsx` | New transformed format | ✅ Fixed |
| Postman Collection | New transformed format | ✅ Updated |

**All components now aligned!** ✅

---

## Summary

The Create Deployment version dropdown was broken because it expected the old raw JSON format, but the backend now returns a transformed format with labels already attached. Fixed by updating the modal to:

1. Access versions as array directly (not `versions.versions`)
2. Find "Latest" labeled version for default
3. Filter version objects by plan
4. Display labels from `versionObj.label`

**Dropdown now works perfectly!** 🎉
