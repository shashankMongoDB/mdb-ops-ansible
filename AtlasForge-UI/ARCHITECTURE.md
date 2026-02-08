# AtlasForge UI - Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser (User)                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AtlasForge UI (Next.js)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │    Pages     │  │  Components  │  │   API Services     │   │
│  │              │  │              │  │                    │   │
│  │ • Tenants    │  │ • Modals     │  │ • tenants.ts       │   │
│  │ • Deployments│  │ • Cards      │  │ • deployments.ts   │   │
│  │ • About      │  │ • Layout     │  │ • api-client.ts    │   │
│  └──────────────┘  └──────────────┘  └────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ REST API (HTTP/JSON)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│             Control Plane Microservice (FastAPI)                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Endpoints:                                               │  │
│  │  • POST   /tenants                                        │  │
│  │  • GET    /tenants                                        │  │
│  │  • POST   /tenants/{id}/deployments                       │  │
│  │  • GET    /tenants/{id}/deployments                       │  │
│  │  • PATCH  /tenants/{id}/deployments/{did}/scale          │  │
│  │  • PATCH  /tenants/{id}/deployments/{did}/version        │  │
│  │  • POST   /tenants/{id}/deployments/{did}/actions/*      │  │
│  │  • GET/PATCH /tenants/{id}/deployments/{did}/monitoring  │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────┬───────────────────────────┬────────────────────┘
                 │                           │
                 │ Kubernetes API            │ Read/Write
                 ▼                           ▼
┌────────────────────────────┐   ┌─────────────────────────┐
│   Kubernetes Cluster        │   │  MongoDB (Metadata)     │
│                            │   │                         │
│ • MongoDB Operator CRs     │   │ • tenants collection    │
│ • StatefulSets             │   │ • deployments collection│
│ • Services                 │   │ • status tracking       │
│ • ConfigMaps               │   │                         │
└────────────────────────────┘   └─────────────────────────┘
```

## Data Flow

### 1. Tenant Creation Flow
```
User → Create Tenant Modal → POST /tenants
  ↓
FastAPI validates & stores → MongoDB (tenants collection)
  ↓
UI refreshes → GET /tenants → Display tenant card
```

### 2. Deployment Creation Flow
```
User → Create Deployment Modal → POST /tenants/{id}/deployments
  ↓
FastAPI creates CR → Kubernetes (MongoDB Operator)
  ↓
Operator provisions → MongoDB StatefulSet + Pods
  ↓
Status tracked → MongoDB (deployments collection)
  ↓
UI polls → GET /deployments/{id} → Display status badge
```

### 3. Scale Operation Flow
```
User → Scale Modal → PATCH /deployments/{id}/scale
  ↓
FastAPI updates CR → Kubernetes
  ↓
Operator scales → Add/Remove pods
  ↓
Status updated → MongoDB
  ↓
UI shows → Status: Scaling → Status: Running
```

### 4. Monitoring Flow
```
User → Prometheus Toggle → PATCH /monitoring/prometheus
  ↓
FastAPI updates CR → spec.prometheus.enabled = true
  ↓
Operator exposes → Service with /metrics endpoint
  ↓
UI displays → Metrics endpoint + YAML config
```

## Component Hierarchy

```
App (_app.tsx)
└── ToastProvider
    └── Layout
        ├── SideNav
        │   ├── "Tenants" link
        │   ├── "About" link
        │   └── Environment Badge
        └── Main Content
            └── Page Component
                ├── Tenants Overview (/)
                │   ├── Tenant Cards
                │   └── CreateTenantModal
                ├── Tenant Details (/tenants/[id])
                │   ├── Tenant Info Card
                │   ├── Deployments Table
                │   │   └── StatusBadge (per row)
                │   └── CreateDeploymentModal
                └── Deployment Details (/tenants/[id]/deployments/[did])
                    ├── Deployment Info Card
                    │   └── StatusBadge
                    ├── Tabs
                    │   ├── Overview Tab
                    │   │   ├── Lifecycle Buttons
                    │   │   └── ConnectionInfoCard
                    │   ├── Monitoring Tab
                    │   │   └── PrometheusCard
                    │   └── Backup Tab
                    ├── ScaleDeploymentModal
                    ├── UpgradeVersionModal
                    └── ConfirmActionModal (x3)
```

## State Management

### Page-Level State
Each page manages its own state using React `useState`:
- **Tenants Page**: `tenants[]`, `loading`, `showCreateModal`
- **Tenant Details**: `tenant`, `deployments[]`, `loading`, `showCreateModal`
- **Deployment Details**: `deployment`, `loading`, modals state, `actionLoading`

### Context State
- **ToastProvider**: Global toast notification queue

### Auto-Refresh
- Implemented via `useEffect` + `setInterval`
- Runs every 15 seconds on:
  - Tenant Details page (refresh deployments list)
  - Deployment Details page (refresh deployment status)

### No Global State Management
- Deliberate choice for simplicity
- Each page fetches its own data
- Parent-child communication via props and callbacks

## API Client Architecture

```
Component
  ↓ (calls)
API Service (tenants.ts / deployments.ts)
  ↓ (uses)
API Client (api-client.ts)
  ↓ (HTTP)
FastAPI Control Plane
```

**API Client Features**:
- Generic request wrapper
- Automatic JSON parsing
- Error handling with typed `ApiError`
- Centralized headers management
- No external HTTP library (uses native `fetch`)

## Routing

Next.js file-based routing:

| File Path | Route | Purpose |
|-----------|-------|---------|
| `pages/index.tsx` | `/` | Tenants overview |
| `pages/about.tsx` | `/about` | About page |
| `pages/tenants/[tenantId].tsx` | `/tenants/t-acme` | Tenant details |
| `pages/tenants/[tenantId]/deployments/[deploymentId].tsx` | `/tenants/t-acme/deployments/rs-orders` | Deployment details |

**Dynamic Routes**:
- `[tenantId]` - Tenant ID from URL
- `[deploymentId]` - Deployment ID from URL
- Accessed via `useRouter()` hook

## Error Handling Strategy

### API Errors
```
API Request Fails
  ↓
API Client catches error
  ↓
Throws ApiError { detail, status }
  ↓
Component catch block
  ↓
useToast().showError(title, detail)
  ↓
User sees red toast notification
```

### Validation Errors
```
User enters invalid data
  ↓
Local validation (utils.ts)
  ↓
Form shows error state
  ↓
Submit button disabled
  ↓
User corrects input
  ↓
Form enables submit
```

### Network Errors
- Handled by API client
- Shows generic error message
- User can retry action

## Security Architecture

### Client-Side
- Environment variables for API URL
- No secrets in client code
- HTTPS in production
- CORS headers required on API

### Server-Side (Future)
- Authentication middleware
- JWT tokens
- Role-based access control
- Rate limiting
- Input validation

### MongoDB Access
- Read-only credentials recommended
- Network access restricted
- Authentication required
- Audit logging

## Performance Optimizations

### Current
- Component-level code splitting (Next.js default)
- Automatic static optimization
- Image optimization (Next.js)
- Efficient re-renders (React)

### Future
- API response caching
- Debounced search/filter
- Virtualized tables for large datasets
- Lazy loading for tabs
- Service worker for offline support

## Scalability Considerations

### Frontend
- Stateless Next.js app (can scale horizontally)
- CDN for static assets
- Load balancer for multiple instances

### API
- Control plane microservice scales independently
- Rate limiting per tenant
- Caching layer (Redis)

### Database
- MongoDB sharding for metadata
- Read replicas for queries
- Index optimization

## Deployment Architecture

### Development
```
Developer Machine
└── npm run dev (localhost:3000)
    └── Connects to dev API
```

### Production (Option 1: Vercel)
```
Git Push
  ↓
Vercel Auto-Deploy
  ↓
Edge Network (CDN)
  ↓
Users worldwide
```

### Production (Option 2: Docker)
```
Docker Build
  ↓
Container Registry (ECR/Docker Hub)
  ↓
Kubernetes/ECS
  ↓
Load Balancer
  ↓
Users
```

### Production (Option 3: Traditional)
```
npm run build
  ↓
Node.js Server (PM2)
  ↓
Nginx Reverse Proxy
  ↓
Users
```

## Monitoring & Observability

### Application Metrics
- Page load times
- API response times
- Error rates
- User actions

### Tools (Recommended)
- **Logging**: Winston, Pino
- **Errors**: Sentry, Rollbar
- **Analytics**: Google Analytics, Mixpanel
- **APM**: New Relic, Datadog
- **Uptime**: Pingdom, UptimeRobot

## Technology Choices Rationale

### Why Next.js?
- File-based routing (easy to understand)
- Server-side rendering capable (future feature)
- Built-in optimization (images, code splitting)
- Large ecosystem and community

### Why LeafyGreen?
- Official MongoDB design system
- Consistent with MongoDB Cloud UI
- Well-documented components
- TypeScript support

### Why TypeScript?
- Type safety (catch errors at compile-time)
- Better IDE support
- Self-documenting code
- Refactoring confidence

### Why No State Management Library?
- Application is simple enough
- Pages are independent
- Avoids complexity
- Can add Redux/Zustand later if needed

### Why Native Fetch?
- No external dependencies
- Modern browsers support it
- Good enough for REST APIs
- Can switch to Axios if needed

## Future Architecture Considerations

### Authentication Layer
```
User Login
  ↓
OAuth/OIDC Provider
  ↓
JWT Token
  ↓
Stored in httpOnly cookie
  ↓
Sent with API requests
```

### WebSocket for Real-Time Updates
```
Deployment Status Change
  ↓
Kubernetes Watch Event
  ↓
FastAPI → WebSocket Server
  ↓
UI receives push notification
  ↓
Auto-update without polling
```

### GraphQL API (Alternative)
```
Component needs data
  ↓
GraphQL query (only fields needed)
  ↓
FastAPI + Graphene
  ↓
Single endpoint, flexible queries
```

### Micro-Frontends
```
Tenants Module → Separate app
Deployments Module → Separate app
Monitoring Module → Separate app
  ↓
All integrated in shell app
```

---

**Version**: 0.1.0
**Last Updated**: 2026-02-09
