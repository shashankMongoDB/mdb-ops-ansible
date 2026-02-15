# Kubernetes Deployment Guide

## Prerequisites

1. **Kubernetes Cluster**: Version 1.28+
2. **kubectl**: Configured with cluster-admin access
3. **MongoDB Operators**: Installed (Enterprise and/or Community)
4. **Docker Registry Access**: For pulling images
5. **Secrets**: Update `backend-secret.yaml` with your credentials

## Quick Deploy

### 1. Update Configuration

Edit `backend-secret.yaml` and update with your actual values:
- MongoDB connection string
- Ops Manager URL and credentials
- AWS credentials (if not using IRSA)

### 2. Build and Push Images

```bash
# Build and push to your registry
./build-and-push.sh docker.io/your-org v1.0.0

# Or use Docker Hub
./build-and-push.sh your-dockerhub-username v1.0.0
```

### 3. Update Image References

Edit deployment manifests:
- `backend-deployment.yaml`: Line 22 - Update image name
- `frontend-deployment.yaml`: Line 22 - Update image name

### 4. Deploy to Kubernetes

```bash
# Apply all manifests
kubectl apply -f k8s-manifests/

# Check deployment status
kubectl get all -n mdbaas-control-plane

# Check logs
kubectl logs -f deployment/backend -n mdbaas-control-plane
kubectl logs -f deployment/frontend -n mdbaas-control-plane
```

## Files Overview

| File | Purpose |
|------|---------|
| `namespace.yaml` | Creates mdbaas-control-plane namespace |
| `backend-serviceaccount.yaml` | RBAC permissions for backend |
| `backend-configmap.yaml` | Non-sensitive configuration |
| `backend-secret.yaml` | Sensitive credentials |
| `backend-deployment.yaml` | Backend deployment + service |
| `frontend-deployment.yaml` | Frontend deployment + service (LoadBalancer) |

## Access the Application

### Get Frontend URL

```bash
# For LoadBalancer
kubectl get svc frontend -n mdbaas-control-plane

# Output:
# NAME       TYPE           CLUSTER-IP      EXTERNAL-IP     PORT(S)        AGE
# frontend   LoadBalancer   10.100.200.50   a1b2c3.elb...   80:32123/TCP   5m

# Access via EXTERNAL-IP
open http://<EXTERNAL-IP>
```

### Port Forward (Alternative)

```bash
# Frontend
kubectl port-forward -n mdbaas-control-plane svc/frontend 8080:80

# Backend (for API docs)
kubectl port-forward -n mdbaas-control-plane svc/backend 8001:8001

# Access
open http://localhost:8080  # UI
open http://localhost:8001/docs  # API docs
```

## Scaling

```bash
# Scale backend
kubectl scale deployment backend -n mdbaas-control-plane --replicas=3

# Scale frontend
kubectl scale deployment frontend -n mdbaas-control-plane --replicas=3
```

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n mdbaas-control-plane
kubectl describe pod <pod-name> -n mdbaas-control-plane
```

### View Logs

```bash
# Backend logs
kubectl logs -f deployment/backend -n mdbaas-control-plane

# Frontend logs
kubectl logs -f deployment/frontend -n mdbaas-control-plane

# All pods
kubectl logs -f -l app=mdbaas-backend -n mdbaas-control-plane --all-containers=true
```

### Check Events

```bash
kubectl get events -n mdbaas-control-plane --sort-by='.lastTimestamp'
```

### Test Connectivity

```bash
# Test backend health
kubectl exec -it deployment/frontend -n mdbaas-control-plane -- wget -O- http://backend:8001/health

# Test from local machine
kubectl port-forward -n mdbaas-control-plane svc/backend 8001:8001
curl http://localhost:8001/health
```

## Updating

### Update Images

```bash
# Build new version
./build-and-push.sh your-registry v1.1.0

# Update deployment
kubectl set image deployment/backend backend=your-registry/mdbaas-backend:v1.1.0 -n mdbaas-control-plane
kubectl set image deployment/frontend frontend=your-registry/mdbaas-frontend:v1.1.0 -n mdbaas-control-plane

# Check rollout status
kubectl rollout status deployment/backend -n mdbaas-control-plane
kubectl rollout status deployment/frontend -n mdbaas-control-plane
```

### Rollback

```bash
# Rollback to previous version
kubectl rollout undo deployment/backend -n mdbaas-control-plane
kubectl rollout undo deployment/frontend -n mdbaas-control-plane
```

## Cleanup

```bash
# Delete all resources
kubectl delete -f k8s-manifests/

# Or delete namespace (deletes everything inside)
kubectl delete namespace mdbaas-control-plane
```

## Production Considerations

1. **Ingress**: Replace LoadBalancer with Ingress for SSL/TLS
2. **Secrets Management**: Use external secrets (Vault, AWS Secrets Manager)
3. **Resource Limits**: Adjust based on load testing
4. **Monitoring**: Add Prometheus/Grafana for observability
5. **Backup**: Regular backups of control plane MongoDB
6. **High Availability**: Run multiple replicas across zones
7. **Network Policies**: Restrict traffic between components
