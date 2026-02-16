# MDBaaS Control Plane - Debug Guide

## Debugging "Nothing Happens" Issues

### Scenario: Button Click Does Nothing

When clicking a button (like Shutdown, Restart, etc.) and nothing happens:

---

## Step 1: Check Browser Console

**Open Developer Tools:**
- Chrome/Edge: Press `F12` or `Ctrl+Shift+I` (Windows) / `Cmd+Option+I` (Mac)
- Firefox: Press `F12` or `Ctrl+Shift+K`

**Look for:**
1. **JavaScript Errors** (Red text in Console tab)
   ```
   Uncaught TypeError: Cannot read property 'x' of undefined
   ReferenceError: xyz is not defined
   ```

2. **Network Errors**
   ```
   Failed to fetch
   net::ERR_CONNECTION_REFUSED
   CORS error
   ```

3. **API Call Failures**
   ```
   POST http://localhost:8001/tenants/.../actions/shutdown 404 (Not Found)
   POST http://localhost:8001/tenants/.../actions/shutdown 500 (Internal Server Error)
   ```

**Take Action:**
- Screenshot the error
- Copy the error message
- Check if backend is running

---

## Step 2: Check Network Tab

**In Developer Tools → Network Tab:**

1. **Clear existing requests** (trash icon)
2. **Click the button** (Shutdown, Restart, etc.)
3. **Look for the POST request** to `/actions/shutdown` or `/actions/restart`

**If you see the request:**

### Request Status: 200 OK ✅
- Success! But UI might not be updating
- Check if there's a success toast notification
- Refresh the page manually

### Request Status: 404 Not Found ❌
- **Problem:** API endpoint not found
- **Check:**
  - Is backend running? `curl http://localhost:8001/health`
  - Correct URL? Check `VITE_API_BASE_URL` in `.env`
  - Correct tenant/deployment IDs?

### Request Status: 500 Internal Server Error ❌
- **Problem:** Backend error
- **Check backend logs:**
  ```bash
  # If running with uvicorn
  # Look at terminal where backend is running
  
  # Or check logs file
  tail -f /var/log/mdbaas/backend.log
  ```

### Request Status: 0 or CORS Error ❌
- **Problem:** Backend not reachable or CORS issue
- **Check:**
  - Backend running? `curl http://localhost:8001/health`
  - Correct URL in `.env`?
  - CORS enabled in backend (should be by default)

### No Request at All ❌
- **Problem:** JavaScript error preventing the request
- **Check Console tab** for errors
- **Possible causes:**
  - Missing tenant/deployment ID
  - Button disabled
  - Event handler not attached

---

## Step 3: Test API Directly

**Test with curl:**

```bash
# 1. Health check
curl http://localhost:8001/health

# Expected: {"status":"healthy"}

# 2. List tenants
curl http://localhost:8001/tenants

# Expected: [{"tenantId":"...","displayName":"..."}]

# 3. Test shutdown (replace IDs)
curl -X POST http://localhost:8001/tenants/YOUR_TENANT_ID/deployments/YOUR_DEPLOYMENT_ID/actions/shutdown -v

# Expected: 200 OK with JSON response
```

**Common Issues:**

### Connection Refused
```
curl: (7) Failed to connect to localhost port 8001: Connection refused
```
**Solution:** Backend is not running. Start it:
```bash
cd AtlasForge
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### 404 Not Found
```
{"detail":"Tenant xyz not found"}
```
**Solution:** Wrong tenant ID. Check correct ID:
```bash
curl http://localhost:8001/tenants
```

### 500 Internal Server Error
```
{"detail":"Internal error: ..."}
```
**Solution:** Check backend logs for Python traceback

---

## Step 4: Check Backend Logs

**If running uvicorn directly:**
```bash
# The terminal where you ran uvicorn shows logs
# Look for lines like:

INFO:     104.30.164.15:49156 - "POST /tenants/test-sharded/deployments/sh-orders/actions/shutdown HTTP/1.1" 200 OK

# Or errors:
ERROR - Error in shutdown_deployment
Traceback (most recent call last):
  ...
```

**Enable debug logging:**
```bash
# In .env or environment
export MCP_LOG_LEVEL=DEBUG

# Restart backend
pkill -f uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

---

## Step 5: Check Kubernetes Resources

**After clicking Shutdown, check if it worked:**

```bash
# For ShardedCluster
kubectl get statefulsets -n mdb-YOUR_NAMESPACE | grep YOUR_DEPLOYMENT

# Expected: All replicas should be 0/0
# sh-orders-shard-0   0/0     0s
# sh-orders-shard-1   0/0     0s
# sh-orders-configsvr 0/0     0s

# For ReplicaSet
kubectl get statefulsets YOUR_DEPLOYMENT -n mdb-YOUR_NAMESPACE

# For Standalone
kubectl get deployment YOUR_DEPLOYMENT-db -n mdb-YOUR_NAMESPACE

# Check pods
kubectl get pods -n mdb-YOUR_NAMESPACE | grep YOUR_DEPLOYMENT

# Expected: All pods should be Terminating or 0/1
```

---

## Common Issues and Solutions

### Issue 1: Button is Greyed Out / Disabled

**Check:**
```javascript
// In browser console
console.log(document.querySelector('button').disabled)
// If true, button is disabled
```

**Solution:** Button might be disabled due to:
- Loading state
- Missing permissions
- Deployment in wrong state

### Issue 2: Modal Doesn't Appear

**Check:**
```javascript
// In browser console
console.log('Modal open state:', confirmAction)
// Should change when you click the button
```

**Solution:**
- Check if `setConfirmAction` is being called
- Look for JavaScript errors

### Issue 3: API Call Succeeds but UI Doesn't Update

**Symptoms:**
- Network tab shows 200 OK
- No error in console
- UI doesn't change

**Solution:**
```javascript
// Check if data refresh is called
// In DeploymentDetailsPage.tsx, loadData() should be called after action

// Manually refresh data
location.reload()
```

### Issue 4: CORS Error

**Error:**
```
Access to XMLHttpRequest at 'http://localhost:8001/...' from origin 'http://localhost:5173' 
has been blocked by CORS policy
```

**Solution:**
Backend CORS should already be enabled, but verify:
```python
# In app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Should allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Quick Diagnostic Commands

**Run all at once:**

```bash
# 1. Check backend health
curl http://localhost:8001/health && echo " ✓ Backend healthy" || echo " ✗ Backend down"

# 2. Check if API responds
curl -X POST http://localhost:8001/tenants/test-tenant/deployments/test-deploy/actions/shutdown 2>&1 | head -5

# 3. Check frontend is running
curl http://localhost:5173 > /dev/null 2>&1 && echo " ✓ Frontend running" || echo " ✗ Frontend down"

# 4. Check Kubernetes connectivity
kubectl cluster-info > /dev/null 2>&1 && echo " ✓ K8s accessible" || echo " ✗ K8s not accessible"
```

---

## Enable Verbose Logging

### Backend Verbose Logs

**Method 1: Environment Variable**
```bash
export MCP_LOG_LEVEL=DEBUG
pkill -f uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

**Method 2: Add Print Statements**
```python
# In lifecycle_service.py
def shutdown_deployment(tenant_id: str, deployment_id: str):
    print(f"[DEBUG] Shutting down {tenant_id}/{deployment_id}")
    # ... rest of code
    print(f"[DEBUG] Shutdown completed")
```

### Frontend Verbose Logs

**Add console.logs:**
```typescript
// In DeploymentDetailsPage.tsx
const handleAction = async (action: ActionType) => {
  console.log('[DEBUG] handleAction called:', action);
  console.log('[DEBUG] tenantId:', tenantId, 'deploymentId:', deploymentId);
  
  try {
    console.log('[DEBUG] Calling API...');
    await deploymentsApi.shutdown(tenantId, deploymentId);
    console.log('[DEBUG] API call succeeded');
  } catch (error) {
    console.error('[DEBUG] API call failed:', error);
  }
};
```

---

## Still Not Working?

### Collect Debug Info

```bash
# Create debug report
cat > debug-report.txt << EOF
=== MDBaaS Debug Report ===

1. Backend Health:
$(curl -s http://localhost:8001/health)

2. Backend Version:
$(curl -s http://localhost:8001/docs | grep -o 'version.*' | head -1)

3. Tenants:
$(curl -s http://localhost:8001/tenants)

4. Frontend URL:
$(cat AtlasForge-UI-Vite/.env | grep VITE_API_BASE_URL)

5. Backend Running:
$(ps aux | grep uvicorn)

6. Kubernetes Accessible:
$(kubectl cluster-info)

7. Recent Backend Logs:
$(tail -20 <path-to-backend-logs>)
EOF

cat debug-report.txt
```

### Check GitHub Issues
- Search for similar issues
- Check if it's a known bug

### Ask for Help
Provide:
1. Browser console screenshot
2. Network tab screenshot showing the failed request
3. Backend logs (last 50 lines)
4. Steps to reproduce

---

## Prevention: Enable Better Error Handling

### Add Toast Notifications

Already implemented in the code, but verify they appear:
```typescript
showError('Failed to shutdown deployment', error.detail || 'An error occurred');
```

### Add Loading Indicators

Check if button shows loading state:
```typescript
<button disabled={actionLoading}>
  {actionLoading ? 'Shutting down...' : 'Shutdown'}
</button>
```

---

**Remember:** 90% of "nothing happens" issues are:
1. Backend not running (50%)
2. JavaScript error in console (30%)
3. Wrong API URL in .env (10%)
4. CORS issues (5%)
5. Other (5%)

Always check these in order!
