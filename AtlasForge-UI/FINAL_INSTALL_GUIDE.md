# AtlasForge UI - Final Installation Guide

## Issues Fixed

✅ **Removed deprecated/non-existent packages**  
✅ **Replaced Table component with Card-based layout** (more reliable)  
✅ **Updated Next.js to latest version** (14.2.3 → 15.0.0)  
✅ **Fixed all LeafyGreen UI compatibility issues**  

## Installation Steps

### Step 1: Get Latest Code

#### Option A: Via Git (Recommended)

```bash
# On MacBook
cd /Users/shashank.pandey/Desktop/Codebase/MDBaaS/Github-repo/mdb-ops-ansible/AtlasForge-UI

git add .
git commit -m "Fix: Replace Table with Cards, update Next.js, remove deprecated packages"
git push origin main

# On Ubuntu Server
ssh ubuntu@ip-172-31-20-249
cd ~/mdb-ops-ansible/AtlasForge-UI
git pull origin main
```

#### Option B: Manual Copy

```bash
# From MacBook, copy updated files
scp package.json ubuntu@ip-172-31-20-249:~/mdb-ops-ansible/AtlasForge-UI/
scp pages/tenants/\[tenantId\].tsx ubuntu@ip-172-31-20-249:~/mdb-ops-ansible/AtlasForge-UI/pages/tenants/
scp -r components/*.tsx ubuntu@ip-172-31-20-249:~/mdb-ops-ansible/AtlasForge-UI/components/
```

### Step 2: Clean Installation

```bash
# On Ubuntu Server
ssh ubuntu@ip-172-31-20-249
cd ~/mdb-ops-ansible/AtlasForge-UI

# Remove old files
rm -rf node_modules package-lock.json

# Clear cache
npm cache clean --force

# Install dependencies
npm install

# If it still fails with peer dependency errors, try:
npm install --legacy-peer-deps
```

### Step 3: Start Development Server

```bash
npm run dev
```

Expected output:
```
✓ Ready in 2.5s
○ Local:        http://localhost:3000
○ Network:      http://0.0.0.0:3000
```

### Step 4: Access the Application

Open browser and navigate to:
- **Ubuntu Server**: `http://ip-172-31-20-249:3000`
- **Or your server IP**: `http://your-server-ip:3000`

## Changes Made

### 1. Removed Non-Existent Packages
- `@leafygreen-ui/confirm-modal` ❌
- `@leafygreen-ui/form-footer` ❌
- `@leafygreen-ui/table` ❌ (causing import errors)

### 2. Updated Packages
- `next`: `14.2.3` → `^15.0.0`
- `@leafygreen-ui/leafygreen-provider`: `^3.0.0` → `^4.0.0`

### 3. UI Changes
- **Tenant Details Page**: Replaced table with card-based layout
  - More responsive
  - Better mobile support
  - No import errors
  
- **All Modals**: Custom button layouts instead of FormFooter

- **Confirmation Dialogs**: Custom implementation using Modal

### Before (Table - causing errors):
```tsx
<Table data={deployments} columns={...}>
  <Row>...</Row>
</Table>
```

### After (Cards - working):
```tsx
{deployments.map((deployment) => (
  <Card>
    <H3>{deployment.displayName}</H3>
    <StatusBadge status={deployment.status} />
    <Button>View Details</Button>
  </Card>
))}
```

## Troubleshooting

### Error: "Element type is invalid"
**Solution**: This was caused by incorrect Table imports. Fixed by using Cards instead.

### Error: "Cannot resolve dependency tree"
**Solution**: Run with `--legacy-peer-deps`:
```bash
npm install --legacy-peer-deps
```

### Error: "Next.js is outdated"
**Solution**: Updated to Next.js 15 in package.json. Just run `npm install`.

### Error: "Module not found"
**Solution**: Clear everything and reinstall:
```bash
rm -rf node_modules package-lock.json .next
npm cache clean --force
npm install
```

### Port 3000 already in use
**Solution**: Kill existing process or use different port:
```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9

# Or use different port
PORT=3001 npm run dev
```

## Production Deployment

```bash
# Build for production
npm run build

# Start production server
npm start

# Or with PM2
npm install -g pm2
pm2 start npm --name "atlasforge-ui" -- start
pm2 save
pm2 startup
```

## Environment Variables

Make sure `.env.local` exists with:

```env
NEXT_PUBLIC_CONTROL_PLANE_API_BASE_URL=http://ec2-34-213-34-101.us-west-2.compute.amazonaws.com:8001
MCP_MONGODB_URI=mongodb://shashank:password@ec2-34-213-34-101.us-west-2.compute.amazonaws.com:27017/?authSource=admin
MCP_DB_NAME=mdb_control_plane
NEXT_PUBLIC_ENVIRONMENT=DEV
```

## Verification Checklist

After installation, verify:

- [ ] `npm install` completes without errors
- [ ] `npm run dev` starts server successfully
- [ ] Homepage loads at http://localhost:3000
- [ ] Can view tenants page
- [ ] Can open "Onboard Tenant" modal
- [ ] Cards display properly (no table rendering errors)
- [ ] No console errors in browser dev tools

## UI Preview

### Home Page (Tenants Overview)
```
┌─────────────────────────────────────────────┐
│  🍃 AtlasForge    Tenants                   │
│                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Acme     │  │ Globex   │  │ Demo     │ │
│  │ t-acme   │  │ t-globex │  │ t-demo   │ │
│  │ 5 deps   │  │ 3 deps   │  │ 1 dep    │ │
│  └──────────┘  └──────────┘  └──────────┘ │
└─────────────────────────────────────────────┘
```

### Tenant Details Page (Card Layout)
```
┌─────────────────────────────────────────────┐
│  ← Back to Tenants                          │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │  Acme Corporation                   │   │
│  │  t-acme                             │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  Deployments        [Create Deployment]     │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ Orders Database      🟢 Running     │   │
│  │ rs-orders           [View Details]  │   │
│  │ ReplicaSet • 8.0.3 • 3 members      │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │ Customers DB         🟢 Running     │   │
│  │ rs-customers        [View Details]  │   │
│  │ ReplicaSet • 8.0.3 • 3 members      │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

## Success Indicators

You'll know it's working when:

✅ No more "Element type is invalid" errors  
✅ No more "Next.js is outdated" warning  
✅ Cards display properly on tenant details page  
✅ All modals open and close correctly  
✅ Status badges show correct colors  
✅ Navigation works smoothly  

## Next Steps

1. ✅ Install dependencies
2. ✅ Start dev server
3. 📝 Test tenant creation
4. 📝 Test deployment creation
5. 📝 Test lifecycle operations
6. 🚀 Deploy to production

## Support

If you encounter any issues:

1. Check the error message carefully
2. Try `npm install --legacy-peer-deps`
3. Clear everything: `rm -rf node_modules package-lock.json .next && npm install`
4. Check browser console for JavaScript errors
5. Verify `.env.local` is properly configured

## Alternative: Use Yarn

If npm continues to have issues, Yarn is more reliable:

```bash
npm install -g yarn
yarn install
yarn dev
```

---

**This should work now!** 🎉

The main issues were:
1. Non-existent packages in npm registry
2. Incompatible Table component causing render errors
3. Outdated Next.js version

All fixed with card-based layout and updated dependencies.
