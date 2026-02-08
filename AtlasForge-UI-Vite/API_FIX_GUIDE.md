# 405 Method Not Allowed - Fix Guide

## Problem

Getting `405 Method Not Allowed` for `GET /tenants` from your FastAPI microservice.

This means the endpoint either:
1. Doesn't exist
2. Only accepts POST but you're calling GET
3. Has incorrect route definition

---

## Solution

### Step 1: Check Your FastAPI Code

Your microservice needs a GET endpoint for `/tenants`. It should look like:

```python
from fastapi import FastAPI, HTTPException
from typing import List

app = FastAPI()

# This is what you NEED
@app.get("/tenants", response_model=List[dict])
async def get_tenants():
    """List all tenants"""
    # Your logic to fetch tenants from MongoDB
    tenants = []  # Replace with actual MongoDB query
    return tenants
```

### Step 2: Common Issues

#### Issue 1: Missing GET Endpoint

**Wrong:**
```python
# Only POST, no GET
@app.post("/tenants")
async def create_tenant(tenant: TenantCreate):
    # ...
```

**Fixed:**
```python
# Add GET endpoint
@app.get("/tenants")
async def list_tenants():
    # Fetch from MongoDB
    tenants = await db.tenants.find().to_list(None)
    return tenants

@app.post("/tenants")
async def create_tenant(tenant: TenantCreate):
    # ...
```

#### Issue 2: Wrong Route Path

**Wrong:**
```python
@app.get("/tenant")  # Singular, but UI calls /tenants (plural)
async def get_tenants():
    # ...
```

**Fixed:**
```python
@app.get("/tenants")  # Must match UI expectation
async def get_tenants():
    # ...
```

#### Issue 3: Router Prefix Issue

**Wrong:**
```python
from fastapi import APIRouter

router = APIRouter(prefix="/api")

@router.get("/tenants")  # This becomes /api/tenants
async def get_tenants():
    # ...
```

**Fixed Option 1:**
```python
# Remove prefix
router = APIRouter()

@router.get("/tenants")
async def get_tenants():
    # ...
```

**Fixed Option 2:**
```python
# Keep prefix, update UI
# In UI .env file:
# VITE_API_BASE_URL=http://your-server:8001/api
```

---

## Complete FastAPI Example

Here's what your microservice should have:

```python
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import List, Optional
import os

app = FastAPI(title="MongoDB Control Plane API")

# CORS (important for UI to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your UI domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGODB_URI = os.getenv("MCP_MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MCP_DB_NAME", "mdb_control_plane")

client = AsyncIOMotorClient(MONGODB_URI)
db = client[DB_NAME]

# Models
class TenantCreate(BaseModel):
    tenantId: str
    displayName: Optional[str] = None
    environment: Optional[str] = None
    notes: Optional[str] = None

class Tenant(BaseModel):
    tenantId: str
    displayName: Optional[str] = None
    namespace: Optional[str] = None
    environment: Optional[str] = None
    notes: Optional[str] = None
    createdAt: Optional[str] = None

# REQUIRED: GET /tenants endpoint
@app.get("/tenants", response_model=List[Tenant])
async def list_tenants():
    """List all tenants"""
    try:
        tenants = await db.tenants.find().to_list(None)
        # Convert MongoDB _id to string or remove it
        for tenant in tenants:
            if '_id' in tenant:
                tenant.pop('_id')
        return tenants
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tenants", status_code=status.HTTP_201_CREATED)
async def create_tenant(tenant: TenantCreate):
    """Create a new tenant"""
    # Check if exists
    existing = await db.tenants.find_one({"tenantId": tenant.tenantId})
    if existing:
        raise HTTPException(status_code=409, detail="Tenant already exists")
    
    # Create tenant
    tenant_dict = tenant.dict()
    await db.tenants.insert_one(tenant_dict)
    return tenant_dict

@app.get("/tenants/{tenant_id}", response_model=Tenant)
async def get_tenant(tenant_id: str):
    """Get a specific tenant"""
    tenant = await db.tenants.find_one({"tenantId": tenant_id})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    if '_id' in tenant:
        tenant.pop('_id')
    return tenant

# Health check
@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

---

## Quick Fix Steps

### 1. Check What Endpoints Exist

Run this in terminal:
```bash
# On your microservice server
curl http://localhost:8001/docs

# Or check OpenAPI spec
curl http://localhost:8001/openapi.json
```

This shows all available endpoints. Look for:
- ✅ `GET /tenants` should be listed
- ✅ `POST /tenants` should be listed

### 2. Test Endpoint Directly

```bash
# Test if GET /tenants works
curl http://ec2-34-213-34-101.us-west-2.compute.amazonaws.com:8001/tenants

# Expected: JSON array of tenants (even if empty: [])
# If 405: Endpoint doesn't exist or wrong method
```

### 3. Check FastAPI Code

Look for this in your microservice code:
```python
@app.get("/tenants")  # Must have this!
async def list_tenants():
    # ...
```

### 4. Common Patterns to Check

**Pattern 1: Using APIRouter**
```python
from fastapi import APIRouter

# Check if using router
tenant_router = APIRouter()

@tenant_router.get("/tenants")
async def list_tenants():
    # ...

# Make sure it's included in app
app.include_router(tenant_router)  # MUST HAVE THIS!
```

**Pattern 2: Using prefix**
```python
app.include_router(tenant_router, prefix="/api")
# This makes endpoint: /api/tenants (not /tenants)
```

---

## Fix Based on Your Code Structure

### If you have the endpoint but still 405:

**1. Check HTTP method**
```python
# Wrong
@app.post("/tenants")  # UI is calling GET, but this is POST
async def get_tenants():
    # ...

# Right
@app.get("/tenants")  # Must be GET
async def get_tenants():
    # ...
```

**2. Check for typos**
```python
# Wrong
@app.get("/tenant")  # Singular

# Right  
@app.get("/tenants")  # Plural
```

**3. Check if router is included**
```python
# If using router, make sure it's added:
app.include_router(tenant_router)  # Must have this!
```

---

## Testing

### 1. Check FastAPI Docs
Navigate to: http://ec2-34-213-34-101.us-west-2.compute.amazonaws.com:8001/docs

You should see:
- `GET /tenants` - List all tenants
- `POST /tenants` - Create tenant
- etc.

### 2. Test with curl
```bash
# Should return JSON array (even if empty)
curl http://ec2-34-213-34-101.us-west-2.compute.amazonaws.com:8001/tenants

# Expected: []
# or: [{"tenantId": "t-acme", "displayName": "Acme Corp"}]

# If 405: Endpoint missing or wrong method
```

### 3. Check CORS
If endpoint exists but UI still fails:
```python
# Add CORS to FastAPI
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify your UI domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Minimal Working Example

Save this as `test_api.py` and run to verify:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Test data
tenants = [
    {"tenantId": "t-test", "displayName": "Test Tenant"}
]

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/tenants")
def list_tenants():
    return tenants

@app.post("/tenants")
def create_tenant(tenant: dict):
    tenants.append(tenant)
    return tenant

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

Run:
```bash
python test_api.py
```

Test:
```bash
curl http://localhost:8001/tenants
# Should return: [{"tenantId": "t-test", "displayName": "Test Tenant"}]
```

---

## Most Likely Issue

Based on your logs, the most likely issue is:

**Your microservice has `POST /tenants` but NOT `GET /tenants`**

Add this to your FastAPI code:

```python
@app.get("/tenants")
async def list_tenants():
    """List all tenants"""
    tenants = await db.tenants.find().to_list(None)
    # Remove MongoDB _id field
    for tenant in tenants:
        if '_id' in tenant:
            tenant.pop('_id')
    return tenants
```

Restart your microservice and try again!

---

## Quick Debug Checklist

- [ ] Run `curl http://your-api:8001/docs` - Check if GET /tenants exists
- [ ] Run `curl http://your-api:8001/tenants` - Test endpoint directly
- [ ] Check FastAPI code has `@app.get("/tenants")`
- [ ] Check router is included: `app.include_router(...)`
- [ ] Check CORS is enabled
- [ ] Restart microservice after code changes

---

## Need More Help?

Share your FastAPI code (the part with tenant endpoints) and I can tell you exactly what's missing!
