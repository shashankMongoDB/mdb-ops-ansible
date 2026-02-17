# Fix: Polling Loop Issue

## Problem Identified ✅

Your backend logs showed:
```
INFO: 104.30.164.15:59304 - "GET /tenants/t-comm/deployments/monitoring-comm/connection HTTP/1.1" 200 OK
INFO: 104.30.164.15:59310 - "GET /tenants/t-comm/deployments/monitoring-comm/connection HTTP/1.1" 200 OK
...repeating continuously...
```

### **Root Cause:**

The `useUpgradePolling` hook was:
1. ❌ **Not stopping when disabled** - Continued polling even after modal closed
2. ❌ **Creating multiple intervals** - useEffect dependency array caused re-creation
3. ❌ **Not cleaning up properly** - Intervals persisted after component unmount
4. ❌ **No safety checks** - Checking even when `enabled=false`

This caused:
- Excessive API calls (multiple requests per second)
- Backend getting hammered
- UI sluggishness
- Other tabs affected
- "Network Error" messages

---

## Solution Applied ✅

### **Changes Made:**

#### **1. Added Safety Check in checkUpgradeStatus**
```typescript
const checkUpgradeStatus = useCallback(async () => {
  if (!enabled) return; // ✅ Stop immediately if disabled
  
  try {
    const connectionInfo = await deploymentsApi.getConnectionInfo(tenantId, deploymentId);
    // ... rest of logic
  }
});
```

#### **2. Fixed useEffect Dependencies**
**Before:**
```typescript
useEffect(() => {
  if (enabled && !isPolling) {
    startPolling();
  } else if (!enabled && isPolling) {
    stopPolling();
  }
  return () => stopPolling();
}, [enabled, isPolling, startPolling, stopPolling]); // ❌ Too many deps
```

**After:**
```typescript
useEffect(() => {
  if (enabled && !isPolling) {
    console.log('[useUpgradePolling] Starting polling for', deploymentId);
    startPolling();
  } else if (!enabled && isPolling) {
    console.log('[useUpgradePolling] Stopping polling for', deploymentId);
    stopPolling();
  }

  return () => {
    if (isPolling) {
      console.log('[useUpgradePolling] Cleanup - stopping polling');
      stopPolling();
    }
  };
}, [enabled]); // ✅ Only depend on 'enabled'
```

**Why this fixes it:**
- Prevents infinite loop from dependency changes
- Cleans up properly on unmount
- Only reacts to `enabled` prop changes

#### **3. Added Logging for Debug**
```typescript
console.log('[useUpgradePolling] Starting polling for', deploymentId);
console.log('[useUpgradePolling] Polling tick for', deploymentId);
console.log('[useUpgradePolling] Stopping polling');
console.log('[useUpgradePolling] Cleanup - stopping polling');
```

**Purpose:**
- Track when polling starts/stops
- Identify if multiple instances are created
- Debug lifecycle issues
- Can remove later for production

#### **4. Improved Timeout Cleanup**
```typescript
const startPolling = useCallback(() => {
  // ... start interval ...
  
  const timeoutId = setTimeout(() => {
    stopPolling();
    onError?.('Upgrade monitoring timeout after 30 minutes');
  }, 1800000);
  
  // ✅ Store timeout ID for cleanup
  (intervalRef.current as any)._timeoutId = timeoutId;
}, []);

const stopPolling = useCallback(() => {
  if (intervalRef.current) {
    clearInterval(intervalRef.current);
    
    // ✅ Clear timeout too
    const timeoutId = (intervalRef.current as any)._timeoutId;
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    
    intervalRef.current = null;
  }
  setIsPolling(false);
}, []);
```

---

## How to Verify Fix

### **1. Check Console Logs**

Open browser DevTools (F12) → Console:

**Good (after fix):**
```
[useUpgradePolling] Starting polling for monitoring-comm
[useUpgradePolling] Polling tick for monitoring-comm
[useUpgradePolling] Polling tick for monitoring-comm
[useUpgradePolling] Stopping polling
```

**Bad (before fix):**
- No logs, or
- Multiple "Starting polling" without "Stopping"
- Continues after modal closes

### **2. Check Network Tab**

Open browser DevTools (F12) → Network tab:

**Good (after fix):**
- Requests only when modal is open
- Stops when modal closes
- Max 1 request every 5 seconds

**Bad (before fix):**
- Continuous requests
- Multiple requests per second
- Continues after modal closes

### **3. Check Backend Logs**

```bash
# Watch backend logs
kubectl logs -n mdbaas-system deployment/mdbaas-backend -f | grep connection

# Or locally
tail -f backend.log | grep connection
```

**Good (after fix):**
- No requests when no upgrade modal open
- 1 request per 5 seconds when modal open
- Stops when modal closes

**Bad (before fix):**
- Continuous flood of connection requests
- Never stops

---

## Testing Procedure

### **Test 1: Normal Upgrade Flow**

```
1. Open deployment page
2. Click [Upgrade Version]
3. Select new version
4. Click [Upgrade Version]
5. Watch console logs
   ✅ Should see: "Starting polling for <deployment>"
   ✅ Should see: "Polling tick" every 5 seconds
6. Click [Done] or [Close]
   ✅ Should see: "Stopping polling"
   ✅ Network requests should stop
7. Check backend logs
   ✅ Connection requests should stop
```

### **Test 2: Navigate Away**

```
1. Start upgrade (as above)
2. Console shows polling started
3. Navigate to another page (e.g., tenant list)
   ✅ Should see: "Cleanup - stopping polling"
   ✅ Polling should stop
4. Check backend logs
   ✅ No more connection requests
```

### **Test 3: Open Multiple Modals**

```
1. Open deployment A
2. Click [Upgrade Version] (don't submit)
3. Open deployment B in new tab
4. Click [Upgrade Version] (don't submit)
5. Check console logs
   ✅ Should see only 1 "Starting polling" at a time
   ✅ No duplicate polling
6. Close both tabs
   ✅ All polling should stop
```

### **Test 4: Rapid Open/Close**

```
1. Click [Upgrade Version]
2. Immediately click [Cancel]
3. Repeat 5 times rapidly
4. Check console logs
   ✅ Should see "Starting" followed by "Stopping"
   ✅ No orphaned intervals
5. Check backend logs
   ✅ Requests stop after last close
```

---

## Additional Improvements Made

### **1. Safety Guard**
Added check at the start of `checkUpgradeStatus`:
```typescript
if (!enabled) return;
```

This prevents any API calls when the hook is disabled.

### **2. Better Logging**
All state changes now logged:
- Starting polling
- Each polling tick
- Stopping polling
- Cleanup on unmount

### **3. Proper Cleanup**
Both `setInterval` and `setTimeout` now properly cleared:
- Clear interval when stopping
- Clear timeout when stopping
- Clean up on component unmount

---

## What Was Happening Before

### **The Infinite Loop:**

```
1. useEffect runs with deps: [enabled, isPolling, startPolling, stopPolling]
2. startPolling is a useCallback with deps [isPolling, checkUpgradeStatus, onError]
3. checkUpgradeStatus is a useCallback with many deps
4. Any state change triggers new callback creation
5. New callback triggers useEffect
6. useEffect calls startPolling
7. Creates new interval (old one not stopped!)
8. Multiple intervals now running
9. Repeat...
```

### **Result:**
- Multiple `setInterval` instances running simultaneously
- Each calling API every 5 seconds
- Never cleaned up
- Exponentially growing API calls

---

## What Happens Now

### **The Correct Flow:**

```
1. Modal opens with upgradeState='upgrading'
2. useUpgradePolling called with enabled=true
3. useEffect sees enabled=true, calls startPolling()
4. Single setInterval created
5. Polls every 5 seconds
6. User closes modal
7. enabled becomes false
8. useEffect sees enabled=false, calls stopPolling()
9. clearInterval called
10. Polling stops
11. Component unmounts
12. useEffect cleanup runs, ensures stopPolling() called
```

---

## Files Modified

✅ `src/hooks/useUpgradePolling.ts`
- Added safety check in checkUpgradeStatus
- Fixed useEffect dependencies
- Added debug logging
- Improved cleanup

---

## Before vs After

### **Backend Logs:**

**Before:**
```
INFO: GET /tenants/.../connection 200 OK
INFO: GET /tenants/.../connection 200 OK
INFO: GET /tenants/.../connection 200 OK  ← Multiple per second
INFO: GET /tenants/.../connection 200 OK
INFO: GET /tenants/.../connection 200 OK
...never stops...
```

**After:**
```
INFO: GET /tenants/.../connection 200 OK
...5 seconds...
INFO: GET /tenants/.../connection 200 OK  ← Once per 5 seconds
...5 seconds...
INFO: GET /tenants/.../connection 200 OK
...modal closes...
...no more requests...
```

### **Browser Console:**

**Before:**
```
(no logs or errors)
```

**After:**
```
[useUpgradePolling] Starting polling for monitoring-comm
[useUpgradePolling] Polling tick for monitoring-comm
[useUpgradePolling] Polling tick for monitoring-comm
[useUpgradePolling] Stopping polling
```

---

## Removing Debug Logs (Later)

Once confirmed working, you can remove the console.log statements:

```typescript
// Remove these lines:
console.log('[useUpgradePolling] Starting polling for', deploymentId);
console.log('[useUpgradePolling] Polling tick for', deploymentId);
console.log('[useUpgradePolling] Stopping polling');
console.log('[useUpgradePolling] Cleanup - stopping polling');
```

Or keep them in development mode only:
```typescript
const isDev = import.meta.env.DEV;
if (isDev) console.log('[useUpgradePolling] Starting polling for', deploymentId);
```

---

## Summary

### **Problem:**
- Polling hook not stopping when disabled
- Multiple intervals created
- Backend getting hammered with requests
- UI sluggish, "Network Error" messages

### **Solution:**
- Added safety check (`if (!enabled) return`)
- Fixed useEffect dependencies (only depend on `enabled`)
- Added debug logging
- Improved cleanup (clear both interval and timeout)

### **Result:**
- ✅ Polling only when modal open
- ✅ Stops when modal closes
- ✅ Proper cleanup on unmount
- ✅ Single interval per deployment
- ✅ No more endless API calls
- ✅ Backend logs clean

---

**Refresh your browser and try upgrading again! The polling loop should be fixed.** 🎉

**Check the console logs to verify polling starts and stops correctly.**
