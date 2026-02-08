# NPM Installation Troubleshooting Guide

## The Issue
Getting "Access token expired or revoked" error when running `npm install`, even though all packages are public.

## Quick Diagnosis

### Step 1: Check if VPN is causing SSL/Certificate issues

```bash
# Test npm registry connectivity
curl -I https://registry.npmjs.org/

# Should return: HTTP/2 200
# If you get certificate errors, VPN is likely the issue
```

### Step 2: Check npm configuration

```bash
# View all npm config
npm config list

# Check for any auth tokens or private registries
cat ~/.npmrc 2>/dev/null || echo "No .npmrc file"
```

### Step 3: Check Node.js and npm versions

```bash
node --version   # Should be v18 or higher
npm --version    # Should be v9 or higher
```

## Solution A: Bypass VPN/Proxy Issues (Most Common)

### Option 1: Use HTTP instead of HTTPS (temporary workaround)

```bash
npm config set registry http://registry.npmjs.org/
npm install
# After install succeeds, set it back:
npm config set registry https://registry.npmjs.org/
```

### Option 2: Disable strict SSL (if corporate VPN intercepts SSL)

```bash
npm config set strict-ssl false
npm install
# After install, re-enable it:
npm config set strict-ssl true
```

### Option 3: Configure proxy settings (if behind corporate proxy)

```bash
# If you have a proxy
npm config set proxy http://proxy.company.com:8080
npm config set https-proxy http://proxy.company.com:8080

# Try install
npm install
```

## Solution B: Complete npm Reset

```bash
# 1. Remove all npm configuration
rm -f ~/.npmrc
rm -f ./.npmrc

# 2. Clear npm cache completely
npm cache clean --force
npm cache verify

# 3. Remove node_modules and lock file
rm -rf node_modules package-lock.json

# 4. Set clean registry
npm config set registry https://registry.npmjs.org/

# 5. Try install
npm install
```

## Solution C: Use Alternative Package Managers

### Using Yarn (Recommended if npm keeps failing)

```bash
# Install yarn globally
npm install -g yarn

# Use yarn instead
yarn install

# Run dev server
yarn dev
```

### Using pnpm (Alternative)

```bash
# Install pnpm
npm install -g pnpm

# Use pnpm
pnpm install

# Run dev
pnpm dev
```

## Solution D: Manual Node.js and npm Reinstall

### On macOS:

```bash
# Using Homebrew
brew uninstall node
brew cleanup
brew install node

# Or using nvm (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc  # or ~/.zshrc
nvm install --lts
nvm use --lts
```

### On Ubuntu:

```bash
# Remove old Node.js
sudo apt remove nodejs npm
sudo apt autoremove

# Install using NodeSource
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Verify
node --version
npm --version
```

## Solution E: Use npx to install with different registry

```bash
# Use npx with explicit registry
npx --yes npm@latest install --registry=https://registry.npmjs.org/
```

## Solution F: Check for Corporate/Network Issues

### Test npm registry connectivity

```bash
# Test if you can reach npm registry
ping registry.npmjs.org

# Test HTTPS connection
curl -v https://registry.npmjs.org/@leafygreen-ui/button

# If this fails, it's definitely a network/VPN issue
```

### Check DNS resolution

```bash
# Check if DNS is resolving correctly
nslookup registry.npmjs.org

# Try with Google DNS
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
npm install
```

## Solution G: Offline Installation (Last Resort)

If nothing works and you're blocked by corporate network:

1. **On a computer with working internet** (no VPN):
   ```bash
   npm install
   tar -czf node_modules.tar.gz node_modules package-lock.json
   ```

2. **Transfer the tar file** to your blocked machine

3. **On the blocked machine**:
   ```bash
   tar -xzf node_modules.tar.gz
   npm run dev  # Should work now
   ```

## For Your Specific Case

### On macOS (your laptop):

```bash
cd /Users/shashank.pandey/Desktop/Codebase/MDBaaS/Github-repo/mdb-ops-ansible/AtlasForge-UI

# Try this sequence:
npm config delete registry
npm config delete proxy
npm config delete https-proxy
npm config set strict-ssl false
rm -rf node_modules package-lock.json ~/.npmrc
npm cache clean --force
npm install
```

### On Ubuntu Server:

```bash
ssh ubuntu@ip-172-31-20-249
cd ~/mdb-ops-ansible/AtlasForge-UI

# Same sequence:
npm config delete registry
npm config delete proxy  
npm config delete https-proxy
npm config set strict-ssl false
rm -rf node_modules package-lock.json ~/.npmrc
npm cache clean --force
npm install
```

## Check for These Common Issues

### 1. Corporate VPN with SSL Inspection
**Symptom**: Certificate errors, SSL errors
**Fix**: `npm config set strict-ssl false`

### 2. Firewall blocking npm registry
**Symptom**: Timeout errors, ENOTFOUND
**Fix**: Use HTTP registry or configure proxy

### 3. Old npm cache with expired tokens
**Symptom**: "Access token expired" 
**Fix**: `npm cache clean --force` and remove ~/.npmrc

### 4. IPv6 issues
**Symptom**: Hangs during install
**Fix**: 
```bash
npm config set ipv6 false
npm install
```

### 5. Network interference
**Symptom**: Random failures, intermittent errors
**Fix**: Try different network, disconnect VPN

## Verification Commands

After trying solutions, verify your setup:

```bash
# 1. Check npm can reach registry
npm ping

# 2. Check configuration is clean
npm config list

# 3. Test installing a single package
npm install lodash

# 4. If that works, install all
npm install
```

## Alternative: Use Volta (Better Node.js Version Manager)

```bash
# Install volta
curl https://get.volta.sh | bash

# Install Node.js with volta
volta install node@18

# Try npm install again
npm install
```

## Still Not Working?

If none of these work, let's create a minimal test:

```bash
# Create test directory
mkdir /tmp/npm-test
cd /tmp/npm-test

# Create minimal package.json
cat > package.json << 'EOF'
{
  "name": "test",
  "version": "1.0.0",
  "dependencies": {
    "lodash": "^4.17.21"
  }
}
EOF

# Try install
npm install

# If this fails, the issue is with your npm/node setup, not the project
# If this works, the issue might be with the LeafyGreen packages
```

## Contact Network Admin If:

- You can't reach registry.npmjs.org
- SSL errors persist even with strict-ssl false
- Firewall is blocking outbound connections
- Corporate proxy requires authentication

## Quick Win: Try on Mobile Hotspot

If you suspect VPN/corporate network:

```bash
# Disconnect from VPN/corporate network
# Connect to mobile hotspot
npm install
```

If this works, your corporate network/VPN is definitely the issue.

---

**Next Steps**: Try the solutions in order (A → B → C → D). Most likely Solution A or B will fix it.
