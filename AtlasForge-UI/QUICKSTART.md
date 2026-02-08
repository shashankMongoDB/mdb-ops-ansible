# Quick Start Guide

## Step 1: Install Dependencies

```bash
npm install
```

## Step 2: Configure Environment

The `.env.local` file is already configured with your settings:

```env
NEXT_PUBLIC_CONTROL_PLANE_API_BASE_URL=http://ec2-34-213-34-101.us-west-2.compute.amazonaws.com:8001
MCP_MONGODB_URI=mongodb://shashank:password@ec2-34-213-34-101.us-west-2.compute.amazonaws.com:27017/?authSource=admin
MCP_DB_NAME=mdb_control_plane
NEXT_PUBLIC_ENVIRONMENT=DEV
```

**Note**: For production, update these values and never commit `.env.local` to version control.

## Step 3: Run the Development Server

```bash
npm run dev
```

The application will be available at: [http://localhost:3000](http://localhost:3000)

## Step 4: Explore the UI

### Home Page (Tenants Overview)
- Navigate to `http://localhost:3000/`
- View all tenants with deployment statistics
- Click "Onboard Tenant" to create a new tenant

### Create a Tenant
1. Click "Onboard Tenant"
2. Fill in the form:
   - Tenant ID: `t-demo` (lowercase, hyphens allowed)
   - Display Name: `Demo Tenant`
   - Environment: `dev`
3. Click "Create Tenant"

### Create a MongoDB Deployment
1. Click on a tenant card to view details
2. Click "Create Deployment"
3. Fill in the form:
   - Deployment ID: `rs-myapp`
   - Type: Replica Set
   - MongoDB Version: `8.0.3`
   - Members: `3`
   - Display Name: `My App Database`
   - Environment: `dev`
4. Click "Create Deployment"

### Manage Deployments
1. Click "View Details" on any deployment
2. Use the tabs to navigate:
   - **Overview**: Connection info, lifecycle controls
   - **Monitoring**: Enable/disable Prometheus
   - **Backup**: View backup status

### Day-2 Operations
- **Scale**: Click "Scale Members" to change replica set size
- **Upgrade**: Click "Upgrade Version" to upgrade MongoDB version
- **Restart**: Click "Restart" for rolling restart
- **Shutdown/Start**: Control deployment state

## Production Build

```bash
npm run build
npm start
```

## Type Checking

```bash
npm run type-check
```

## Troubleshooting

### Can't connect to API
- Verify the control plane microservice is running
- Check the URL in `.env.local`
- Check browser console for CORS errors

### Missing dependencies
```bash
rm -rf node_modules package-lock.json
npm install
```

### Port 3000 already in use
```bash
# Use a different port
PORT=3001 npm run dev
```

## Next Steps

1. Customize the MongoDB connection credentials in `.env.local`
2. Test all API endpoints with your control plane
3. Add authentication/authorization if needed
4. Deploy to production environment
5. Configure HTTPS and security headers

## API Endpoints Used

All endpoints are relative to `NEXT_PUBLIC_CONTROL_PLANE_API_BASE_URL`:

- `GET /health` - Health check
- `GET /tenants` - List tenants
- `POST /tenants` - Create tenant
- `GET /tenants/{tenantId}/deployments` - List deployments
- `POST /tenants/{tenantId}/deployments` - Create deployment
- `GET /tenants/{tenantId}/deployments/{deploymentId}` - Deployment details
- `GET /tenants/{tenantId}/deployments/{deploymentId}/connection` - Connection info
- `PATCH /tenants/{tenantId}/deployments/{deploymentId}/scale` - Scale
- `PATCH /tenants/{tenantId}/deployments/{deploymentId}/version` - Upgrade
- `POST /tenants/{tenantId}/deployments/{deploymentId}/actions/{action}` - Lifecycle
- `GET /tenants/{tenantId}/deployments/{deploymentId}/monitoring/prometheus` - Get Prometheus config
- `PATCH /tenants/{tenantId}/deployments/{deploymentId}/monitoring/prometheus` - Update Prometheus

Refer to your Postman collection for complete API documentation.
