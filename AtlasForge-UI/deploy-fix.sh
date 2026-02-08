#!/bin/bash

echo "================================================"
echo "AtlasForge UI - Deploy Fixed Version"
echo "================================================"
echo ""

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found. Please run from AtlasForge-UI directory."
    exit 1
fi

echo "Step 1: Committing changes..."
git add .
git commit -m "Fix: Replace Table with Cards, update Next.js 15, remove incompatible packages

- Removed @leafygreen-ui/table (causing Element type invalid error)
- Removed @leafygreen-ui/confirm-modal (doesn't exist in npm)
- Removed @leafygreen-ui/form-footer (doesn't exist in npm)
- Updated Next.js from 14.2.3 to 15.0.0
- Updated leafygreen-provider to v4 for compatibility
- Replaced Table component with Card-based layout on tenant details page
- Custom implementation for confirmation modals and form footers
- All modals now use standard button layouts"

if [ $? -eq 0 ]; then
    echo "✓ Changes committed"
else
    echo "ℹ Nothing to commit or commit failed"
fi

echo ""
echo "Step 2: Pushing to remote..."
git push origin main

if [ $? -eq 0 ]; then
    echo "✓ Pushed to remote successfully"
    echo ""
    echo "================================================"
    echo "✓ Deployment successful!"
    echo "================================================"
    echo ""
    echo "Next steps on Ubuntu server:"
    echo ""
    echo "  ssh ubuntu@ip-172-31-20-249"
    echo "  cd ~/mdb-ops-ansible/AtlasForge-UI"
    echo "  git pull origin main"
    echo "  rm -rf node_modules package-lock.json"
    echo "  npm install --legacy-peer-deps"
    echo "  npm run dev"
    echo ""
else
    echo "❌ Push failed. Check your git remote configuration."
    exit 1
fi
