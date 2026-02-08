# AtlasForge UI - Installation with Yarn

## Using Yarn Instead of npm

Since npm is not working, we'll use Yarn for all package management.

---

## 🚀 Quick Installation

### On Your MacBook

```bash
cd /Users/shashank.pandey/Desktop/Codebase/MDBaaS/Github-repo/mdb-ops-ansible/AtlasForge-UI

# Commit and push fixes
git add .
git commit -m "Fix: Replace Table with Cards, update Next.js, remove incompatible packages"
git push origin main
```

### On Ubuntu Server

```bash
ssh ubuntu@ip-172-31-20-249
cd ~/mdb-ops-ansible/AtlasForge-UI

# Pull latest changes
git pull origin main

# Clean everything
rm -rf node_modules yarn.lock package-lock.json

# Install with Yarn
yarn install

# Start dev server
yarn dev
```

---

## 📦 Yarn Commands Reference

| Task | Yarn Command |
|------|--------------|
| Install dependencies | `yarn install` or just `yarn` |
| Start dev server | `yarn dev` |
| Build for production | `yarn build` |
| Start production server | `yarn start` |
| Run linter | `yarn lint` |
| Type check | `yarn type-check` |
| Add a package | `yarn add package-name` |
| Remove a package | `yarn remove package-name` |
| Clear cache | `yarn cache clean` |

---

## 🔧 If Yarn is Not Installed

### Install Yarn on Ubuntu:

```bash
# Option 1: Using npm (if available)
npm install -g yarn

# Option 2: Using apt (recommended)
curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | sudo apt-key add -
echo "deb https://dl.yarnpkg.com/debian/ stable main" | sudo tee /etc/apt/sources.list.d/yarn.list
sudo apt update
sudo apt install yarn

# Option 3: Using npm alternative
sudo npm install -g yarn --force

# Verify installation
yarn --version
```

### Install Yarn on macOS:

```bash
# Using Homebrew
brew install yarn

# Or using npm
npm install -g yarn

# Verify
yarn --version
```

---

## 🎯 Complete Setup (Ubuntu Server)

```bash
# 1. SSH to server
ssh ubuntu@ip-172-31-20-249

# 2. Navigate to project
cd ~/mdb-ops-ansible/AtlasForge-UI

# 3. Pull latest code
git pull origin main

# 4. Install Yarn if needed
yarn --version || npm install -g yarn

# 5. Clean old files
rm -rf node_modules yarn.lock package-lock.json .next

# 6. Install dependencies
yarn install

# 7. Start development server
yarn dev
```

Expected output:
```
✓ Ready in 2.5s
○ Local:        http://localhost:3000
○ Network:      http://0.0.0.0:3000
```

---

## 🌐 Access the Application

Once `yarn dev` is running:

- **From server**: http://localhost:3000
- **From browser**: http://ip-172-31-20-249:3000
- **Or your IP**: http://your-server-ip:3000

---

## 🐛 Troubleshooting with Yarn

### Error: "There appears to be trouble with your network connection"

```bash
yarn install --network-timeout 100000
```

### Error: "Incorrect integrity when fetching from the cache"

```bash
yarn cache clean
rm -rf node_modules yarn.lock
yarn install
```

### Error: Port 3000 already in use

```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9

# Or use different port
PORT=3001 yarn dev
```

### Error: "Module not found"

```bash
rm -rf node_modules yarn.lock .next
yarn cache clean
yarn install
```

### Yarn hangs during install

```bash
# Try with verbose output to see what's happening
yarn install --verbose

# Or with network concurrency limit
yarn install --network-concurrency 1
```

---

## ⚡ Why Yarn is Better

1. **Faster** - Parallel downloads and caching
2. **More Reliable** - Better dependency resolution
3. **Deterministic** - yarn.lock ensures same versions everywhere
4. **Better Error Messages** - Easier to debug
5. **Offline Mode** - Can install from cache

---

## 🔄 Migrating from npm to Yarn

Already have `package-lock.json`? No problem:

```bash
# Remove npm files
rm -rf node_modules package-lock.json

# Yarn will read package.json and create yarn.lock
yarn install
```

Yarn will automatically:
- Read your `package.json`
- Install all dependencies
- Create `yarn.lock` (similar to package-lock.json)

---

## 📝 Update package.json Scripts (Already Done)

Your `package.json` already has scripts that work with both npm and yarn:

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "type-check": "tsc --noEmit"
  }
}
```

So you can use either:
- `npm run dev` or `yarn dev`
- `npm run build` or `yarn build`
- `npm start` or `yarn start`

---

## 🚀 Production Deployment with Yarn

```bash
# Build
yarn build

# Start production server
yarn start

# Or with PM2
pm2 start yarn --name "atlasforge-ui" -- start
pm2 save
pm2 startup
```

---

## ✅ Verification Checklist

After running `yarn dev`, verify:

- [ ] Server starts without errors
- [ ] Can access http://localhost:3000
- [ ] Home page loads (tenants overview)
- [ ] Tenant cards display properly
- [ ] "Onboard Tenant" modal opens
- [ ] No errors in browser console
- [ ] No "Element type is invalid" error
- [ ] No "Next.js is outdated" warning

---

## 🎉 Success!

When you see:
```
✓ Ready in 2.5s
○ Local:   http://localhost:3000
```

You're all set! The application is running with:
- ✅ Yarn (faster, more reliable)
- ✅ Next.js 15 (latest)
- ✅ Card-based UI (no table errors)
- ✅ All dependencies resolved

---

## 🆘 Still Having Issues?

If Yarn also fails, try:

```bash
# Clear everything
rm -rf node_modules yarn.lock package-lock.json .next ~/.yarn ~/.cache/yarn

# Reinstall Yarn
npm install -g yarn --force

# Try again
yarn install --verbose
```

Or check network/firewall:
```bash
# Test yarn registry
curl -I https://registry.yarnpkg.com/

# Test npm registry (yarn uses it)
curl -I https://registry.npmjs.org/
```

---

**Yarn should work much better than npm!** 🎯
