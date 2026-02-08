# FastAPI Changes - Fix 405 Method Not Allowed

## Summary

Added missing `GET /tenants` and `GET /tenants/{tenantId}` endpoints to fix the 405 error.

## Changes Made

### 1. **app/main.py** - Added GET endpoints

#### Added: `GET /tenants` endpoint
```python
@app.get("/tenants", response_model=List[dict])
def list_tenants():
    """List all tenants"""
    try:
        tenants = tenants_service.list_tenants()
        return tenants
    except Exception as e:
        logger.exception("Error listing tenants")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
```

#### Added: `GET /tenants/{tenantId}` endpoint
```python
@app.get("/tenants/{tenantId}", response_model=dict)
def get_tenant(tenantId: str = Path(..., description="Tenant identifier")):
    """Get a specific tenant by ID"""
    try:
        tenant = tenants_service.get_tenant(tenant_id=tenantId)
        if not tenant:
            raise HTTPException(status_code=404, detail=f"Tenant {tenantId} not found")
        return tenant
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting tenant")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
```

#### Added: CORS Middleware
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. **app/services/tenants_service.py** - Added service functions

#### Added: `list_tenants()` function
```python
def list_tenants() -> List[Dict[str, Any]]:
    """List all tenants"""
    repo = get_repo()
    tenants = repo.list_tenants()
    
    # Remove MongoDB _id field
    result = []
    for tenant in tenants:
        if '_id' in tenant:
            tenant.pop('_id')
        result.append(tenant)
    
    return result
```

#### Added: `get_tenant()` function
```python
def get_tenant(tenant_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific tenant by ID"""
    repo = get_repo()
    tenant = repo.get_tenant(tenant_id)
    
    if tenant and '_id' in tenant:
        tenant.pop('_id')
    
    return tenant
```

### 3. **app/services/mongo_repo.py** - Added repository method

#### Added: `list_tenants()` method
```python
def list_tenants(self) -> list[Dict[str, Any]]:
    """List all tenants"""
    return list(self.tenants.find())
```

## What Was Fixed

### Before (Issues)
- ❌ `GET /tenants` - 405 Method Not Allowed
- ❌ `GET /tenants/{id}` - Not implemented
- ❌ CORS errors when UI tries to connect

### After (Fixed)
- ✅ `GET /tenants` - Returns list of all tenants
- ✅ `GET /tenants/{id}` - Returns specific tenant
- ✅ CORS enabled - UI can connect from any origin

## API Endpoints Now Available

```
GET    /health                                         - Health check
GET    /tenants                                        - List all tenants ✨ NEW
GET    /tenants/{id}                                   - Get specific tenant ✨ NEW
POST   /tenants                                        - Create tenant
DELETE /tenants/{id}                                   - Delete tenant
GET    /tenants/{id}/deployments                       - List deployments
POST   /tenants/{id}/deployments                       - Create deployment
GET    /tenants/{id}/deployments/{did}                 - Get deployment
DELETE /tenants/{id}/deployments/{did}                 - Delete deployment
GET    /tenants/{id}/deployments/{did}/connection      - Get connection info
PATCH  /tenants/{id}/deployments/{did}/scale          - Scale deployment
PATCH  /tenants/{id}/deployments/{did}/version        - Upgrade version
POST   /tenants/{id}/deployments/{did}/actions/shutdown - Shutdown
POST   /tenants/{id}/deployments/{did}/actions/start    - Start
POST   /tenants/{id}/deployments/{did}/actions/restart  - Restart
GET    /tenants/{id}/deployments/{did}/monitoring/prometheus - Get Prometheus config
PATCH  /tenants/{id}/deployments/{did}/monitoring/prometheus - Update Prometheus
```

## How to Apply Changes

### If Running Locally
```bash
# Stop the current server (Ctrl+C)

# Restart the server
cd /path/to/AtlasForge
python -m app.main

# Or with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### If Running on Ubuntu Server
```bash
# SSH to server
ssh ubuntu@ec2-34-213-34-101.us-west-2.compute.amazonaws.com

# Navigate to project
cd ~/path/to/AtlasForge

# Pull latest changes (if using git)
git pull

# Restart service
# Option 1: Kill and restart
ps aux | grep uvicorn
kill <PID>
uvicorn app.main:app --host 0.0.0.0 --port 8001

# Option 2: If using systemd
sudo systemctl restart mdb-control-plane

# Option 3: If using supervisor
sudo supervisorctl restart mdb-control-plane
```

## Testing

### 1. Test GET /tenants
```bash
curl http://ec2-34-213-34-101.us-west-2.compute.amazonaws.com:8001/tenants

# Expected: [] or [{"tenantId": "t-acme", "displayName": "Acme Corp", ...}]
```

### 2. Test GET /tenants/{id}
```bash
curl http://ec2-34-213-34-101.us-west-2.compute.amazonaws.com:8001/tenants/t-acme

# Expected: {"tenantId": "t-acme", "displayName": "Acme Corp", ...}
# Or 404 if tenant doesn't exist
```

### 3. Check FastAPI Docs
Open in browser:
```
http://ec2-34-213-34-101.us-west-2.compute.amazonaws.com:8001/docs
```

You should now see:
- ✅ GET /tenants
- ✅ GET /tenants/{tenantId}

### 4. Test from UI
```bash
# Start the Vite UI
cd AtlasForge-UI-Vite
npm run dev

# Open http://localhost:3000
# Should now load tenants without 405 error!
```

## Response Format

### GET /tenants
```json
[
  {
    "tenantId": "t-acme",
    "displayName": "Acme Corporation",
    "namespace": "mdb-t-acme",
    "status": "Active",
    "createdAt": "2026-02-09T10:30:00Z",
    "opsManager": {
      "projectName": "mdb-t-acme-project"
    }
  }
]
```

### GET /tenants/{id}
```json
{
  "tenantId": "t-acme",
  "displayName": "Acme Corporation",
  "namespace": "mdb-t-acme",
  "status": "Active",
  "createdAt": "2026-02-09T10:30:00Z",
  "opsManager": {
    "projectName": "mdb-t-acme-project"
  }
}
```

## Files Modified

1. ✅ `AtlasForge/app/main.py` - Added GET endpoints and CORS
2. ✅ `AtlasForge/app/services/tenants_service.py` - Added service functions
3. ✅ `AtlasForge/app/services/mongo_repo.py` - Added repository method

## Commit Changes

```bash
cd /Users/shashank.pandey/Desktop/Codebase/MDBaaS/Github-repo/mdb-ops-ansible

git add AtlasForge/app/main.py
git add AtlasForge/app/services/tenants_service.py
git add AtlasForge/app/services/mongo_repo.py

git commit -m "Fix: Add missing GET /tenants and GET /tenants/{id} endpoints

- Added GET /tenants endpoint to list all tenants
- Added GET /tenants/{id} endpoint to get specific tenant
- Added CORS middleware to allow UI connections
- Added list_tenants() and get_tenant() service functions
- Added list_tenants() repository method

Fixes 405 Method Not Allowed error when UI tries to fetch tenants."

git push origin main
```

## Success Indicators

After restarting the microservice, you should see:

✅ No more 405 errors in logs  
✅ UI loads tenants successfully  
✅ GET requests return JSON data  
✅ FastAPI docs show new endpoints  
✅ CORS headers present in responses  

---

**Status:** ✅ All changes complete - Ready to restart microservice!
