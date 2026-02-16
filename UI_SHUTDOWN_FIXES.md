# UI Shutdown State Fixes

## Issues Fixed

### **Issue 1: No Start Button on Deployment List**
**Problem:** When deployment is shutdown, there was no way to start it from the tenant deployments page.

**Solution:** Added "Start" button next to "Details" button when deployment status is "shutdown".

### **Issue 2: Lifecycle Controls Visible When Shutdown**
**Problem:** When deployment is shutdown, lifecycle controls (Scale Members, Upgrade Version, Restart, Shutdown) were still visible and could be clicked, which doesn't make sense.

**Solution:** Hide all lifecycle controls when deployment is shutdown. Only show "Start Deployment" button.

---

## Changes Made

### **1. ExpandableDeploymentList.tsx**

#### **Added Imports:**
```typescript
import { deploymentsApi } from '@/lib/api';
import { useToast } from './Toast';
```

#### **Added State:**
```typescript
const [startingDeployment, setStartingDeployment] = useState<string | null>(null);
const { showSuccess, showError } = useToast();
```

#### **Added Function:**
```typescript
const handleStartDeployment = async (deploymentId: string) => {
  setStartingDeployment(deploymentId);
  try {
    await deploymentsApi.start(tenantId, deploymentId);
    showSuccess('Deployment starting', `Deployment ${deploymentId} is starting up`);
    await loadAllStatuses(); // Refresh immediately
  } catch (error: any) {
    showError('Failed to start deployment', error.detail || 'An error occurred');
  } finally {
    setStartingDeployment(null);
  }
};
```

#### **Updated Actions Section:**
```typescript
{/* Actions - Show Start button if shutdown, otherwise Details */}
<div className="flex gap-2">
  {status?.status === 'shutdown' ? (
    <button
      onClick={(e) => {
        e.stopPropagation();
        handleStartDeployment(deployment.deploymentId);
      }}
      disabled={startingDeployment === deployment.deploymentId}
      className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
    >
      {startingDeployment === deployment.deploymentId ? 'Starting...' : 'Start'}
    </button>
  ) : null}
  <button
    onClick={() => navigate(`/tenants/${tenantId}/deployments/${deployment.deploymentId}`)}
    className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-100"
  >
    Details
  </button>
</div>
```

---

### **2. DeploymentDetailsPage.tsx**

#### **Wrapped Lifecycle Controls:**
```typescript
{/* Lifecycle Controls - Only show if NOT shutdown */}
{deployment.status !== 'shutdown' && (
  <div>
    <h2>Lifecycle Controls</h2>
    <div className="flex gap-3 flex-wrap">
      {/* Scale, Upgrade, Restart, Shutdown buttons */}
    </div>
  </div>
)}
```

#### **Added Start Button for Shutdown State:**
```typescript
{/* Show Start button if shutdown */}
{deployment.status === 'shutdown' && (
  <div>
    <h2>Deployment Actions</h2>
    <button 
      onClick={async () => {
        try {
          setActionLoading(true);
          await deploymentsApi.start(deployment.tenantId, deployment.deploymentId);
          showSuccess('Deployment starting', 'Deployment is starting up');
          await loadData();
        } catch (error: any) {
          showError('Failed to start deployment', error.detail);
        } finally {
          setActionLoading(false);
        }
      }}
      disabled={actionLoading}
      className="btn-primary"
    >
      {actionLoading ? 'Starting...' : 'Start Deployment'}
    </button>
    <p className="text-sm text-gray-500 mt-2">
      Start the deployment to restore all MongoDB processes.
    </p>
  </div>
)}
```

#### **Hid Connection Info When Shutdown:**
```typescript
{/* Connection Info - Only show if NOT shutdown */}
{deployment.status !== 'shutdown' && (
  <ConnectionInfo tenantId={deployment.tenantId} deploymentId={deployment.deploymentId} />
)}
```

---

## UI Behavior

### **Before (Shutdown State):**
```
Deployments List:
  ● Deployment-1 (Running)    [Details]
  ○ Deployment-2 (Shutdown)   [Details]  ❌ No way to start!

Detail Page (Shutdown):
  Lifecycle Controls:
    [Scale Members] [Upgrade Version] [Restart] [Shutdown]  ❌ Shouldn't be visible!
  Connection Information:
    Internal URI: ...  ❌ Doesn't make sense when shutdown
```

### **After (Fixed):**
```
Deployments List:
  ● Deployment-1 (Running)    [Details]
  ○ Deployment-2 (Shutdown)   [Start] [Details]  ✅ Can start now!

Detail Page (Running):
  Lifecycle Controls:
    [Scale Members] [Upgrade Version] [Restart] [Shutdown]  ✅ Visible
  Connection Information:
    Internal URI: ...  ✅ Visible

Detail Page (Shutdown):
  Deployment Actions:
    [Start Deployment]  ✅ Only this button visible
  Message: "Start the deployment to restore all MongoDB processes."
  
  (No Lifecycle Controls shown)  ✅ Hidden
  (No Connection Info shown)  ✅ Hidden
```

---

## User Flow

### **Scenario 1: Start from Deployment List**

1. User navigates to tenant page
2. Sees deployment with status "○ Shutdown"
3. Sees **[Start]** button next to Details
4. Clicks **[Start]**
5. Button shows "Starting..."
6. Success message appears: "Deployment starting"
7. Status updates to "◐ Partial" (pods coming up)
8. After 2 minutes: "● Running"
9. **[Start]** button disappears

### **Scenario 2: Start from Detail Page**

1. User clicks on shutdown deployment
2. Sees yellow banner: "Deployment is Shutdown"
3. Overview tab shows **only**:
   - "Deployment Actions" section
   - **[Start Deployment]** button
   - Help text
4. No Lifecycle Controls visible
5. No Connection Info visible
6. User clicks **[Start Deployment]**
7. Button shows "Starting..."
8. Page refreshes after start
9. Lifecycle Controls reappear
10. Connection Info reappears

---

## Testing

### **Test 1: Start from List**
```bash
# 1. Shutdown a deployment
curl -X POST http://localhost:8001/tenants/t5/deployments/test-5-deployment/actions/shutdown

# 2. Open UI
# Navigate to tenant page

# 3. Verify:
# - Status shows "○ Shutdown"
# - [Start] button is visible
# - Click [Start]
# - Button shows "Starting..."
# - Success message appears
# - Status updates to "◐ Starting"
```

### **Test 2: Detail Page When Shutdown**
```bash
# 1. With deployment shutdown
# Navigate to deployment detail page

# 2. Verify Overview tab:
# - Yellow banner shows "Deployment is Shutdown"
# - Only "Deployment Actions" section visible
# - Only [Start Deployment] button visible
# - NO Scale/Upgrade/Restart/Shutdown buttons
# - NO Connection Information section

# 3. Click [Start Deployment]
# - Button shows "Starting..."
# - Page refreshes
# - Lifecycle Controls appear
# - Connection Info appears
```

### **Test 3: Detail Page When Running**
```bash
# 1. With deployment running
# Navigate to deployment detail page

# 2. Verify Overview tab:
# - NO yellow banner
# - "Lifecycle Controls" section visible
# - All buttons visible: Scale, Upgrade, Restart, Shutdown
# - "Connection Information" section visible
# - NO "Deployment Actions" section
# - NO [Start Deployment] button
```

---

## Edge Cases Handled

### **1. Button Loading State**
- While starting, button shows "Starting..."
- Button is disabled during operation
- Prevents double-clicks

### **2. Immediate Status Refresh**
- After clicking Start, status refreshes immediately
- Doesn't wait for 10-second poll interval
- User sees status change right away

### **3. Multiple Shutdown Deployments**
- Each deployment has independent Start button
- Only the clicked deployment shows "Starting..."
- Others remain clickable

### **4. Navigation**
- Start button stops event propagation
- Doesn't expand/collapse row when clicked
- "Details" button still works normally

---

## CSS Classes Used

### **Start Button:**
```css
bg-green-600        # Green background
text-white          # White text
hover:bg-green-700  # Darker on hover
disabled:opacity-50 # Faded when disabled
disabled:cursor-not-allowed  # Shows not-allowed cursor
```

### **Conditional Rendering:**
```typescript
{deployment.status === 'shutdown' && (
  // Show Start button
)}

{deployment.status !== 'shutdown' && (
  // Show Lifecycle Controls and Connection Info
)}
```

---

## Files Modified

1. ✅ `ExpandableDeploymentList.tsx` - Added Start button and handler
2. ✅ `DeploymentDetailsPage.tsx` - Conditional rendering based on status

---

## Backward Compatibility

✅ **No breaking changes:**
- Existing running deployments work as before
- All lifecycle controls work for running deployments
- Connection info shows normally when running
- Only new behavior is for shutdown state

---

## Summary

### **What Changed:**
1. ✅ Added [Start] button on deployment list when shutdown
2. ✅ Hide Lifecycle Controls when deployment is shutdown
3. ✅ Hide Connection Info when deployment is shutdown
4. ✅ Show only [Start Deployment] button on detail page when shutdown
5. ✅ Immediate status refresh after starting

### **User Benefits:**
- ✨ Clear way to start shutdown deployments
- ✨ No confusing controls when shutdown
- ✨ Clean UI that matches deployment state
- ✨ Faster feedback (immediate refresh)

### **Result:**
Perfect UX for shutdown deployments! 🎉
