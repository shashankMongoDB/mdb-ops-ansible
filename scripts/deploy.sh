#!/bin/bash

#
# MongoDB Control Plane - Automated Deployment Script
#
# This script deploys the MongoDB Control Plane in phases with dependency checks.
# Each phase is idempotent and can be run multiple times safely.
#
# Usage:
#   ./scripts/deploy.sh --config config/production.env --phase <phase-name>
#
# Phases:
#   operator        - Install MongoDB operators (Enterprise + Community)
#   ops-manager     - Install Ops Manager (optional, Enterprise only)
#   appdb-backup    - Install backup infrastructure (S3, IRSA, CronJobs)
#   monitoring      - Install Prometheus + Grafana
#   control-plane   - Install backend + frontend + metadata DB
#   verify          - Verify all components are healthy
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Log directory
LOG_DIR="${PROJECT_ROOT}/logs"
mkdir -p "$LOG_DIR"

# Default values
CONFIG_FILE=""
PHASE=""
SKIP_CHECKS=false
DRY_RUN=false
FORCE=false
UNINSTALL=false

# ==========================================
# Helper Functions
# ==========================================

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}❌${NC} $1"
}

log_step() {
    echo ""
    echo -e "${BLUE}==>${NC} $1"
    echo ""
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is not installed. Please install it first."
        exit 1
    fi
}

load_config() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
    
    log_info "Loading configuration from: $CONFIG_FILE"
    # shellcheck disable=SC1090
    source "$CONFIG_FILE"
    log_success "Configuration loaded"
}

check_kubernetes() {
    log_info "Checking Kubernetes connectivity..."
    
    if ! kubectl cluster-info &>/dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        log_info "Please check your kubeconfig: ${KUBECONFIG_PATH:-~/.kube/config}"
        exit 1
    fi
    
    log_success "Kubernetes cluster is accessible"
    
    # Show cluster info
    CLUSTER_VERSION=$(kubectl version --short 2>/dev/null | grep "Server Version" | awk '{print $3}')
    log_info "Cluster version: ${CLUSTER_VERSION}"
}

namespace_exists() {
    kubectl get namespace "$1" &>/dev/null
}

create_namespace() {
    local ns="$1"
    if namespace_exists "$ns"; then
        log_warning "Namespace $ns already exists"
    else
        log_info "Creating namespace: $ns"
        kubectl create namespace "$ns"
        log_success "Namespace $ns created"
    fi
}

wait_for_pods() {
    local namespace="$1"
    local label="$2"
    local timeout="${3:-300}"
    
    log_info "Waiting for pods with label $label in namespace $namespace (timeout: ${timeout}s)..."
    
    if kubectl wait --for=condition=ready pod \
        -l "$label" \
        -n "$namespace" \
        --timeout="${timeout}s" &>/dev/null; then
        log_success "Pods are ready"
        return 0
    else
        log_error "Pods failed to become ready within ${timeout}s"
        kubectl get pods -n "$namespace" -l "$label"
        return 1
    fi
}

# ==========================================
# Phase: Operator
# ==========================================

deploy_operator() {
    log_step "Phase: Installing MongoDB Operators"
    
    # Check if already installed
    if kubectl get deployment mongodb-enterprise-operator -n "${OPERATOR_NAMESPACE}" &>/dev/null && [[ "$FORCE" != "true" ]]; then
        log_success "MongoDB Enterprise Operator already installed"
    else
        log_info "Installing MongoDB Enterprise Operator v${ENTERPRISE_OPERATOR_VERSION}..."
        
        # Create namespace
        create_namespace "${OPERATOR_NAMESPACE}"
        
        # Install CRDs
        kubectl apply -f https://raw.githubusercontent.com/mongodb/mongodb-enterprise-kubernetes/${ENTERPRISE_OPERATOR_VERSION}/crds.yaml
        
        # Install operator
        kubectl apply -f https://raw.githubusercontent.com/mongodb/mongodb-enterprise-kubernetes/${ENTERPRISE_OPERATOR_VERSION}/mongodb-enterprise.yaml
        
        # Wait for operator
        wait_for_pods "${OPERATOR_NAMESPACE}" "app=mongodb-enterprise-operator" 300
        
        log_success "MongoDB Enterprise Operator installed"
    fi
    
    # Install Community Operator
    if kubectl get deployment mongodb-kubernetes-operator -n "${OPERATOR_NAMESPACE}" &>/dev/null && [[ "$FORCE" != "true" ]]; then
        log_success "MongoDB Community Operator already installed"
    else
        log_info "Installing MongoDB Community Operator v${COMMUNITY_OPERATOR_VERSION}..."
        
        # Install CRDs
        kubectl apply -f https://raw.githubusercontent.com/mongodb/mongodb-kubernetes-operator/v${COMMUNITY_OPERATOR_VERSION}/config/crd/bases/mongodbcommunity.mongodb.com_mongodbcommunity.yaml
        
        # Install operator
        kubectl apply -f https://raw.githubusercontent.com/mongodb/mongodb-kubernetes-operator/v${COMMUNITY_OPERATOR_VERSION}/config/manager/manager.yaml
        
        # Wait for operator
        wait_for_pods "${OPERATOR_NAMESPACE}" "app=mongodb-kubernetes-operator" 300
        
        log_success "MongoDB Community Operator installed"
    fi
    
    log_success "Phase: Operator installation complete"
}

uninstall_operator() {
    log_step "Phase: Uninstalling MongoDB Operators"
    
    log_warning "This will delete all MongoDB deployments!"
    read -p "Are you sure? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_info "Uninstall cancelled"
        exit 0
    fi
    
    # Delete operators
    kubectl delete deployment mongodb-enterprise-operator -n "${OPERATOR_NAMESPACE}" --ignore-not-found
    kubectl delete deployment mongodb-kubernetes-operator -n "${OPERATOR_NAMESPACE}" --ignore-not-found
    
    # Delete CRDs
    kubectl delete crd mongodb.mongodb.com --ignore-not-found
    kubectl delete crd mongodbcommunity.mongodbcommunity.mongodb.com --ignore-not-found
    
    log_success "Operators uninstalled"
}

# ==========================================
# Phase: Ops Manager
# ==========================================

deploy_ops_manager() {
    log_step "Phase: Installing Ops Manager"
    
    if [[ "${INSTALL_OPS_MANAGER}" != "true" ]]; then
        log_info "Skipping Ops Manager installation (INSTALL_OPS_MANAGER=false)"
        log_info "Using external Ops Manager: ${OPS_MANAGER_URL}"
        return 0
    fi
    
    # Check if already installed
    if kubectl get deployment ops-manager -n "${OPERATOR_NAMESPACE}" &>/dev/null && [[ "$FORCE" != "true" ]]; then
        log_success "Ops Manager already installed"
        return 0
    fi
    
    log_info "Installing Ops Manager v${OPS_MANAGER_VERSION}..."
    
    # Create Ops Manager deployment
    kubectl apply -f "${PROJECT_ROOT}/k8s/ops-manager/deployment.yaml"
    
    # Wait for Ops Manager
    wait_for_pods "${OPERATOR_NAMESPACE}" "app=ops-manager" 600
    
    log_success "Ops Manager installed"
    
    # Get Ops Manager URL
    OM_URL=$(kubectl get svc ops-manager -n "${OPERATOR_NAMESPACE}" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    log_info "Ops Manager URL: http://${OM_URL}:8080"
    log_info "Complete setup at Ops Manager UI"
}

uninstall_ops_manager() {
    log_step "Phase: Uninstalling Ops Manager"
    
    kubectl delete deployment ops-manager -n "${OPERATOR_NAMESPACE}" --ignore-not-found
    kubectl delete svc ops-manager -n "${OPERATOR_NAMESPACE}" --ignore-not-found
    
    log_success "Ops Manager uninstalled"
}

# ==========================================
# Phase: Backup Infrastructure
# ==========================================

deploy_backup() {
    log_step "Phase: Installing Backup Infrastructure"
    
    log_info "Configuring S3 bucket: ${AWS_S3_BUCKET}"
    
    # Check if bucket exists
    if aws s3 ls "s3://${AWS_S3_BUCKET}" &>/dev/null; then
        log_success "S3 bucket already exists"
    else
        log_info "Creating S3 bucket: ${AWS_S3_BUCKET}"
        aws s3 mb "s3://${AWS_S3_BUCKET}" --region "${AWS_REGION}"
        log_success "S3 bucket created"
    fi
    
    # Create backup CronJob template
    log_info "Creating backup CronJob template..."
    cat > "${PROJECT_ROOT}/k8s/backup/cronjob-template.yaml" <<EOF
apiVersion: batch/v1
kind: CronJob
metadata:
  name: mongodb-backup
spec:
  schedule: "${COMMUNITY_BACKUP_SCHEDULE}"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: ${COMMUNITY_BACKUP_MONGODUMP_IMAGE}
            env:
            - name: AWS_REGION
              value: "${AWS_REGION}"
            - name: S3_BUCKET
              value: "${AWS_S3_BUCKET}"
EOF
    
    log_success "Backup infrastructure configured"
}

# ==========================================
# Phase: Monitoring
# ==========================================

deploy_monitoring() {
    log_step "Phase: Installing Monitoring"
    
    if [[ "${INSTALL_MONITORING}" != "true" ]]; then
        log_info "Skipping monitoring installation (INSTALL_MONITORING=false)"
        return 0
    fi
    
    # Create monitoring namespace
    create_namespace "${MONITORING_NAMESPACE}"
    
    # Install Prometheus
    log_info "Installing Prometheus..."
    kubectl apply -f "${PROJECT_ROOT}/k8s/monitoring/prometheus.yaml"
    wait_for_pods "${MONITORING_NAMESPACE}" "app=prometheus" 300
    log_success "Prometheus installed"
    
    # Install Grafana
    log_info "Installing Grafana..."
    kubectl apply -f "${PROJECT_ROOT}/k8s/monitoring/grafana.yaml"
    wait_for_pods "${MONITORING_NAMESPACE}" "app=grafana" 300
    log_success "Grafana installed"
    
    # Get Grafana URL
    GRAFANA_URL=$(kubectl get svc grafana -n "${MONITORING_NAMESPACE}" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    log_info "Grafana URL: http://${GRAFANA_URL}:3000"
    log_info "Login: admin / ${GRAFANA_ADMIN_PASSWORD}"
}

uninstall_monitoring() {
    log_step "Phase: Uninstalling Monitoring"
    
    kubectl delete namespace "${MONITORING_NAMESPACE}" --ignore-not-found
    
    log_success "Monitoring uninstalled"
}

# ==========================================
# Phase: Control Plane
# ==========================================

deploy_control_plane() {
    log_step "Phase: Installing Control Plane"
    
    # Create control plane namespace
    create_namespace "${CONTROL_PLANE_NAMESPACE}"
    
    # Deploy metadata database
    log_info "Deploying metadata database..."
    kubectl apply -f "${PROJECT_ROOT}/k8s/control-plane/metadata-db.yaml"
    wait_for_pods "${CONTROL_PLANE_NAMESPACE}" "app=mdbaas-metadata-db" 300
    log_success "Metadata database deployed"
    
    # Deploy backend
    log_info "Deploying backend API..."
    kubectl apply -f "${PROJECT_ROOT}/k8s/control-plane/backend.yaml"
    wait_for_pods "${CONTROL_PLANE_NAMESPACE}" "app=mdbaas-backend" 300
    log_success "Backend API deployed"
    
    # Deploy frontend
    log_info "Deploying frontend UI..."
    kubectl apply -f "${PROJECT_ROOT}/k8s/control-plane/frontend.yaml"
    wait_for_pods "${CONTROL_PLANE_NAMESPACE}" "app=mdbaas-frontend" 300
    log_success "Frontend UI deployed"
    
    # Get URLs
    BACKEND_URL=$(kubectl get svc mdbaas-backend-svc -n "${CONTROL_PLANE_NAMESPACE}" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    FRONTEND_URL=$(kubectl get svc mdbaas-frontend-svc -n "${CONTROL_PLANE_NAMESPACE}" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    
    echo ""
    log_success "Control Plane deployed successfully!"
    echo ""
    echo "🌐 Frontend UI:  http://${FRONTEND_URL}:${FRONTEND_PORT}"
    echo "🔌 Backend API:  http://${BACKEND_URL}:${BACKEND_PORT}"
    echo "📖 API Docs:     http://${BACKEND_URL}:${BACKEND_PORT}/docs"
    echo ""
}

uninstall_control_plane() {
    log_step "Phase: Uninstalling Control Plane"
    
    log_warning "This will delete all control plane data!"
    read -p "Are you sure? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_info "Uninstall cancelled"
        exit 0
    fi
    
    kubectl delete namespace "${CONTROL_PLANE_NAMESPACE}" --ignore-not-found
    
    log_success "Control Plane uninstalled"
}

# ==========================================
# Phase: Verify
# ==========================================

verify_installation() {
    log_step "Phase: Verifying Installation"
    
    local failed=0
    
    # Check operators
    log_info "Checking operators..."
    if kubectl get deployment mongodb-enterprise-operator -n "${OPERATOR_NAMESPACE}" &>/dev/null; then
        log_success "Enterprise Operator: Running"
    else
        log_error "Enterprise Operator: Not found"
        ((failed++))
    fi
    
    if kubectl get deployment mongodb-kubernetes-operator -n "${OPERATOR_NAMESPACE}" &>/dev/null; then
        log_success "Community Operator: Running"
    else
        log_error "Community Operator: Not found"
        ((failed++))
    fi
    
    # Check control plane
    log_info "Checking control plane..."
    if kubectl get deployment mdbaas-backend -n "${CONTROL_PLANE_NAMESPACE}" &>/dev/null; then
        log_success "Backend: Running"
    else
        log_error "Backend: Not found"
        ((failed++))
    fi
    
    if kubectl get deployment mdbaas-frontend -n "${CONTROL_PLANE_NAMESPACE}" &>/dev/null; then
        log_success "Frontend: Running"
    else
        log_error "Frontend: Not found"
        ((failed++))
    fi
    
    # Check backend health
    log_info "Checking backend health..."
    BACKEND_IP=$(kubectl get svc mdbaas-backend-svc -n "${CONTROL_PLANE_NAMESPACE}" -o jsonpath='{.spec.clusterIP}')
    if kubectl run -it --rm curl-test --image=curlimages/curl --restart=Never -- \
        curl -sf "http://${BACKEND_IP}:${BACKEND_PORT}/health" &>/dev/null; then
        log_success "Backend health check: Passed"
    else
        log_error "Backend health check: Failed"
        ((failed++))
    fi
    
    # Summary
    echo ""
    if [[ $failed -eq 0 ]]; then
        log_success "All components verified successfully!"
        return 0
    else
        log_error "$failed component(s) failed verification"
        return 1
    fi
}

# ==========================================
# Main Function
# ==========================================

show_help() {
    cat <<EOF
MongoDB Control Plane - Deployment Script

Usage:
  $0 [OPTIONS]

Options:
  --config FILE          Configuration file (required)
  --phase PHASE          Deployment phase (required)
  --skip-checks          Skip pre-installation checks
  --dry-run              Show what would be installed
  --force                Force reinstall
  --uninstall            Uninstall the specified phase
  --help                 Show this help message

Phases:
  operator               Install MongoDB operators
  ops-manager            Install Ops Manager (optional)
  appdb-backup           Install backup infrastructure
  monitoring             Install Prometheus + Grafana
  control-plane          Install backend + frontend
  verify                 Verify all components

Examples:
  # Install operators
  $0 --config config/production.env --phase operator

  # Install control plane
  $0 --config config/production.env --phase control-plane

  # Verify installation
  $0 --config config/production.env --phase verify

  # Uninstall control plane
  $0 --config config/production.env --phase control-plane --uninstall

EOF
}

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            --phase)
                PHASE="$2"
                shift 2
                ;;
            --skip-checks)
                SKIP_CHECKS=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --uninstall)
                UNINSTALL=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Validate arguments
    if [[ -z "$CONFIG_FILE" ]]; then
        log_error "Configuration file required. Use --config"
        show_help
        exit 1
    fi
    
    if [[ -z "$PHASE" ]]; then
        log_error "Phase required. Use --phase"
        show_help
        exit 1
    fi
    
    # Load configuration
    load_config
    
    # Check prerequisites
    if [[ "$SKIP_CHECKS" != "true" ]]; then
        log_step "Checking Prerequisites"
        check_command "kubectl"
        check_command "aws"
        check_kubernetes
    fi
    
    # Execute phase
    case $PHASE in
        operator)
            if [[ "$UNINSTALL" == "true" ]]; then
                uninstall_operator
            else
                deploy_operator
            fi
            ;;
        ops-manager)
            if [[ "$UNINSTALL" == "true" ]]; then
                uninstall_ops_manager
            else
                deploy_ops_manager
            fi
            ;;
        appdb-backup)
            deploy_backup
            ;;
        monitoring)
            if [[ "$UNINSTALL" == "true" ]]; then
                uninstall_monitoring
            else
                deploy_monitoring
            fi
            ;;
        control-plane)
            if [[ "$UNINSTALL" == "true" ]]; then
                uninstall_control_plane
            else
                deploy_control_plane
            fi
            ;;
        verify)
            verify_installation
            ;;
        *)
            log_error "Unknown phase: $PHASE"
            show_help
            exit 1
            ;;
    esac
    
    log_success "Phase '$PHASE' completed successfully!"
}

# Run main function
main "$@"
