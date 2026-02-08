# AtlasForge UI

A MongoDB-themed web interface for managing your MDBaaS (MongoDB Database as a Service) control plane.

## Features

- **Tenant Management**: Onboard and manage multiple tenants with detailed statistics
- **Deployment Lifecycle**: Create, scale, upgrade, and manage MongoDB deployments (Standalone, Replica Sets)
- **Real-time Monitoring**: Auto-refresh status indicators and deployment health
- **Connection Management**: Easy access to MongoDB URIs and mongosh connection strings
- **Prometheus Integration**: Enable/disable Prometheus monitoring with configuration snippets
- **Day-2 Operations**: Scale, upgrade, shutdown, start, and restart deployments
- **MongoDB-themed UI**: Built with LeafyGreen components for a native MongoDB look and feel

## Prerequisites

- Node.js 18+ and npm
- Access to a running MDBaaS Control Plane microservice (FastAPI)
- MongoDB database for control-plane metadata (optional, for read-only access)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd AtlasForge-UI
```

2. Install dependencies:
```bash
npm install
```

3. Configure environment variables:

Create a `.env.local` file in the root directory:

```env
# Control Plane Microservice API
NEXT_PUBLIC_CONTROL_PLANE_API_BASE_URL=http://ec2-34-213-34-101.us-west-2.compute.amazonaws.com:8001

# MongoDB for control-plane metadata (read-only access from server-side)
MCP_MONGODB_URI=mongodb://username:password@host:27017/?authSource=admin
MCP_DB_NAME=mdb_control_plane

# Environment indicator
NEXT_PUBLIC_ENVIRONMENT=DEV
```

**Important**: Copy `.env.local.example` to `.env.local` and update with your actual values.

## Running the Application

### Development Mode

```bash
npm run dev
```

The application will be available at [http://localhost:3000](http://localhost:3000).

### Production Build

```bash
npm run build
npm start
```

### Type Checking

```bash
npm run type-check
```

## Project Structure

```
AtlasForge-UI/
├── components/          # Reusable React components
│   ├── Layout.tsx       # Main layout with sidebar navigation
│   ├── StatusBadge.tsx  # Deployment status indicator
│   ├── Toast.tsx        # Toast notification system
│   ├── CreateTenantModal.tsx
│   ├── CreateDeploymentModal.tsx
│   ├── ScaleDeploymentModal.tsx
│   ├── UpgradeVersionModal.tsx
│   ├── ConfirmActionModal.tsx
│   ├── ConnectionInfoCard.tsx
│   └── PrometheusCard.tsx
├── lib/                 # Utilities and services
│   ├── api/             # API service layer
│   │   ├── tenants.ts
│   │   └── deployments.ts
│   ├── api-client.ts    # HTTP client
│   ├── config.ts        # Environment configuration
│   ├── types.ts         # TypeScript interfaces
│   └── utils.ts         # Helper functions
├── pages/               # Next.js pages
│   ├── _app.tsx         # App wrapper
│   ├── index.tsx        # Tenants overview (home)
│   ├── about.tsx        # About page
│   └── tenants/
│       ├── [tenantId].tsx                           # Tenant details
│       └── [tenantId]/deployments/[deploymentId].tsx # Deployment details
├── styles/              # Global styles
│   └── globals.css
├── package.json
├── tsconfig.json
└── next.config.js
```

## Key Pages

### 1. Tenants Overview (`/`)
- View all tenants with deployment statistics
- Create new tenants
- Navigate to tenant details

### 2. Tenant Details (`/tenants/[tenantId]`)
- View tenant information
- List all deployments for the tenant
- Create new deployments
- View deployment status and details

### 3. Deployment Details (`/tenants/[tenantId]/deployments/[deploymentId]`)
- View deployment configuration and status
- **Overview Tab**: Connection info and lifecycle controls
- **Monitoring Tab**: Prometheus configuration
- **Backup Tab**: Backup enrollment status
- Perform day-2 operations:
  - Scale replica set members
  - Upgrade MongoDB version
  - Shutdown/Start/Restart deployment

## API Integration

The UI communicates with the FastAPI Control Plane microservice via REST APIs:

- `GET /tenants` - List all tenants
- `POST /tenants` - Create a new tenant
- `GET /tenants/{tenantId}/deployments` - List deployments for a tenant
- `POST /tenants/{tenantId}/deployments` - Create a deployment
- `GET /tenants/{tenantId}/deployments/{deploymentId}` - Get deployment details
- `GET /tenants/{tenantId}/deployments/{deploymentId}/connection` - Get connection info
- `PATCH /tenants/{tenantId}/deployments/{deploymentId}/scale` - Scale deployment
- `PATCH /tenants/{tenantId}/deployments/{deploymentId}/version` - Upgrade version
- `POST /tenants/{tenantId}/deployments/{deploymentId}/actions/{action}` - Lifecycle actions
- `PATCH /tenants/{tenantId}/deployments/{deploymentId}/monitoring/prometheus` - Prometheus config

## Features in Detail

### Auto-refresh
- Tenant and deployment pages auto-refresh every 15 seconds
- Manual refresh buttons available on all pages

### Status Indicators
- **Running**: Green badge (deployment is operational)
- **Provisioning/Scaling**: Blue badge (deployment is being created or scaled)
- **Stopped**: Gray badge (deployment is shut down)
- **Error**: Red badge (deployment has errors)

### Validation
- **Scale**: Enforces >= 3 members for replica sets, warns on even numbers
- **Version Upgrade**: Prevents downgrades, validates version format
- **Member Count**: Real-time validation with error and warning messages

### Toast Notifications
- Success notifications for completed actions
- Error notifications with detailed messages
- Warning notifications for configuration issues

## Deployment Types

### Supported
- **Standalone**: Single MongoDB instance
- **Replica Set**: MongoDB replica set with 3+ members

### Coming Soon
- **Sharded Cluster**: MongoDB sharded cluster with configurable shards

## Environment Configuration

### Required Environment Variables

#### NEXT_PUBLIC_CONTROL_PLANE_API_BASE_URL
The base URL of your FastAPI control plane microservice.

Example: `http://ec2-34-213-34-101.us-west-2.compute.amazonaws.com:8001`

#### MCP_MONGODB_URI
MongoDB connection string for control-plane metadata (server-side only, optional).

Example: `mongodb://user:pass@host:27017/?authSource=admin`

#### MCP_DB_NAME
MongoDB database name for control-plane metadata.

Default: `mdb_control_plane`

#### NEXT_PUBLIC_ENVIRONMENT
Environment indicator displayed in the UI sidebar.

Example: `DEV`, `STAGING`, `PROD`

## Security Considerations

- Store sensitive credentials in `.env.local` (never commit to Git)
- Use read-only MongoDB credentials for metadata access
- Implement proper authentication/authorization in production
- Consider using environment-specific API keys
- Use HTTPS in production environments

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Troubleshooting

### API Connection Issues
1. Verify `NEXT_PUBLIC_CONTROL_PLANE_API_BASE_URL` is correct
2. Check that the control plane microservice is running
3. Ensure CORS is properly configured on the microservice
4. Check browser console for network errors

### Build Errors
1. Run `npm install` to ensure all dependencies are installed
2. Check Node.js version (18+ required)
3. Run `npm run type-check` to identify TypeScript errors

### Styling Issues
1. Clear browser cache
2. Restart the development server
3. Ensure all LeafyGreen dependencies are installed

## Contributing

1. Create a feature branch
2. Make your changes
3. Run `npm run type-check` and `npm run lint`
4. Submit a pull request

## License

[Your License Here]

## Support

For issues and questions, please contact your MDBaaS administrator or create an issue in the repository.
