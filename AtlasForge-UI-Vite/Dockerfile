# ============================================================
# MongoDB Control Plane - Frontend Dockerfile
# ============================================================
# Multi-stage build for optimized production image

# Stage 1: Build stage
FROM node:18-alpine AS builder

ARG VITE_API_BASE_URL=http://localhost:8001
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install ALL dependencies (including devDependencies needed for build)
# npm ci requires package-lock.json, so fall back to npm install to support builds without a lockfile
RUN npm install && npm cache clean --force

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Stage 2: Runtime stage with nginx
FROM nginx:alpine

# Copy built files from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# Run nginx
CMD ["nginx", "-g", "daemon off;"]