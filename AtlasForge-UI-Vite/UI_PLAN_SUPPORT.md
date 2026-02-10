# UI Updates for Enterprise vs Community Plan Support

## Overview

Updated the MDBaaS UI to support **Enterprise vs Community** tenants with clear visual indicators and feature availability based on the selected plan.

---

## Changes Made

### 1. Tenant Onboarding Form (`CreateTenantModal.tsx`)

#### Added Plan Selector
- **Radio buttons** to choose between Enterprise and Community plans
- Default selection: **Enterprise**
- Visual styling with badges and descriptions

```tsx
<div>
  <label>Deployment Plan *</label>
  <div className="space-y-3">
    {/* Enterprise Option */}
    <label className="flex items-start p-3 border-2 rounded-lg cursor-pointer">
      <input type="radio" name="plan" value="enterprise" checked={...} />
      <div className="ml-3 flex-1">
        <span className="font-medium">Enterprise (Ops Manager)</span>
        <span className="badge badge-green">Recommended</span>
        <p className="text-sm text-gray-600">
          Full features including Ops Manager integration, backup, and advanced monitoring
        </p>
      </div>
    </label>

    {/* Community Option */}
    <label className="flex items-start p-3 border-2 rounded-lg cursor-pointer">
      <input type="radio" name="plan" value="community" checked={...} />
      <div className="ml-3 flex-1">
        <span className="font-medium">Community (No Ops Manager)</span>
        <span className="badge badge-blue">Open Source</span>
        <p className="text-sm text-gray-600">
          MongoDB Community binaries. Backup and Ops Manager features not available.
        </p>
      </div>
    </label>
  </div>
</div>
```

#### API Request
```typescript
const request: CreateTenantRequest = {
  tenantId: formData.tenantId.trim(),
  displayName: formData.displayName.trim(),
  plan: formData.plan, // 'enterprise' or 'community'
  environment: formData.environment.trim(),
  notes: formData.notes.trim()
};
```

---

### 2. Tenants Overview Page (`TenantsPage.tsx`)

#### Plan Badges on Tenant Cards
Each tenant card now displays a plan badge in the top-right corner:
- **Enterprise**: Green badge "Enterprise"
- **Community**: Blue badge "Community"

```tsx
<div className="flex items-start justify-between mb-2">
  <h3 className="text-xl font-semibold text-mongodb-forest">
    {tenant.displayName || tenant.tenantId}
  </h3>
  {tenant.plan === 'community' ? (
    <span className="badge badge-blue text-xs">Community</span>
  ) : (
    <span className="badge badge-green text-xs">Enterprise</span>
  )}
</div>
```

**Visual Preview:**
```
┌─────────────────────────────────────┐
│  Acme Corporation    [Enterprise ✓] │
│  t-acme                              │
│  prod                                │
│                                      │
│  Deployments: 3   Running: 2        │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Initech Inc        [Community 🔵]  │
│  t-initech                           │
│  dev                                 │
│                                      │
│  Deployments: 1   Running: 1        │
└─────────────────────────────────────┘
```

---

### 3. Tenant Details Page (`TenantDetailsPage.tsx`)

#### Plan Display in Header
- Badge next to tenant name
- Descriptive text showing plan details

```tsx
<div className="flex items-center gap-3 mb-2">
  <h1 className="text-3xl font-bold text-mongodb-forest">
    {tenant.displayName || tenant.tenantId}
  </h1>
  {tenant.plan === 'community' ? (
    <span className="badge badge-blue">Community</span>
  ) : (
    <span className="badge badge-green">Enterprise</span>
  )}
</div>
<p className="text-mongodb-slate mb-3">
  Plan: <span className="font-medium">
    {tenant.plan === 'community' 
      ? 'Community (No Ops Manager)' 
      : 'Enterprise (Ops Manager)'}
  </span>
</p>
```

#### Pass Plan to Deployment Modal
```tsx
<CreateDeploymentModal
  open={showCreateModal}
  onClose={() => setShowCreateModal(false)}
  onSuccess={loadData}
  tenantId={tenant.tenantId}
  tenantPlan={tenant.plan}  // NEW
/>
```

---

### 4. Deployment Creation Form (`CreateDeploymentModal.tsx`)

#### Plan-Specific Information Banner

**For Enterprise Tenants:**
```tsx
<div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-md">
  <p className="text-sm text-green-800">
    <span className="font-medium">Enterprise Plan:</span> This deployment will use 
    Enterprise Advanced with Ops Manager integration, including backup and advanced monitoring.
  </p>
</div>
```

**For Community Tenants:**
```tsx
<div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
  <p className="text-sm text-blue-800">
    <span className="font-medium">Community Plan:</span> This deployment will use 
    MongoDB Community binaries. Ops Manager backup and advanced features are not available.
  </p>
</div>
```

---

### 5. Deployment Details Page (`DeploymentDetailsPage.tsx`)

#### Fetch Tenant Data
```typescript
const loadData = async () => {
  const [deploymentData, tenantData] = await Promise.all([
    deploymentsApi.getById(tenantId, deploymentId),
    tenantsApi.getById(tenantId)  // NEW - fetch tenant to get plan
  ]);
  setDeployment(deploymentData);
  setTenant(tenantData);
};

const tenantPlan = tenant?.plan || 'enterprise';
```

#### Plan Badge in Header
```tsx
<div className="flex items-center gap-3 mb-2">
  <h1 className="text-3xl font-bold text-mongodb-forest">
    {deployment.displayName || deployment.deploymentId}
  </h1>
  {tenantPlan === 'community' ? (
    <span className="badge badge-blue">Community</span>
  ) : (
    <span className="badge badge-green">Enterprise</span>
  )}
</div>
```

#### Conditional Tabs Display
**Enterprise deployments** show all tabs:
- Overview
- Monitoring
- Backup ✓

**Community deployments** hide Backup tab:
- Overview
- Monitoring
- ~~Backup~~ (hidden)

```tsx
<nav className="flex space-x-8">
  {(['overview', 'monitoring', 
     ...(tenantPlan === 'enterprise' ? ['backup' as TabType] : [])]
  ).map((tab) => (
    <button key={tab} onClick={() => setActiveTab(tab)}>
      {tab}
    </button>
  ))}
</nav>
```

#### Backup Tab Content

**For Enterprise (if accessed):**
```tsx
{activeTab === 'backup' && tenantPlan === 'enterprise' && (
  <BackupCard 
    tenantId={deployment.tenantId} 
    deploymentId={deployment.deploymentId}
    initialEnabled={false}
  />
)}
```

**For Community (fallback message):**
```tsx
{activeTab === 'backup' && tenantPlan === 'community' && (
  <div className="card">
    <h3>Backup Not Available</h3>
    <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
      <p className="text-sm text-yellow-800">
        <span className="font-medium">Community Plan Limitation:</span> 
        Backup is only available for Enterprise deployments with Ops Manager integration.
      </p>
    </div>
  </div>
)}
```

---

## Type Updates (`types.ts`)

### Updated Interfaces

```typescript
export interface Tenant {
  tenantId: string;
  displayName?: string;
  plan?: 'enterprise' | 'community';  // NEW
  namespace?: string;
  createdAt?: string;
  environment?: string;
  notes?: string;
}

export interface CreateTenantRequest {
  tenantId: string;
  displayName?: string;
  plan?: 'enterprise' | 'community';  // NEW
  environment?: string;
  notes?: string;
}
```

---

## Visual Design Summary

### Color Coding
- **Enterprise**: Green badges/accents (`badge-green`)
- **Community**: Blue badges/accents (`badge-blue`)
- **Warnings**: Yellow backgrounds for limitations

### Badge Styles
```css
.badge-green {
  background-color: #DEF7EC;
  color: #046C4E;
}

.badge-blue {
  background-color: #DBEAFE;
  color: #1E40AF;
}
```

### Information Panels
- **Enterprise**: Green border + background
- **Community**: Blue border + background
- **Limitations**: Yellow border + background

---

## Feature Availability Matrix

| Feature | Enterprise | Community |
|---------|-----------|-----------|
| **Tenant Creation** | ✅ Full support | ✅ Full support |
| **Plan Selection** | ✅ Shows "Enterprise" badge | ✅ Shows "Community" badge |
| **Deployment Creation** | ✅ All types | ✅ ReplicaSet only (backend enforced) |
| **Scale Operations** | ✅ Available | ✅ Available |
| **Version Upgrade** | ✅ Available | ✅ Available |
| **Lifecycle (Shutdown/Start/Restart)** | ✅ Available | ✅ Available |
| **Prometheus Monitoring** | ✅ Available | ✅ Available |
| **Backup Tab** | ✅ Visible with toggle | ❌ Hidden from UI |
| **Connection Info** | ✅ Available | ✅ Available |

---

## User Experience Flow

### Enterprise Tenant Flow
1. **Create Tenant**
   - Select "Enterprise (Ops Manager)"
   - See green "Recommended" badge
   - Get full feature description

2. **View Tenant**
   - Green "Enterprise" badge on card
   - "Plan: Enterprise (Ops Manager)" in details

3. **Create Deployment**
   - Green info panel: "This deployment will use Enterprise Advanced..."
   - All deployment types available

4. **View Deployment**
   - Green "Enterprise" badge
   - All tabs visible: Overview, Monitoring, **Backup**
   - Full backup toggle functionality

### Community Tenant Flow
1. **Create Tenant**
   - Select "Community (No Ops Manager)"
   - See blue "Open Source" badge
   - Get feature limitation notice

2. **View Tenant**
   - Blue "Community" badge on card
   - "Plan: Community (No Ops Manager)" in details

3. **Create Deployment**
   - Blue info panel: "This deployment will use MongoDB Community binaries..."
   - Backend enforces ReplicaSet only

4. **View Deployment**
   - Blue "Community" badge
   - Tabs visible: Overview, Monitoring (**NO Backup tab**)
   - If backup accessed directly: Yellow warning message

---

## Error Handling

### Backend Errors for Community
If backend returns 400 for unsupported operations:

```typescript
// Example: Backup API call on community deployment
try {
  await deploymentsApi.updateBackup(tenantId, deploymentId, true);
} catch (error) {
  // Backend returns: 400 "Backup is not supported for community deployments"
  showError('Backup not available', error.detail);
}
```

**UI handles this by:**
1. Hiding the backup tab completely (prevention)
2. Showing limitation message if accessed (fallback)

---

## Testing Checklist

### Enterprise Tenant
- [ ] Create enterprise tenant (explicit plan="enterprise")
- [ ] Create enterprise tenant (implicit, no plan specified)
- [ ] Verify green "Enterprise" badge on tenant card
- [ ] Verify "Enterprise (Ops Manager)" text in details
- [ ] Create deployment - see green info banner
- [ ] View deployment - see green badge
- [ ] Verify Backup tab is visible
- [ ] Test backup enable/disable toggle

### Community Tenant
- [ ] Create community tenant (plan="community")
- [ ] Verify blue "Community" badge on tenant card
- [ ] Verify "Community (No Ops Manager)" text in details
- [ ] Create deployment - see blue info banner
- [ ] View deployment - see blue badge
- [ ] Verify Backup tab is NOT visible
- [ ] Try to create Standalone (backend should reject)

### Plan Display
- [ ] Tenant cards show correct badge colors
- [ ] Tenant details page shows plan information
- [ ] Deployment header shows inherited plan badge
- [ ] Create deployment modal shows correct plan notice

---

## Files Modified

1. ✅ `src/components/CreateTenantModal.tsx` - Added plan selector with radio buttons
2. ✅ `src/lib/types.ts` - Added plan field to Tenant and CreateTenantRequest
3. ✅ `src/pages/TenantsPage.tsx` - Added plan badges to tenant cards
4. ✅ `src/pages/TenantDetailsPage.tsx` - Display plan info, pass to modal
5. ✅ `src/components/CreateDeploymentModal.tsx` - Plan-specific info banners
6. ✅ `src/pages/DeploymentDetailsPage.tsx` - Fetch tenant, conditional tabs, plan badge

---

## API Integration

### Request Examples

**Create Enterprise Tenant:**
```bash
POST /tenants
{
  "tenantId": "t-acme",
  "displayName": "Acme Corp",
  "plan": "enterprise"
}
```

**Create Community Tenant:**
```bash
POST /tenants
{
  "tenantId": "t-initech",
  "displayName": "Initech Inc",
  "plan": "community"
}
```

### Response Examples

**GET /tenants:**
```json
[
  {
    "tenantId": "t-acme",
    "displayName": "Acme Corp",
    "plan": "enterprise",
    "namespace": "mdb-t-acme",
    "status": "Active"
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

---

## Summary

✅ **Tenant onboarding** includes clear plan selection with descriptions  
✅ **Visual indicators** (badges) throughout UI show current plan  
✅ **Feature availability** automatically adjusted based on plan  
✅ **Backup tab** hidden for community deployments  
✅ **Informative messages** explain limitations  
✅ **Consistent color coding** (green=enterprise, blue=community)  
✅ **User-friendly** with clear expectations at every step  

The UI now provides a seamless experience for both Enterprise and Community deployments with appropriate feature visibility and helpful guidance!
