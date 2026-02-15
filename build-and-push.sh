#!/bin/bash
# ============================================================
# Build and Push Docker Images
# ============================================================
# Usage: ./build-and-push.sh <registry> <version>
# Example: ./build-and-push.sh docker.io/myorg v1.0.0

set -e

# Check arguments
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <registry> <version>"
    echo "Example: $0 docker.io/myorg v1.0.0"
    exit 1
fi

REGISTRY=$1
VERSION=$2
BACKEND_IMAGE="${REGISTRY}/mdbaas-backend:${VERSION}"
FRONTEND_IMAGE="${REGISTRY}/mdbaas-frontend:${VERSION}"

echo "============================================================"
echo "Building and pushing MDBaaS Control Plane images"
echo "Registry: ${REGISTRY}"
echo "Version: ${VERSION}"
echo "============================================================"

# Build Backend
echo ""
echo "Building Backend image..."
docker build -t "${BACKEND_IMAGE}" ./AtlasForge
docker tag "${BACKEND_IMAGE}" "${REGISTRY}/mdbaas-backend:latest"

# Build Frontend
echo ""
echo "Building Frontend image..."
docker build -t "${FRONTEND_IMAGE}" ./AtlasForge-UI-Vite
docker tag "${FRONTEND_IMAGE}" "${REGISTRY}/mdbaas-frontend:latest"

# Push images
echo ""
echo "Pushing images to registry..."
docker push "${BACKEND_IMAGE}"
docker push "${REGISTRY}/mdbaas-backend:latest"
docker push "${FRONTEND_IMAGE}"
docker push "${REGISTRY}/mdbaas-frontend:latest"

echo ""
echo "============================================================"
echo "✅ Successfully built and pushed images:"
echo "  - ${BACKEND_IMAGE}"
echo "  - ${FRONTEND_IMAGE}"
echo "============================================================"
echo ""
echo "Next steps:"
echo "1. Update k8s-manifests/backend-deployment.yaml with image: ${BACKEND_IMAGE}"
echo "2. Update k8s-manifests/frontend-deployment.yaml with image: ${FRONTEND_IMAGE}"
echo "3. Update k8s-manifests/backend-secret.yaml with your credentials"
echo "4. Run: kubectl apply -f k8s-manifests/"
