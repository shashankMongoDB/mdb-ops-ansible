#!/bin/bash
# MongoDB Replica Set - Quick Start Deployment Script
# Run this on your Ubuntu control node

set -e  # Exit on error

echo "=========================================="
echo "MongoDB Replica Set Deployment"
echo "=========================================="
echo ""

# Step 1: Check if in correct directory
if [ ! -f "../load_env.sh" ]; then
    echo "❌ Error: Must run from replica_set/ directory"
    echo "   cd ~/mdbaas-repo/mdb-ops-ansible/playbooks/cluster_creation/replica_set/"
    exit 1
fi

# Step 2: Check if .env exists
if [ ! -f "../.env" ]; then
    echo "❌ Error: .env file not found"
    echo ""
    echo "Create it from template:"
    echo "  cd .."
    echo "  cp .env.example .env"
    echo "  vi .env  # Fill your values"
    exit 1
fi

# Step 3: Load environment
echo "📦 Loading environment variables..."
cd ..
source load_env.sh
cd replica_set/

if [ -z "$OPS_MANAGER_URL" ]; then
    echo "❌ Error: Environment not loaded properly"
    exit 1
fi

echo ""

# Step 4: Check PEM file
echo "🔑 Checking SSH key..."
if [ ! -f "../sp-k8s.pem" ]; then
    echo "❌ Error: PEM file not found at ../sp-k8s.pem"
    exit 1
fi

PEM_PERMS=$(stat -c "%a" ../sp-k8s.pem 2>/dev/null || stat -f "%A" ../sp-k8s.pem)
if [ "$PEM_PERMS" != "400" ]; then
    echo "⚠️  Fixing PEM file permissions..."
    chmod 400 ../sp-k8s.pem
fi

echo "✅ PEM file OK"
echo ""

# Step 5: Check Ansible installed
echo "🔧 Checking Ansible..."
if ! command -v ansible &> /dev/null; then
    echo "❌ Error: Ansible not installed"
    echo ""
    echo "Install it:"
    echo "  sudo apt update"
    echo "  sudo apt install -y ansible"
    exit 1
fi

echo "✅ Ansible version: $(ansible --version | head -1)"
echo ""

# Step 6: Test inventory
echo "📋 Testing inventory parsing..."
if ! ansible-inventory -i inventory.yml --list &> /dev/null; then
    echo "❌ Error: Inventory parsing failed"
    echo ""
    echo "Debug:"
    echo "  ansible-inventory -i inventory.yml --list"
    exit 1
fi

echo "✅ Inventory parsed successfully"
echo ""

# Step 7: Test connectivity
echo "🌐 Testing SSH connectivity to VMs..."
if ! ansible -i inventory.yml mongodb_all -m ping &> /dev/null; then
    echo "❌ Error: Cannot connect to VMs"
    echo ""
    echo "Debug:"
    echo "  ansible -i inventory.yml mongodb_all -m ping -vvv"
    echo ""
    echo "Check:"
    echo "  - VMs are running"
    echo "  - Security group allows SSH from control node"
    echo "  - PEM file is correct"
    exit 1
fi

echo "✅ All VMs reachable"
echo ""

# Step 8: Confirm deployment
echo "=========================================="
echo "Ready to Deploy!"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Ops Manager: $OPS_MANAGER_URL"
echo "  Project ID: $OPS_MANAGER_PROJECT_ID"
echo "  VMs: $VM1_IP, $VM2_IP, $VM3_IP"
echo "  Replica Set: $REPLICA_SET_NAME"
echo "  MongoDB Version: $MONGODB_VERSION"
echo "  Authentication: $ENABLE_AUTHENTICATION"
echo "  Monitoring: $ENABLE_MONITORING"
echo ""
echo "Deployment steps:"
echo "  1. Install agents (~5 minutes)"
echo "  2. Deploy replica set (~10-15 minutes)"
echo ""
read -p "Continue with deployment? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    exit 0
fi

# Step 9: Install agents
echo ""
echo "=========================================="
echo "Step 1: Installing Agents"
echo "=========================================="
echo ""
ansible-playbook -i inventory.yml 1_install_agents.yml

echo ""
echo "✅ Agents installed!"
echo ""
echo "⏳ Waiting 30 seconds for agents to connect to Ops Manager..."
sleep 30

# Step 10: Deploy replica set
echo ""
echo "=========================================="
echo "Step 2: Deploying Replica Set"
echo "=========================================="
echo ""
ansible-playbook -i inventory.yml 2_deploy_replica_set_secure.yml

# Done
echo ""
echo "=========================================="
echo "🎉 DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Check Ops Manager UI:"
echo "     $OPS_MANAGER_URL"
echo ""
echo "  2. Verify processes:"
echo "     Go to: Your Project → Deployment → Processes"
echo "     Should see: 3 mongod processes in GOAL_STATE"
echo ""
echo "  3. Create admin user (optional):"
echo "     ansible-playbook -i inventory.yml 3_create_admin_user.yml"
echo ""
echo "Connection string (after creating admin user):"
echo "  mongodb://admin:PASSWORD@$VM1_IP:27017,$VM2_IP:27017,$VM3_IP:27017/?replicaSet=$REPLICA_SET_NAME&authSource=admin"
echo ""
echo "=========================================="
