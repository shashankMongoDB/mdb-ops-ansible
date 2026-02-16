# Quick Test Guide - Progressive Status Disclosure

## 🚀 Quick Test (5 minutes)

### **Setup:**
```bash
# Restart frontend (no backend changes needed)
cd AtlasForge-UI-Vite
npm run dev

# Open browser
# Navigate to: http://localhost:5173
```

---

## ✅ Test Scenario: Create New Deployment

### **Step 1: Create Deployment**
```
1. Navigate to any tenant
2. Click [Create Deployment]
3. Fill form:
   - Deployment ID: progress-test
   - Type: ReplicaSet
   - MongoDB Version: 8.0.10
   - Members: 3
4. Click [Create]
```

---

### **Step 2: Immediately Check List (0-10 seconds)**

**Expected Behavior:**
```
┌─────────────────────────────────────────────────────┐
│  ▶ ○ progress-test (Pending)                        │
│     Pods: 0/3 | Version: 8.0.10                     │
│                                                      │
│     [🔄 Refresh]  [Details (Starting...)]           │
│                          ↑                           │
│                    GREYED OUT / DISABLED             │
└─────────────────────────────────────────────────────┘
```

**Verify:**
- ✅ Status shows ○ (hollow circle) with "Pending"
- ✅ Pods shows "0/3"
- ✅ [Details] button is disabled/greyed
- ✅ Shows "Details (Starting...)" text
- ✅ [🔄 Refresh] button is enabled

---

### **Step 3: Expand to See Progress**

**Action:**
```
Click the chevron (▶) or deployment name
```

**Expected View:**
```
┌─────────────────────────────────────────────────────┐
│  ▼ ○ progress-test (Pending)                        │
│     Pods: 0/3                                       │
│                                                      │
│     ┌───────────────────────────────────────────┐  │
│     │  🔄 Starting Up...                        │  │
│     │  Pods: 0/3 ready                          │  │
│     │                                            │  │
│     │  Progress                          0%     │  │
│     │  ░░░░░░░░░░░░░░░░░░░░                    │  │
│     │                                            │  │
│     │  This may take 2-3 minutes. The detail   │  │
│     │  page will be available once all pods    │  │
│     │  are running.                             │  │
│     │                                            │  │
│     │  Pod Status:                              │  │
│     │  ○ progress-test-0    Pending        ⏳  │  │
│     │  ○ progress-test-1    Pending        ⏳  │  │
│     │  ○ progress-test-2    Pending        ⏳  │  │
│     └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

**Verify:**
- ✅ Blue banner with spinning loader icon
- ✅ "Starting Up..." header
- ✅ "Pods: 0/3 ready" counter
- ✅ Progress bar (empty at 0%)
- ✅ Message: "This may take 2-3 minutes..."
- ✅ Pod Status section with all pods "Pending"
- ✅ ○ (hollow circle) for each pod
- ✅ ⏳ (hourglass) icon on pending pods

---

### **Step 4: Wait 20-30 Seconds, Click Refresh**

**Action:**
```
1. Wait 20-30 seconds
2. Click [🔄 Refresh] button
```

**Expected Update:**
```
┌─────────────────────────────────────────────────────┐
│  ▼ ◐ progress-test (Partial)                        │
│     Pods: 1/3                                       │
│                                                      │
│     ┌───────────────────────────────────────────┐  │
│     │  🔄 Starting Up...                        │  │
│     │  Pods: 1/3 ready                          │  │
│     │                                            │  │
│     │  Progress                         33%     │  │
│     │  ━━━━━━━━░░░░░░░░░░░░                    │  │
│     │                                            │  │
│     │  This may take 2-3 minutes...             │  │
│     │                                            │  │
│     │  Pod Status:                              │  │
│     │  ● progress-test-0    Running        ✓   │  │
│     │  ◐ progress-test-1    ContainerCreating   │  │
│     │  ○ progress-test-2    Pending        ⏳  │  │
│     └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

**Verify:**
- ✅ Status changed to ◐ (half circle) "Partial"
- ✅ Pods counter updated: "1/3 ready"
- ✅ Progress bar filled to 33%
- ✅ Pod-0: ● (filled circle) + "Running" + ✓
- ✅ Pod-1: ◐ (half circle) + "ContainerCreating"
- ✅ Pod-2: ○ (hollow circle) + "Pending" + ⏳
- ✅ [Details] button STILL disabled

---

### **Step 5: Wait 1-2 Minutes (All Pods Running)**

**Action:**
```
Wait for all pods to become running
(Or manually refresh a few times)
```

**Expected Final State:**
```
┌─────────────────────────────────────────────────────┐
│  ▼ ● progress-test (Running)                        │
│     Pods: 3/3                                       │
│                                                      │
│     ┌───────────────────────────────────────────┐  │
│     │  Pod Status:                              │  │
│     │  ● progress-test-0    Running        ✓   │  │
│     │  ● progress-test-1    Running        ✓   │  │
│     │  ● progress-test-2    Running        ✓   │  │
│     └───────────────────────────────────────────┘  │
│                                                      │
│     [Details]  ← NOW ENABLED!                       │
└─────────────────────────────────────────────────────┘
```

**Verify:**
- ✅ Status changed to ● (filled circle) "Running"
- ✅ Pods counter: "3/3"
- ✅ Progress bar: 100% (or progress view replaced by topology)
- ✅ All pods: ● + "Running" + ✓
- ✅ [Details] button NOW ENABLED (not greyed)
- ✅ Can click [Details] and navigate

---

### **Step 6: Test Navigation**

**Action A: Click [Details] Button**
```
Click the [Details] button
```

**Expected:**
- ✅ Navigates to deployment detail page
- ✅ Shows full deployment info
- ✅ Lifecycle controls visible
- ✅ Connection info visible

**Action B: Click Deployment Name (When Running)**
```
Click "progress-test" text
```

**Expected:**
- ✅ Also navigates to detail page
- ✅ Same as clicking [Details]

---

## ❌ Negative Tests

### **Test 1: Try Clicking Details When Pending**

**Action:**
```
1. Deployment in "Pending" or "Partial" state
2. Try to click [Details (Starting...)] button
```

**Expected:**
- ✅ Button does nothing (disabled)
- ✅ Cursor shows "not-allowed" icon
- ✅ No navigation occurs

---

### **Test 2: Click Deployment Name When Pending**

**Action:**
```
1. Deployment in "Pending" or "Partial" state
2. Click deployment name
```

**Expected:**
- ✅ Does NOT navigate
- ✅ Toggles expand instead
- ✅ Shows progress view
- ✅ Tooltip: "Details available when deployment is fully running"

---

### **Test 3: Direct URL Access**

**Action:**
```
1. Create deployment (wait for "Partial" state)
2. Copy deployment ID
3. Navigate directly to:
   http://localhost:5173/tenants/<tenant-id>/deployments/<deployment-id>
```

**Expected:**
- ✅ Page loads briefly
- ✅ Error toast appears:
   Title: "Deployment not ready"
   Message: "This deployment is still starting up..."
- ✅ Automatically redirects to tenant page
- ✅ Shows deployment list

---

## 🎨 Visual Checklist

### **Status Indicators:**
```
○ Pending   - Hollow circle, gray
◐ Partial   - Half circle, yellow
● Running   - Filled circle, green
✗ Error     - X mark, red
○ Shutdown  - Hollow circle, gray
```

### **Progress Bar Colors:**
```
Container: bg-blue-200 (light blue)
Fill:      bg-blue-600 (darker blue)
Animation: Smooth transition (duration-500)
```

### **Button States:**
```
[🔄 Refresh]               - Blue border, blue text
[Details (Starting...)]    - Gray text, disabled, not clickable
[Details]                  - Black border, black text, clickable
```

### **Pod Status Badges:**
```
Running:            bg-green-100 text-green-800
Pending:            bg-yellow-100 text-yellow-800
ContainerCreating:  bg-gray-100 text-gray-800
```

---

## 🐛 Troubleshooting

### **Issue: Details button not disabled**

**Check:**
```javascript
// In browser console (F12)
console.log(status?.status);

// Should see: "pending" or "partial"
// NOT "running"
```

**Fix:**
- Clear browser cache (Ctrl+Shift+R)
- Restart dev server
- Check status API response

---

### **Issue: Progress bar not showing**

**Check:**
```javascript
// In browser console
console.log(status?.readyReplicas);
console.log(status?.totalReplicas);

// Should see numbers like: 1, 3
```

**Fix:**
- Verify backend returning status correctly
- Check status API endpoint
- Verify pods exist in Kubernetes

---

### **Issue: Redirect not working**

**Check:**
```javascript
// In DeploymentDetailsPage.tsx
console.log('Deployment status:', deployment?.status);

// Should trigger redirect if "pending" or "partial"
```

**Fix:**
- Check useEffect dependencies
- Verify navigate function imported
- Check browser console for errors

---

## 📊 Success Criteria

After all tests pass:

- ✅ [Details] button disabled for pending/partial deployments
- ✅ Progress view shows when expanded
- ✅ Spinning loader animates smoothly
- ✅ Progress bar updates from 0% → 33% → 67% → 100%
- ✅ Pod status shows individual states
- ✅ [🔄 Refresh] button updates status
- ✅ [Details] enables when all pods running
- ✅ Deployment name click behavior changes based on status
- ✅ Direct URL access redirects if not ready
- ✅ No errors in console

---

## ⏱️ Expected Timings

```
0s    - Create deployment
5s    - Appears in list as "Pending" (0/3 pods)
30s   - Changes to "Partial" (1/3 pods)
60s   - More pods starting (2/3 pods)
120s  - All pods "Running" (3/3 pods)
      - [Details] button enables
      - Can navigate successfully
```

---

## 🎯 Quick Verification Commands

```bash
# Check deployment status via API
curl http://localhost:8001/tenants/<tenant-id>/deployments/<deployment-id>

# Check all deployments status
curl http://localhost:8001/tenants/<tenant-id>/deployments-status

# Check pods in Kubernetes
kubectl get pods -n mdb-<tenant-id>

# Watch pods come up
kubectl get pods -n mdb-<tenant-id> -w
```

---

## 📝 Notes

- Auto-polling every 10 seconds (you don't have to keep clicking refresh)
- Progress view only shows for pending/partial (not for running/shutdown)
- [Details] button text changes to show current state
- All animations are CSS-based (performant)
- No backend changes required (frontend only)

---

**Test Complete!** 🎉

If all verifications pass, progressive status disclosure is working perfectly!
