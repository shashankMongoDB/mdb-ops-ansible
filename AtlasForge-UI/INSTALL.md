# AtlasForge UI - Installation Guide

## Fixed Issues

✅ Removed deprecated packages (`@leafygreen-ui/confirm-modal`, `@leafygreen-ui/form-footer`)  
✅ Updated `leafygreen-provider` to v4 for compatibility  
✅ Replaced deprecated components with custom implementations  
✅ All packages now use compatible versions  

## Installation Steps

### On Your MacBook

```bash
cd /Users/shashank.pandey/Desktop/Codebase/MDBaaS/Github-repo/mdb-ops-ansible/AtlasForge-UI

# Clean up
rm -rf node_modules package-lock.json
npm cache clean --force

# Install dependencies
npm install

# Start development server
npm run dev
```

### On Ubuntu Server

First, copy the updated files:

```bash
# From your MacBook
cd /Users/shashank.pandey/Desktop/Codebase/MDBaaS/Github-repo/mdb-ops-ansible/AtlasForge-UI

# Copy package.json
scp package.json ubuntu@ip-172-31-20-249:~/mdb-ops-ansible/AtlasForge-UI/

# Copy updated components
scp components/ConfirmActionModal.tsx ubuntu@ip-172-31-20-249:~/mdb-ops-ansible/AtlasForge-UI/components/
scp components/CreateTenantModal.tsx ubuntu@ip-172-31-20-249:~/mdb-ops-ansible/AtlasForge-UI/components/
scp components/CreateDeploymentModal.tsx ubuntu@ip-172-31-20-249:~/mdb-ops-ansible/AtlasForge-UI/components/
scp components/ScaleDeploymentModal.tsx ubuntu@ip-172-31-20-249:~/mdb-ops-ansible/AtlasForge-UI/components/
scp components/UpgradeVersionModal.tsx ubuntu@ip-172-31-20-249:~/mdb-ops-ansible/AtlasForge-UI/components/
```

Or push to git and pull on Ubuntu:

```bash
# On MacBook - commit and push
git add .
git commit -m "Fix: Remove deprecated LeafyGreen packages and update dependencies"
git push origin main

# On Ubuntu - pull changes
ssh ubuntu@ip-172-31-20-249
cd ~/mdb-ops-ansible/AtlasForge-UI
git pull origin main
```

Then install:

```bash
# On Ubuntu
ssh ubuntu@ip-172-31-20-249
cd ~/mdb-ops-ansible/AtlasForge-UI

# Clean up
rm -rf node_modules package-lock.json
npm cache clean --force

# Install
npm install

# Start dev server
npm run dev
```

## If npm install Still Fails

Try with legacy peer deps:

```bash
npm install --legacy-peer-deps
```

Or use Yarn:

```bash
npm install -g yarn
yarn install
yarn dev
```

## Verify Installation

After successful installation, you should see:

```
added 400+ packages in 30s
```

Then start the dev server:

```bash
npm run dev
```

You should see:

```
ready - started server on 0.0.0.0:3000, url: http://localhost:3000
```

## Access the Application

- **MacBook**: http://localhost:3000
- **Ubuntu Server**: http://ip-172-31-20-249:3000 (or your server IP)

## Changes Made

### Removed Packages
- `@leafygreen-ui/confirm-modal` - Package doesn't exist in npm registry
- `@leafygreen-ui/form-footer` - Package doesn't exist in npm registry

### Updated Packages
- `@leafygreen-ui/leafygreen-provider`: `^3.0.0` → `^4.0.0` (fixes peer dependency conflict)

### Component Updates
All modals now use custom button layouts instead of deprecated `FormFooter`:

```tsx
// Old (with FormFooter)
<FormFooter
  primaryButton={<Button>Submit</Button>}
  secondaryButton={<Button>Cancel</Button>}
/>

// New (custom layout)
<div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
  <Button variant="default">Cancel</Button>
  <Button>Submit</Button>
</div>
```

`ConfirmActionModal` now uses `Modal` directly instead of the non-existent `ConfirmationModal`.

## Troubleshooting

### Error: "Cannot find module"
```bash
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

### Error: "peer dependency conflict"
```bash
npm install --legacy-peer-deps
```

### Error: "EACCES permission denied"
```bash
sudo chown -R $USER ~/.npm
npm cache clean --force
npm install
```

### Still having issues?
Try using Yarn:
```bash
npm install -g yarn
yarn install
```

## Production Build

```bash
npm run build
npm start
```

## Environment Variables

Don't forget to set up `.env.local`:

```env
NEXT_PUBLIC_CONTROL_PLANE_API_BASE_URL=http://ec2-34-213-34-101.us-west-2.compute.amazonaws.com:8001
MCP_MONGODB_URI=mongodb://shashank:password@ec2-34-213-34-101.us-west-2.compute.amazonaws.com:27017/?authSource=admin
MCP_DB_NAME=mdb_control_plane
NEXT_PUBLIC_ENVIRONMENT=DEV
```

(File already exists in the project)

## Success!

If everything works, you should be able to:
- View the tenants page at http://localhost:3000
- Create tenants
- Create deployments
- Manage lifecycle operations

Enjoy! 🎉
