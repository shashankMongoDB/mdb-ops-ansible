#!/bin/bash

echo "=================================="
echo "NPM Installation Diagnostic Script"
echo "=================================="
echo ""

echo "1. Checking Node.js and npm versions..."
node --version 2>&1 || echo "❌ Node.js not found"
npm --version 2>&1 || echo "❌ npm not found"
echo ""

echo "2. Checking npm registry connectivity..."
curl -I https://registry.npmjs.org/ 2>&1 | head -1
echo ""

echo "3. Checking npm configuration..."
echo "Registry: $(npm config get registry)"
echo "Strict SSL: $(npm config get strict-ssl)"
echo "Proxy: $(npm config get proxy)"
echo "HTTPS Proxy: $(npm config get https-proxy)"
echo ""

echo "4. Checking for .npmrc files..."
if [ -f ~/.npmrc ]; then
    echo "~/.npmrc exists:"
    cat ~/.npmrc
else
    echo "~/.npmrc does not exist (good)"
fi
echo ""

if [ -f ./.npmrc ]; then
    echo "./.npmrc exists:"
    cat ./.npmrc
else
    echo "./.npmrc does not exist (good)"
fi
echo ""

echo "5. Testing npm ping..."
npm ping 2>&1 || echo "❌ npm ping failed"
echo ""

echo "6. Checking DNS resolution..."
nslookup registry.npmjs.org 2>&1 | grep -A1 "Name:"
echo ""

echo "7. Testing package download..."
curl -s https://registry.npmjs.org/lodash/latest | head -5
echo ""

echo "8. Checking for IPv6 issues..."
echo "IPv6 setting: $(npm config get ipv6)"
echo ""

echo "=================================="
echo "Diagnostic complete!"
echo "=================================="
echo ""
echo "Common fixes:"
echo "1. If SSL/certificate errors: npm config set strict-ssl false"
echo "2. If DNS issues: npm config set registry http://registry.npmjs.org/"
echo "3. If token errors: rm ~/.npmrc && npm cache clean --force"
echo "4. If VPN issues: Disconnect VPN and try again"
echo "5. If all fails: Try 'yarn install' instead"
