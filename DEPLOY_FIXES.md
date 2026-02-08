# Deploy API Fixes - Quick Guide

## ✅ Changes Made

Fixed the 405 error by adding:
1. **GET /tenants** endpoint - List all tenants
2. **GET /tenants/{id}** endpoint - Get specific tenant
3. **CORS middleware** - Allow UI to connect

## 🚀 Deploy to Server

### Option 1: Git (Recommended)

```bash
# On MacBook - Commit and push
cd /Users/shashank.pandey/Desktop/Codebase/MDBaaS/Github-repo/mdb-ops-ansible

git add AtlasForge/
git commit -m "Fix: Add missing GET /tenants endpoints and CORS"
git push origin main

# On Ubuntu Server - Pull and restart
ssh ubuntu@ec2-34-213-34-101.us-west-2.compute.amazonaws.com

cd ~/mdb-ops-ansible
git pull origin main

# Find and kill the running process
ps aux | grep "app.main"
kill <PID>

# Restart the service
cd AtlasForge
python -m app.main

# Or with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### Option 2: Manual Copy

```bash
# From MacBook - Copy modified files
scp AtlasForge/app/main.py ubuntu@ec2-34-213-34-101.us-west-2.compute.amazonaws.com:~/mdb-ops-ansible/AtlasForge/app/
scp AtlasForge/app/services/tenants_service.py ubuntu@ec2-34-213-34-101.us-west-2.compute.amazonaws.com:~/mdb-ops-ansible/AtlasForge/app/services/
scp AtlasForge/app/services/mongo_repo.py ubuntu@ec2-34-213-34-101.us-west-2.compute.amazonaws.com:~/mdb-ops-ansible/AtlasForge/app/services/

# On Ubuntu - Restart
ssh ubuntu@ec2-34-213-34-101.us-west-2.compute.amazonaws.com
ps aux | grep "app.main"
kill <PID>
cd ~/mdb-ops-ansible/AtlasForge
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

## 🧪 Test

### 1. Test API Directly
```bash
# Should return [] or list of tenants (NOT 405!)
curl http://ec2-34-213-34-101.us-west-2.compute.amazonaws.com:8001/tenants
```

### 2. Check FastAPI Docs
Open: http://ec2-34-213-34-101.us-west-2.compute.amazonaws.com:8001/docs

You should see:
- ✅ GET /tenants
- ✅ GET /tenants/{tenantId}

### 3. Test UI
```bash
cd AtlasForge-UI-Vite
npm run dev
# Open http://localhost:3000
# Should now load without errors!
```

## ✅ Success Indicators

- ✅ curl returns `[]` not 405
- ✅ Logs show 200 not 405
- ✅ UI loads tenants page
- ✅ No CORS errors in browser console

## 📝 Files Changed

- `AtlasForge/app/main.py`
- `AtlasForge/app/services/tenants_service.py`
- `AtlasForge/app/services/mongo_repo.py`

See `AtlasForge/API_CHANGES.md` for detailed changes.
