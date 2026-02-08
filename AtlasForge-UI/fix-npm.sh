#!/bin/bash

echo "=================================="
echo "NPM Installation Fix Script"
echo "=================================="
echo ""

echo "Step 1: Cleaning up npm configuration..."
rm -f ~/.npmrc
rm -f ./.npmrc
echo "✓ Removed .npmrc files"

echo ""
echo "Step 2: Clearing npm cache..."
npm cache clean --force
echo "✓ Cache cleared"

echo ""
echo "Step 3: Removing node_modules and lock file..."
rm -rf node_modules package-lock.json
echo "✓ Removed node_modules and package-lock.json"

echo ""
echo "Step 4: Resetting npm configuration..."
npm config delete registry
npm config delete proxy
npm config delete https-proxy
npm config set strict-ssl false
npm config set registry https://registry.npmjs.org/
echo "✓ Configuration reset"

echo ""
echo "Step 5: Attempting npm install..."
echo "=================================="
npm install

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================="
    echo "✓ SUCCESS! npm install completed"
    echo "=================================="
    echo ""
    echo "Next steps:"
    echo "  npm run dev    # Start development server"
    echo ""
    echo "Don't forget to re-enable strict-ssl later:"
    echo "  npm config set strict-ssl true"
else
    echo ""
    echo "=================================="
    echo "❌ npm install failed"
    echo "=================================="
    echo ""
    echo "Try these alternatives:"
    echo ""
    echo "1. Use Yarn instead:"
    echo "   npm install -g yarn"
    echo "   yarn install"
    echo ""
    echo "2. Use HTTP registry:"
    echo "   npm config set registry http://registry.npmjs.org/"
    echo "   npm install"
    echo ""
    echo "3. Disconnect VPN and try again"
    echo ""
    echo "4. Check TROUBLESHOOTING_NPM.md for more solutions"
fi
