# Progressive Status Disclosure Implementation

## Overview

Prevents users from accessing deployment details until the deployment is fully running. Shows progress indicators and status updates during deployment creation.

---

## Problem Solved

### **Before:**
❌ Users could navigate to detail page while deployment was still starting  
❌ Detail page showed empty/broken connection info  
❌ Controls didn't work properly for partial deployments  
❌ Confusing UX - users didn't know what was happening  

### **After:**
✅ Details button disabled until deployment is fully running  
✅ Clear progress indicators with loading animation  
✅ Pod-by-pod status with visual feedback  
✅ Progress bar showing percentage complete  
✅ Refresh button for manual status updates  
✅ Estimated time indicator  

---

## Implementation

### **1. Deployment List - Status-Based Actions**

```typescript
// In ExpandableDeploymentList.tsx

// Status: Shutdown
{status?.status === 'shutdown' ? (
  <button>Start</button>
) : 

// Status: Pending/Partial (Not Ready)
status?.status === 'pending' || status?.status === 'partial' ? (
  <>
    <button>🔄 Refresh</button>
    <button disabled title="Details available when deployment is fully running">
      Details (Starting...)
    </button>
  </>
) : 

// Status: Running (Ready)
(
  <button>Details</button>
)}
```

---

### **2. Progress View in Expanded Section**

When deployment is `pending` or `partial`, expanded section shows:

#### **Components:**
1. **Loading Spinner** - Animated spinning wheel
2. **Status Header** - "Starting Up..."
3. **Pod Counter** - "Pods: 1/3 ready"
4. **Progress Bar** - Visual bar with percentage
5. **Estimated Time** - "This may take 2-3 minutes"
6. **Pod List** - Individual pod status with icons

```typescript
// Calculate progress
const progressPercent = status.totalReplicas > 0 
  ? Math.round((status.readyReplicas / status.totalReplicas) * 100)
  : 0;

// Show progress view
if (status.status === 'pending' || status.status === 'partial') {
  return (
    <div>
      {/* Spinning loader */}
      <div className="animate-spin">...</div>
      
      {/* Progress bar */}
      <div className="bg-blue-200 rounded-full h-2">
        <div style={{ width: `${progressPercent}%` }}></div>
      </div>
      
      {/* Pod status list */}
      {status.pods.map(pod => (
        <div>
          {pod.ready ? '●' : '◐'} {pod.name} - {pod.status}
        </div>
      ))}
    </div>
  );
}
```

---

### **3. Deployment Name Click Behavior**

```typescript
// Before: Always navigated to detail page
<button onClick={() => navigate(`/tenants/${tenantId}/deployments/${deploymentId}`)}>
  {deployment.displayName}
</button>

// After: Only navigate if running, otherwise toggle expand
<button
  onClick={() => {
    if (status?.status === 'running') {
      navigate(`/tenants/${tenantId}/deployments/${deploymentId}`);
    } else {
      toggleExpand(deployment.deploymentId);
    }
  }}
  title={status?.status !== 'running' ? 'Details available when deployment is fully running' : ''}
>
  {deployment.displayName}
</button>
```

---

### **4. Detail Page Redirect Guard**

```typescript
// In DeploymentDetailsPage.tsx

// Redirect back if accessed directly while not running
useEffect(() => {
  if (deployment && (deployment.status === 'pending' || deployment.status === 'partial')) {
    showError(
      'Deployment not ready',
      'This deployment is still starting up. Please wait for all pods to be running.'
    );
    navigate(`/tenants/${tenantId}`);
  }
}, [deployment?.status]);
```

---

## Visual Guide

### **Deployment List - Pending State**

```
┌──────────────────────────────────────────────────────────┐
│ Tenant: testing5                    [Create Deployment]  │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ▼ ◐ test-5-deployment (Partial)                         │
│     test-5-deployment • ReplicaSet • 3 Members           │
│     Status: Partial | Pods: 1/3 | Version: 8.0.10       │
│     Monitoring: ✓ | Backup: ✗                           │
│                                                           │
│     [🔄 Refresh] [Details (Starting...)]                 │
│                    ↑                                      │
│              DISABLED BUTTON                              │
│                                                           │
│     ┌────────────────────────────────────────────────┐  │
│     │  🔄 Starting Up...                             │  │
│     │  Pods: 1/3 ready                               │  │
│     │                                                 │  │
│     │  Progress                              33%     │  │
│     │  ━━━━━━━━░░░░░░░░░░░░░░                       │  │
│     │                                                 │  │
│     │  This may take 2-3 minutes. Detail page       │  │
│     │  will be available once all pods are running.  │  │
│     │                                                 │  │
│     │  Pod Status:                                   │  │
│     │  ● test-5-deployment-0    Running          ✓  │  │
│     │  ◐ test-5-deployment-1    ContainerCreating   │  │
│     │  ○ test-5-deployment-2    Pending         ⏳  │  │
│     └────────────────────────────────────────────────┘  │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

---

### **Deployment List - Running State**

```
┌──────────────────────────────────────────────────────────┐
│  ▶ ● test-5-deployment (Running)                         │
│     test-5-deployment • ReplicaSet • 3 Members           │
│     Status: Running | Pods: 3/3 | Version: 8.0.10       │
│     Monitoring: ✓ | Backup: ✗                           │
│                                                           │
│     [Details]  ← NOW ENABLED!                            │
│                                                           │
└──────────────────────────────────────────────────────────┘

Click [Details] → Navigate to detail page ✅
Click deployment name → Navigate to detail page ✅
```

---

## User Flows

### **Flow 1: Create New Deployment**

```
1. User creates new deployment
   ↓
2. Deployment appears in list with status "Pending"
   Status: ○ Pending
   Pods: 0/3
   Button: [Details (Starting...)] - DISABLED
   ↓
3. User clicks chevron to expand
   ↓
4. Sees progress view:
   - Spinning loader
   - "Starting Up..."
   - Progress: 0%
   - Pod list: All "Pending"
   ↓
5. Waits 30 seconds, clicks [🔄 Refresh]
   ↓
6. Status updates:
   Status: ◐ Partial
   Pods: 1/3 (33%)
   Pod-1: Running ✓
   Pod-2: ContainerCreating
   Pod-3: Pending ⏳
   ↓
7. Waits another minute...
   ↓
8. Status becomes "Running":
   Status: ● Running
   Pods: 3/3 (100%)
   All pods: Running ✓
   ↓
9. [Details] button becomes enabled
   ↓
10. User clicks [Details]
   ↓
11. Navigates to full detail page ✅
```

---

### **Flow 2: Try to Access Detail Page Too Early**

```
1. User creates deployment
   ↓
2. User tries to navigate directly:
   http://localhost:5173/tenants/t5/deployments/test-5
   ↓
3. Page loads deployment data
   ↓
4. Detects status is "pending" or "partial"
   ↓
5. Shows error toast:
   "Deployment not ready"
   "This deployment is still starting up..."
   ↓
6. Automatically redirects to tenant page
   ↓
7. User sees deployment list with progress view
```

---

### **Flow 3: Click Deployment Name Before Ready**

```
1. Deployment is in "Partial" state
   ↓
2. User clicks deployment name
   ↓
3. Instead of navigating:
   - Row expands
   - Shows progress view
   - User sees pod status
   ↓
4. User waits for "Running" status
   ↓
5. Clicks deployment name again
   ↓
6. NOW navigates to detail page ✅
```

---

## Status Indicators

### **Status Mapping:**

| Status    | Icon | Color  | Meaning                    | Detail Access |
|-----------|------|--------|----------------------------|---------------|
| pending   | ○    | Gray   | Not started                | ❌ Disabled    |
| partial   | ◐    | Yellow | Some pods running          | ❌ Disabled    |
| running   | ●    | Green  | All pods running           | ✅ Enabled     |
| error     | ✗    | Red    | Something went wrong       | ✅ Enabled     |
| shutdown  | ○    | Gray   | Intentionally stopped      | ❌ Disabled    |

---

## Progress Calculation

```typescript
// Calculate percentage based on ready/total pods
const progressPercent = status.totalReplicas > 0 
  ? Math.round((status.readyReplicas / status.totalReplicas) * 100)
  : 0;

// Examples:
// 0/3 pods ready → 0%
// 1/3 pods ready → 33%
// 2/3 pods ready → 67%
// 3/3 pods ready → 100%
```

---

## Pod Status Icons

```typescript
// Ready pods
{pod.ready ? '●' : '◐'}

// Status badges
{pod.status === 'Running' ? 'bg-green-100 text-green-800' :
 pod.status === 'Pending' ? 'bg-yellow-100 text-yellow-800' :
 'bg-gray-100 text-gray-800'}

// Waiting indicator
{!pod.ready && <span>⏳</span>}
```

---

## CSS Classes

### **Spinning Loader:**
```css
animate-spin        /* Rotates continuously */
h-6 w-6            /* Size */
text-blue-600      /* Color */
```

### **Progress Bar:**
```css
/* Container */
bg-blue-200 rounded-full h-2

/* Fill */
bg-blue-600 h-2 rounded-full transition-all duration-500
width: ${progressPercent}%  /* Dynamic */
```

### **Disabled Button:**
```css
border border-gray-300
text-gray-400
cursor-not-allowed
```

### **Info Banner:**
```css
bg-blue-50 border border-blue-200 rounded-lg p-4
```

---

## Testing

### **Test 1: Create Deployment and Watch Progress**

```bash
# 1. Create deployment
curl -X POST http://localhost:8001/tenants/t5/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "deploymentId": "progress-test",
    "type": "ReplicaSet",
    "mongoVersion": "8.0.10",
    "members": 3
  }'

# 2. Open UI
# Navigate to tenant page

# 3. Verify:
# - Deployment appears with "Pending" status
# - [Details] button is disabled
# - Shows "Details (Starting...)"
# - Can click chevron to expand
# - Sees progress view with spinner
# - Progress bar shows 0%

# 4. Wait 30 seconds, click [🔄 Refresh]

# 5. Verify:
# - Status updates to "Partial"
# - Progress bar increases (e.g., 33%)
# - Some pods show "Running"
# - [Details] still disabled

# 6. Wait 1-2 minutes

# 7. Verify:
# - Status becomes "Running"
# - Progress bar shows 100%
# - All pods show "Running ✓"
# - [Details] button becomes enabled
# - Can click and navigate successfully
```

---

### **Test 2: Try to Access Detail Page Directly**

```bash
# 1. Create deployment (don't wait for it to finish)

# 2. Try to navigate directly:
# http://localhost:5173/tenants/t5/deployments/progress-test

# 3. Verify:
# - Error toast appears
# - "Deployment not ready"
# - Automatically redirects to tenant page
# - Shows deployment list with progress
```

---

### **Test 3: Click Deployment Name Before Ready**

```bash
# 1. With deployment in "Partial" state

# 2. Click deployment name

# 3. Verify:
# - Does NOT navigate
# - Row expands instead
# - Shows progress view
# - Tooltip says "Details available when..."

# 4. Wait for "Running" status

# 5. Click deployment name again

# 6. Verify:
# - NOW navigates to detail page
```

---

## Edge Cases Handled

### **1. No Pods Yet**
```typescript
{status.pods && status.pods.length > 0 ? (
  // Show pod list
) : (
  <p>Loading pod information...</p>
)}
```

### **2. Zero Total Replicas**
```typescript
const progressPercent = status.totalReplicas > 0 
  ? Math.round((status.readyReplicas / status.totalReplicas) * 100)
  : 0;  // Prevents division by zero
```

### **3. Direct URL Access**
```typescript
// Redirect guard in DeploymentDetailsPage
useEffect(() => {
  if (deployment && (deployment.status === 'pending' || deployment.status === 'partial')) {
    showError(...);
    navigate(`/tenants/${tenantId}`);
  }
}, [deployment?.status]);
```

### **4. Status Changes While Viewing**
- Auto-poll every 10 seconds updates status
- Progress bar animates smoothly (transition-all duration-500)
- [Details] button enables automatically when ready

---

## Performance Considerations

### **Polling Frequency:**
- Every 10 seconds automatically
- Manual refresh available via [🔄 Refresh] button
- Only polls when list is visible

### **Animation Performance:**
```css
/* Smooth transitions without jank */
transition-all duration-500  /* Progress bar */
animate-spin                  /* Spinner (CSS animation) */
```

### **Batch Status Requests:**
- Uses `/deployments-status` endpoint
- Single request for all deployments
- Reduces server load

---

## Files Modified

1. ✅ `ExpandableDeploymentList.tsx` - Progress view, button states, click handlers
2. ✅ `DeploymentDetailsPage.tsx` - Redirect guard

---

## Summary

### **What Changed:**
1. ✅ [Details] button disabled when not running
2. ✅ Progress view with spinner and bar
3. ✅ Pod-by-pod status indicators
4. ✅ [🔄 Refresh] button for manual updates
5. ✅ Deployment name click toggles expand (not navigate)
6. ✅ Detail page redirect guard
7. ✅ Estimated time indicator
8. ✅ Clear visual feedback at every stage

### **User Benefits:**
- ✨ No confusion - can't access incomplete deployments
- ✨ Clear progress indicators
- ✨ Manual refresh option
- ✨ Knows exactly what's happening
- ✨ Knows when deployment will be ready
- ✨ Can monitor pod-by-pod progress

### **Result:**
**Perfect progressive disclosure UX!** 🎉
