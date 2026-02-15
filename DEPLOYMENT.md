# MDBaaS Control Plane - Deployment Guide

## Overview

This guide covers deploying the MongoDB Control Plane using Docker and Kubernetes.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development with Docker Compose](#local-development-with-docker-compose)
3. [Building Docker Images](#building-docker-images)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Configuration](#configuration)
6. [Testing](#testing)

---

## Prerequisites

### Infrastructure
- **Docker**: 20.10+
- **Kubernetes**: 1.28+
- **kubectl**: Configured with cluster access
- **Docker Registry**: Docker Hub, ECR, GCR, or private registry

### MongoDB Operators (Pre-installed in K8s)
```bash
# MongoDB Enterprise Operator
kubectl apply -f https://raw.githubusercontent.com/mongodb/mongodb-enterprise-kubernetes/master/crds.yaml
kubectl apply -f https://raw.githubusercontent.com/mongodb/mongodb-enterprise-kubernetes/master/mongodb-enterprise.yaml

# MongoDB Community Operator
helm repo add mongodb https://mongodb.github.io/helm-charts
helm install community-operator mongodb/community-operator --namespace mongodb --create-namespace
```

### External Dependencies
- **Control Plane MongoDB**: Standalone MongoDB for metadata
- **Ops Manager**: 6.0+ (for Enterprise deployments)
- **AWS S3**: For Community backups (optional)

---

## Local Development with Docker Compose

### 1. Setup Environment Files

**Backend (.env)**
```bash
cd AtlasForge
cp .env.example .env
# Edit .env with your values
```

**Frontend (.env)**
```bash
cd AtlasForge-UI-Vite
cp .env.example .env
# Edit .env with backend URL
```

### 2. Start Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 3. Access Application

- **Frontend**: http://localhost
- **Backend API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs

---

## Building Docker Images

### Option 1: Automated Build Script

```bash
# Make script executable
chmod +x build-and-push.sh

# Build and push
./build-and-push.sh docker.io/your-username v1.0.0
```

### Option 2: Manual Build

**Backend**
```bash
cd AtlasForge
docker build -t your-registry/mdbaas-backend:v1.0.0 .
docker tag your-registry/mdbaas-backend:v1.0.0 your-registry/mdbaas-backend:latest
docker push your-registry/mdbaas-backend:v1.0.0
docker push your-registry/mdbaas-backend:latest
```

**Frontend**
```bash
cd AtlasForge-UI-Vite
docker build -t your-registry/mdbaas-frontend:v1.0.0 .
docker tag your-registry/mdbaas-frontend:v1.0.0 your-registry/mdbaas-frontend:latest
docker push your-registry/mdbaas-frontend:v1.0.0
docker push your-registry/mdbaas-frontend:latest
```

### Test Images Locally

```bash
# Test backend
docker run -p 8001:8001 --env-file AtlasForge/.env your-registry/mdbaas-backend:v1.0.0

# Test frontend
docker run -p 80:80 your-registry/mdbaas-frontend:v1.0.0
```

---

## Kubernetes Deployment

### 1. Prepare Configuration

#### Update Secrets
```bash
# Edit k8s-manifests/backend-secret.yaml
# Replace with your actual credentials:
# - MCP_MONGODB_URI
# - MCP_OPS_MANAGER_URL
# - MCP_OPS_MANAGER_ORG
# - MCP_OM_GLOBAL_PUBLIC_KEY
# - MCP_OM_GLOBAL_PRIVATE_KEY
# - AWS_ACCESS_KEY_ID (if not using IRSA)
# - AWS_SECRET_ACCESS_KEY (if not using IRSA)
```

#### Update Image References
```bash
# Edit k8s-manifests/backend-deployment.yaml
# Line 22: image: your-registry/mdbaas-backend:v1.0.0

# Edit k8s-manifests/frontend-deployment.yaml
# Line 22: image: your-registry/mdbaas-frontend:v1.0.0
```

### 2. Deploy to Kubernetes

```bash
# Apply all manifests
kubectl apply -f k8s-manifests/

# Verify deployment
kubectl get all -n mdbaas-control-plane
```

### 3. Check Status

```bash
# Check pods
kubectl get pods -n mdbaas-control-plane

# Check services
kubectl get svc -n mdbaas-control-plane

# View logs
kubectl logs -f deployment/backend -n mdbaas-control-plane
kubectl logs -f deployment/frontend -n mdbaas-control-plane
```

### 4. Access Application

#### Option A: LoadBalancer (Default)
```bash
# Get frontend external IP
kubectl get svc frontend -n mdbaas-control-plane

# Access via EXTERNAL-IP
# Example: http://a1b2c3d4.elb.amazonaws.com
```

#### Option B: Port Forward (Testing)
```bash
# Frontend
kubectl port-forward -n mdbaas-control-plane svc/frontend 8080:80

# Backend
kubectl port-forward -n mdbaas-control-plane svc/backend 8001:8001

# Access
# Frontend: http://localhost:8080
# Backend API: http://localhost:8001
# API Docs: http://localhost:8001/docs
```

#### Option C: Ingress (Production)
```yaml
# Create ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mdbaas-ingress
  namespace: mdbaas-control-plane
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - mdbaas.your-domain.com
    secretName: mdbaas-tls
  rules:
  - host: mdbaas.your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 80
  - host: api.mdbaas.your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 8001
```

---

## Configuration

### Backend Environment Variables

See `AtlasForge/.env.example` for complete reference.

**Required:**
- `MCP_MONGODB_URI`: Control plane MongoDB
- `MCP_KUBECONFIG_PATH`: Path to kubeconfig
- `MCP_OPS_MANAGER_URL`: Ops Manager URL
- `MCP_OPS_MANAGER_ORG`: Ops Manager Organization ID
- `MCP_OM_GLOBAL_PUBLIC_KEY`: Ops Manager API public key
- `MCP_OM_GLOBAL_PRIVATE_KEY`: Ops Manager API private key

**Optional:**
- `AWS_ACCESS_KEY_ID`: AWS credentials (non-EKS)
- `AWS_SECRET_ACCESS_KEY`: AWS credentials (non-EKS)
- `COMMUNITY_BACKUP_S3_BUCKET`: Default S3 bucket
- `COMMUNITY_BACKUP_IRSA_ROLE_ARN`: IRSA role (EKS)

### Frontend Environment Variables

See `AtlasForge-UI-Vite/.env.example` for complete reference.

**Required:**
- `VITE_API_BASE_URL`: Backend API URL

---

## Testing

### Health Checks

```bash
# Backend health
curl http://localhost:8001/health

# Frontend health
curl http://localhost/health

# In Kubernetes
kubectl exec -it deployment/backend -n mdbaas-control-plane -- curl http://localhost:8001/health
```

### API Testing

```bash
# List tenants
curl http://localhost:8001/tenants

# Create tenant
curl -X POST http://localhost:8001/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "tenantId": "test-tenant",
    "displayName": "Test Tenant",
    "plan": "community"
  }'
```

### UI Testing

1. Open browser: http://localhost (or LoadBalancer IP)
2. Create a tenant
3. Create a deployment
4. Verify in Kubernetes:
   ```bash
   kubectl get mongodbcommunity -A
   kubectl get mongodb -A
   ```

---

## Production Checklist

- [ ] Use Ingress with TLS/SSL certificates
- [ ] Configure HorizontalPodAutoscaler for scaling
- [ ] Set up monitoring (Prometheus + Grafana)
- [ ] Configure log aggregation (ELK, Loki)
- [ ] Use external secrets management (Vault, AWS Secrets Manager)
- [ ] Enable network policies for security
- [ ] Configure resource requests/limits based on load testing
- [ ] Set up backup for control plane MongoDB
- [ ] Configure alerting for critical failures
- [ ] Document disaster recovery procedures
- [ ] Implement CI/CD pipeline
- [ ] Regular security scanning of Docker images

---

## Troubleshooting

### Backend Won't Start

```bash
# Check logs
kubectl logs deployment/backend -n mdbaas-control-plane

# Common issues:
# - MongoDB connection failed: Check MCP_MONGODB_URI
# - Kubeconfig not found: Check volume mount
# - Ops Manager unreachable: Check MCP_OPS_MANAGER_URL
```

### Frontend Can't Connect to Backend

```bash
# Check service connectivity
kubectl exec -it deployment/frontend -n mdbaas-control-plane -- wget -O- http://backend:8001/health

# Common issues:
# - Wrong VITE_API_BASE_URL: Should be http://backend:8001 (in-cluster) or LoadBalancer IP (external)
# - Backend service not running
# - Network policy blocking traffic
```

### Permission Errors

```bash
# Check ServiceAccount and RBAC
kubectl get sa mdbaas-backend-sa -n mdbaas-control-plane
kubectl describe clusterrolebinding mdbaas-backend-binding

# Verify permissions
kubectl auth can-i create mongodb --as=system:serviceaccount:mdbaas-control-plane:mdbaas-backend-sa
```

---

## Support

- **Documentation**: README.md
- **API Reference**: http://localhost:8001/docs
- **Postman Collection**: MongoDB_Control_Plane.postman_collection.json

---

**Built with ❤️ for MongoDB-as-a-Service providers**
