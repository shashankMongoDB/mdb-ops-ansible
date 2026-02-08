# AtlasForge UI - Project Summary

## Overview

AtlasForge UI is a complete, MongoDB-themed web interface for managing your MDBaaS control plane. Built with Next.js, React, TypeScript, and MongoDB LeafyGreen components.

## Architecture

### Frontend Stack
- **Framework**: Next.js 14.2.3
- **UI Library**: React 18.3.1
- **Language**: TypeScript 5
- **Components**: MongoDB LeafyGreen UI
- **Styling**: LeafyGreen + CSS

### API Integration
- REST API client communicating with FastAPI control plane microservice
- Environment-configurable API base URL
- Comprehensive error handling and toast notifications

## Project Structure

```
AtlasForge-UI/
├── components/              # Reusable UI components
│   ├── Layout.tsx           # Main layout with sidebar navigation
│   ├── StatusBadge.tsx      # Deployment status indicator
│   ├── Toast.tsx            # Toast notification provider
│   ├── CreateTenantModal.tsx
│   ├── CreateDeploymentModal.tsx
│   ├── ScaleDeploymentModal.tsx
│   ├── UpgradeVersionModal.tsx
│   ├── ConfirmActionModal.tsx
│   ├── ConnectionInfoCard.tsx
│   └── PrometheusCard.tsx
│
├── lib/                     # Business logic and utilities
│   ├── api/                 # API service layer
│   │   ├── tenants.ts       # Tenant API endpoints
│   │   └── deployments.ts   # Deployment API endpoints
│   ├── api-client.ts        # HTTP client wrapper
│   ├── config.ts            # Environment configuration
│   ├── types.ts             # TypeScript interfaces
│   └── utils.ts             # Helper functions
│
├── pages/                   # Next.js pages (routes)
│   ├── _app.tsx             # App wrapper with providers
│   ├── _document.tsx        # HTML document structure
│   ├── index.tsx            # Home: Tenants overview
│   ├── about.tsx            # About page
│   └── tenants/
│       ├── [tenantId].tsx   # Tenant details page
│       └── [tenantId]/deployments/
│           └── [deploymentId].tsx  # Deployment details page
│
├── styles/
│   └── globals.css          # Global styles
│
├── package.json             # Dependencies and scripts
├── tsconfig.json            # TypeScript configuration
├── next.config.js           # Next.js configuration
├── .eslintrc.json           # ESLint configuration
├── .env.local               # Environment variables (git-ignored)
├── .env.local.example       # Environment template
├── README.md                # Full documentation
├── QUICKSTART.md            # Quick start guide
└── PROJECT_SUMMARY.md       # This file
```

## Pages and Routes

### 1. Home / Tenants Overview (`/`)
**File**: `pages/index.tsx`

**Features**:
- Grid view of all tenants with cards
- Displays per-tenant statistics:
  - Total deployments
  - Running deployments (green)
  - Error deployments (red)
- "Onboard Tenant" button → opens modal
- Auto-refresh every 15 seconds
- Click card → navigate to tenant details

**Components Used**:
- `CreateTenantModal` - For tenant onboarding
- LeafyGreen: Card, Badge, Button, Icon

### 2. Tenant Details (`/tenants/[tenantId]`)
**File**: `pages/tenants/[tenantId].tsx`

**Features**:
- Tenant metadata card (ID, namespace, environment)
- Table of all deployments for the tenant
- Columns: Deployment ID, Display Name, Type, Version, Members, Status, Actions
- "Create Deployment" button → opens modal
- Real-time status badges
- Auto-refresh every 15 seconds
- Click "View Details" → navigate to deployment details

**Components Used**:
- `CreateDeploymentModal` - For creating deployments
- `StatusBadge` - For deployment status
- LeafyGreen: Table, Card, Badge, Button

### 3. Deployment Details (`/tenants/[tenantId]/deployments/[deploymentId]`)
**File**: `pages/tenants/[tenantId]/deployments/[deploymentId].tsx`

**Features**:
- Deployment metadata card (ID, type, version, members, status)
- Three tabs:
  1. **Overview**: 
     - Lifecycle control buttons (Scale, Upgrade, Restart, Shutdown/Start)
     - Connection info card with MongoDB URI and mongosh example
     - Copy buttons for easy clipboard access
  2. **Monitoring**:
     - Prometheus toggle (enable/disable)
     - Metrics endpoint info when enabled
     - Prometheus YAML snippet for scrape config
  3. **Backup**:
     - Backup enrollment status indicator
     - Note about CR-based configuration

**Components Used**:
- `ScaleDeploymentModal` - Scale replica set members
- `UpgradeVersionModal` - Upgrade MongoDB version
- `ConfirmActionModal` - Confirm shutdown/start/restart
- `ConnectionInfoCard` - Connection strings
- `PrometheusCard` - Prometheus monitoring
- `StatusBadge` - Real-time status
- LeafyGreen: Tabs, Card, Button, Badge, Toggle

### 4. About Page (`/about`)
**File**: `pages/about.tsx`

**Features**:
- Overview of AtlasForge UI
- Feature list
- Deployment types supported
- Current configuration display
- Technology stack info
- Version information

## Components

### Layout Components

#### `Layout.tsx`
- Main application layout
- Left sidebar navigation with SideNav
- Environment badge in sidebar footer
- Content area wrapper
- LeafyGreenProvider wrapper

#### `StatusBadge.tsx`
- Visual status indicator for deployments
- Color-coded badges:
  - Green: Running
  - Blue: Provisioning/Scaling
  - Gray: Stopped/Deleted
  - Red: Error
  - Yellow: Unknown
- Shows ready/desired counts when available

### Modal Components

#### `CreateTenantModal.tsx`
- Form for onboarding new tenants
- Fields: Tenant ID, Display Name, Environment, Notes
- Validation: tenant ID format (lowercase, hyphens)
- Error handling with toast notifications
- Calls `POST /tenants`

#### `CreateDeploymentModal.tsx`
- Form for creating MongoDB deployments
- Deployment types: Standalone, ReplicaSet, ShardedCluster (disabled)
- Fields: Deployment ID, Type, Version, Members, Display Name, Environment
- Real-time validation for member count (>= 3, odd number recommended)
- Warning banners for even member counts
- Calls `POST /tenants/{tenantId}/deployments`

#### `ScaleDeploymentModal.tsx`
- Form for scaling replica set members
- Shows current member count
- New member count input with validation
- Error on < 3 members
- Warning on even member counts
- Prevents no-change submissions
- Calls `PATCH /tenants/{tenantId}/deployments/{deploymentId}/scale`

#### `UpgradeVersionModal.tsx`
- Form for upgrading MongoDB version
- Shows current version
- New version input
- Downgrade detection and blocking
- Warning banner for downgrade attempts
- Prevents same-version submissions
- Calls `PATCH /tenants/{tenantId}/deployments/{deploymentId}/version`

#### `ConfirmActionModal.tsx`
- Generic confirmation dialog
- Configurable title, message, confirm text
- Support for "danger" variant (red button)
- Used for shutdown, start, restart actions

### Card Components

#### `ConnectionInfoCard.tsx`
- Displays MongoDB connection information
- Shows MongoDB URI with copy button
- Shows mongosh connection example with copy button
- Uses Code component for syntax highlighting
- Loads data via `GET /connection` endpoint

#### `PrometheusCard.tsx`
- Prometheus monitoring configuration
- Toggle to enable/disable Prometheus
- Shows metrics endpoint when enabled
- Displays Prometheus YAML scrape config
- Copyable code block
- Confirmation modal for enable/disable
- Calls `GET /monitoring/prometheus` and `PATCH /monitoring/prometheus`

### Utility Components

#### `Toast.tsx`
- Toast notification system with React Context
- `ToastProvider` - Context provider
- `useToast()` - Hook for showing toasts
- Methods:
  - `showSuccess(title, body?)` - Green success toast
  - `showError(title, body?)` - Red error toast
  - `showWarning(title, body?)` - Yellow warning toast
- Auto-dismiss after 5 seconds

## API Service Layer

### `lib/api-client.ts`
Generic HTTP client with error handling:
- `get<T>(endpoint)` - GET request
- `post<T>(endpoint, data?)` - POST request
- `patch<T>(endpoint, data)` - PATCH request
- `delete<T>(endpoint)` - DELETE request
- Automatic JSON parsing
- Error handling with `ApiError` interface
- Content-Type headers

### `lib/api/tenants.ts`
Tenant-specific API calls:
- `getAll()` - GET /tenants
- `getById(tenantId)` - GET /tenants/{tenantId}
- `create(data)` - POST /tenants
- `delete(tenantId)` - DELETE /tenants/{tenantId}

### `lib/api/deployments.ts`
Deployment-specific API calls:
- `getAllForTenant(tenantId)` - GET /tenants/{tenantId}/deployments
- `getById(tenantId, deploymentId)` - GET deployment details
- `create(tenantId, data)` - POST create deployment
- `delete(tenantId, deploymentId)` - DELETE deployment
- `getConnectionInfo(tenantId, deploymentId)` - GET connection strings
- `scale(tenantId, deploymentId, data)` - PATCH scale
- `upgradeVersion(tenantId, deploymentId, data)` - PATCH version
- `shutdown(tenantId, deploymentId)` - POST shutdown action
- `start(tenantId, deploymentId)` - POST start action
- `restart(tenantId, deploymentId)` - POST restart action
- `getPrometheusConfig(tenantId, deploymentId)` - GET Prometheus config
- `updatePrometheus(tenantId, deploymentId, data)` - PATCH Prometheus
- `updateMonitoring(tenantId, deploymentId, data)` - PATCH monitoring
- `updateBackup(tenantId, deploymentId, data)` - PATCH backup

## Type Definitions (`lib/types.ts`)

### Core Types
- `Tenant` - Tenant metadata
- `Deployment` - Deployment configuration and status
- `DeploymentStatus` - Status phase, ready/desired counts
- `ConnectionInfo` - MongoDB URI and connection examples
- `PrometheusConfig` - Prometheus monitoring configuration
- `BackupConfig` - Backup enrollment status
- `TenantWithStats` - Tenant with deployment statistics

### Request Types
- `CreateTenantRequest`
- `CreateDeploymentRequest`
- `ScaleDeploymentRequest`
- `UpgradeVersionRequest`
- `MonitoringRequest`
- `PrometheusRequest`
- `BackupRequest`

### Error Types
- `ApiError` - API error response structure

## Utility Functions (`lib/utils.ts`)

- `getStatusColor(phase)` - Map deployment phase to badge color
- `formatTimestamp(timestamp)` - Format ISO timestamp for display
- `validateMembers(members)` - Validate replica set member count
  - Returns: `{ valid: boolean, warning?: string, error?: string }`
- `compareVersions(v1, v2)` - Compare MongoDB version strings
- `isDowngrade(currentVersion, newVersion)` - Check if version is downgrade
- `copyToClipboard(text)` - Copy text to clipboard with fallback

## Configuration (`lib/config.ts`)

Environment variables:
- `apiBaseUrl` - Control plane API base URL (required)
- `environment` - Environment name (DEV, STAGING, PROD)
- `mongodbUri` - MongoDB connection string (optional, server-side)
- `dbName` - MongoDB database name (optional)

## Features

### 1. Tenant Management
- Create tenants with validation
- View all tenants with statistics
- Navigate to tenant details
- Delete tenants (via API, not yet in UI)

### 2. Deployment Lifecycle
- Create deployments (Standalone, ReplicaSet)
- View deployment details and status
- Scale replica set members with validation
- Upgrade MongoDB version with downgrade protection
- Shutdown, start, restart deployments
- Delete deployments (via API, not yet in UI)

### 3. Monitoring & Observability
- Real-time status indicators
- Auto-refresh every 15 seconds
- Manual refresh buttons
- Prometheus metrics integration
- Enable/disable Prometheus with toggle
- Prometheus scrape config generation

### 4. Connection Management
- MongoDB URI display with copy
- mongosh connection example with copy
- Host list (when available)

### 5. User Experience
- MongoDB LeafyGreen themed UI
- Toast notifications for all actions
- Confirmation modals for destructive actions
- Form validation with real-time feedback
- Warning banners for configuration issues
- Loading states and error handling
- Responsive layout

### 6. Validation & Safety
- Tenant ID format validation (lowercase, hyphens)
- Replica set member count validation (>= 3)
- Even member count warnings
- Version downgrade prevention
- No-change submission prevention
- Confirmation for shutdown/start/restart

## Environment Variables

Create `.env.local` in project root:

```env
# Required: Control Plane API
NEXT_PUBLIC_CONTROL_PLANE_API_BASE_URL=http://your-api-host:8001

# Optional: MongoDB metadata DB (read-only)
MCP_MONGODB_URI=mongodb://user:pass@host:27017/?authSource=admin
MCP_DB_NAME=mdb_control_plane

# Optional: Environment indicator
NEXT_PUBLIC_ENVIRONMENT=DEV
```

## Getting Started

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
npm start

# Type check
npm run type-check

# Lint
npm run lint
```

## API Endpoints Mapped

From Postman collection to UI features:

| Endpoint | Method | UI Feature |
|----------|--------|------------|
| `/health` | GET | Health check (not in UI yet) |
| `/tenants` | GET | Tenants overview page |
| `/tenants` | POST | Create Tenant modal |
| `/tenants/{id}` | DELETE | Not yet implemented |
| `/tenants/{id}/deployments` | GET | Tenant details page |
| `/tenants/{id}/deployments` | POST | Create Deployment modal |
| `/tenants/{id}/deployments/{did}` | GET | Deployment details page |
| `/tenants/{id}/deployments/{did}` | DELETE | Not yet implemented |
| `/tenants/{id}/deployments/{did}/connection` | GET | Connection Info card |
| `/tenants/{id}/deployments/{did}/scale` | PATCH | Scale Deployment modal |
| `/tenants/{id}/deployments/{did}/version` | PATCH | Upgrade Version modal |
| `/tenants/{id}/deployments/{did}/actions/shutdown` | POST | Shutdown button |
| `/tenants/{id}/deployments/{did}/actions/start` | POST | Start button |
| `/tenants/{id}/deployments/{did}/actions/restart` | POST | Restart button |
| `/tenants/{id}/deployments/{did}/monitoring/prometheus` | GET | Prometheus card |
| `/tenants/{id}/deployments/{did}/monitoring/prometheus` | PATCH | Prometheus toggle |
| `/tenants/{id}/deployments/{did}/backup` | PATCH | Not yet implemented |

## Future Enhancements

### Short Term
- Health check indicator in UI
- Delete tenant functionality
- Delete deployment functionality
- Backup enable/disable toggle
- Search and filter for tenants/deployments

### Medium Term
- Sharded Cluster support
- Cluster topology visualization
- Logs viewer
- Metrics charts (integrate with Prometheus)
- Deployment templates

### Long Term
- User authentication and authorization
- Role-based access control (RBAC)
- Audit logs
- Multi-region support
- Cost estimation and tracking
- Backup restore UI
- PITR (Point-in-Time Recovery) controls

## Testing Checklist

Before deploying to production:

- [ ] Verify API connectivity
- [ ] Test tenant creation
- [ ] Test deployment creation (Standalone)
- [ ] Test deployment creation (ReplicaSet)
- [ ] Test scale operation
- [ ] Test version upgrade
- [ ] Test shutdown/start/restart
- [ ] Test Prometheus enable/disable
- [ ] Verify connection info display
- [ ] Test member count validation
- [ ] Test version downgrade prevention
- [ ] Verify auto-refresh works
- [ ] Test error handling (API down, 404s, etc.)
- [ ] Test toast notifications
- [ ] Verify all modals close properly
- [ ] Test navigation between pages
- [ ] Cross-browser testing

## Security Considerations

- Store credentials in `.env.local` (git-ignored)
- Use read-only MongoDB credentials for metadata
- Implement authentication in production
- Use HTTPS in production
- Add CORS configuration on API
- Consider rate limiting
- Add input sanitization
- Implement CSRF protection
- Add security headers

## Production Deployment

### Build
```bash
npm run build
```

### Environment Variables
Set these in your production environment:
- `NEXT_PUBLIC_CONTROL_PLANE_API_BASE_URL`
- `MCP_MONGODB_URI` (optional)
- `MCP_DB_NAME` (optional)
- `NEXT_PUBLIC_ENVIRONMENT=PROD`

### Deploy Options
- Vercel (recommended for Next.js)
- AWS (ECS, EKS, Amplify)
- Docker container
- Traditional Node.js hosting

### Docker Example
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

## Support

For issues or questions:
1. Check the README.md
2. Check the QUICKSTART.md
3. Review API endpoint mappings in Postman collection
4. Contact your MDBaaS administrator

## Version

**Current Version**: 0.1.0

**Last Updated**: 2026-02-09
