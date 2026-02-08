# AtlasForge UI - User Interface Guide

## Visual Overview

This guide describes what each page looks like and how to use it.

## Color Scheme (MongoDB LeafyGreen)

- **Primary Green**: `#00684A` - Running states, success
- **Blue**: `#007BC7` - Provisioning/Scaling states
- **Red**: `#CE1126` - Error states
- **Gray**: `#89979B` - Stopped/Disabled states
- **Background**: `#F9FBFA` - Main background
- **Text Dark**: `#001E2B` - Headers
- **Text Medium**: `#5C6C75` - Body text

---

## Page 1: Tenants Overview (Home)

**URL**: `http://localhost:3000/`

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│  [🍃 AtlasForge]          Tenants                           │
│  • Tenants                Manage your MongoDB tenants       │
│  • About                                                    │
│                           [🔄 Refresh] [Onboard Tenant]     │
│  [DEV]                    ─────────────────────────────     │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Acme Corp   │  │  Globex Ind  │  │  Demo Tenant │    │
│  │  t-acme      │  │  t-globex    │  │  t-demo      │    │
│  │  [dev]       │  │  [prod]      │  │  [staging]   │    │
│  │              │  │              │  │              │    │
│  │ Deployments: │  │ Deployments: │  │ Deployments: │    │
│  │     5        │  │     12       │  │     3        │    │
│  │ Running: 4   │  │ Running: 11  │  │ Running: 2   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**Features**:
- Left sidebar: Navigation (Tenants, About), Environment badge at bottom
- Header: Page title, subtitle, Refresh button, "Onboard Tenant" button
- Main area: Grid of tenant cards (3 columns, responsive)
- Each card shows:
  - Display name (large)
  - Tenant ID (small, gray)
  - Environment badge
  - Deployment count
  - Running count (green) if > 0
  - Error count (red) if > 0
- Click card → Navigate to tenant details

**Empty State**:
```
┌─────────────────────────────────────────────────┐
│  No tenants found.                              │
│  Create your first tenant to get started.      │
│                                                 │
│         [Onboard Tenant]                        │
└─────────────────────────────────────────────────┘
```

---

## Modal: Create Tenant

**Triggered by**: "Onboard Tenant" button

**Form Fields**:
```
┌──────────────────────────────────────────────────┐
│  Onboard New Tenant                    [×]       │
├──────────────────────────────────────────────────┤
│                                                  │
│  Tenant ID *                                     │
│  [_____________]                                 │
│  Lowercase letters, numbers, and hyphens only    │
│                                                  │
│  Display Name                                    │
│  [_____________]                                 │
│  Human-readable name for the tenant              │
│                                                  │
│  Environment                                     │
│  [_____________]                                 │
│  e.g., dev, staging, prod                        │
│                                                  │
│  Notes                                           │
│  [_____________]                                 │
│  Optional notes about this tenant                │
│                                                  │
│         [Cancel]  [Create Tenant]                │
└──────────────────────────────────────────────────┘
```

**Validation**:
- Tenant ID required
- Must match pattern: `^[a-z0-9-]+$`
- Shows error toast if invalid

---

## Page 2: Tenant Details

**URL**: `http://localhost:3000/tenants/t-acme`

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│  [← Back to Tenants]                                        │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Acme Corporation                                   │   │
│  │  Tenant ID: t-acme                                  │   │
│  │  Namespace: mdb-tenant-t-acme                       │   │
│  │  [dev]                                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Deployments            [🔄 Refresh] [Create Deployment]    │
│  ─────────────────────────────────────────────────────     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ID       │ Name    │ Type   │ Ver  │ Mem │ Status │ │  │
│  ├─────────────────────────────────────────────────────┤   │
│  │ rs-orders│ Orders  │ RepSet │ 8.0.3│ 3   │🟢 Run  │▶│  │
│  │ rs-custom│ Cust DB │ RepSet │ 8.0.3│ 3   │🟢 Run  │▶│  │
│  │ st-cache │ Cache   │ Stand. │ 7.0  │ -   │⚪ Stop │▶│  │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Features**:
- Back button (← Back to Tenants)
- Tenant info card (display name, ID, namespace, environment)
- Deployments section header with Refresh and Create buttons
- Table of deployments:
  - Deployment ID
  - Display Name
  - Type (ReplicaSet, Standalone, ShardedCluster)
  - MongoDB Version
  - Members (for ReplicaSet)
  - Status badge (color-coded)
  - "View Details" button
- Status colors:
  - 🟢 Green: Running
  - 🔵 Blue: Provisioning/Scaling
  - ⚪ Gray: Stopped
  - 🔴 Red: Error

---

## Modal: Create Deployment

**Triggered by**: "Create Deployment" button on Tenant Details

**Form**:
```
┌──────────────────────────────────────────────────┐
│  Create MongoDB Deployment           [×]         │
├──────────────────────────────────────────────────┤
│                                                  │
│  Deployment ID *                                 │
│  [_____________]                                 │
│  Unique identifier (e.g., rs-orders)             │
│                                                  │
│  Deployment Type *                               │
│  ◉ Standalone   ○ Replica Set                    │
│  ○ Sharded Cluster (Coming Soon)                 │
│                                                  │
│  MongoDB Version *                               │
│  [8.0.3______]                                   │
│  e.g., 8.0.3, 7.0.14, 8.0.17-ent                 │
│                                                  │
│  Number of Members                               │
│  [3__________]                                   │
│  Recommended: odd number >= 3                    │
│                                                  │
│  Display Name                                    │
│  [_____________]                                 │
│                                                  │
│  Environment                                     │
│  [_____________]                                 │
│                                                  │
│         [Cancel]  [Create Deployment]            │
└──────────────────────────────────────────────────┘
```

**Validation**:
- Shows error if members < 3
- Shows warning banner if members is even number
- Submit button disabled if invalid

---

## Page 3: Deployment Details

**URL**: `http://localhost:3000/tenants/t-acme/deployments/rs-orders`

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│  [← Back to Tenant]                                         │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Orders Database                        🟢 Running  │   │
│  │  Deployment ID: rs-orders               (3/3)       │   │
│  │  Tenant: t-acme                         Updated:    │   │
│  │                                         2 min ago   │   │
│  │  Type: ReplicaSet   Version: 8.0.3     [🔄]        │   │
│  │  Members: 3         Environment: prod              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [Overview] [Monitoring] [Backup]                           │
│  ─────────────────────────────────────────────────────     │
│                                                             │
│  Lifecycle Controls                                         │
│  [Scale Members] [Upgrade Version] [Restart] [Shutdown]     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Connection Information                             │   │
│  │                                                     │   │
│  │  MongoDB URI                              [Copy]   │   │
│  │  mongodb://rs-orders-0.svc:27017,...              │   │
│  │                                                     │   │
│  │  mongosh Example                          [Copy]   │   │
│  │  mongosh "mongodb://rs-orders-0..."               │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Tabs**:

### Overview Tab (Default)
- Lifecycle control buttons
- Connection Information card
  - MongoDB URI with copy button
  - mongosh example with copy button

### Monitoring Tab
```
┌─────────────────────────────────────────────────────┐
│  Prometheus Monitoring              [Toggle: ON]    │
│                                                     │
│  [Enabled ✓]                                        │
│                                                     │
│  Metrics Endpoint                                   │
│  ec2-host:9216/metrics                              │
│                                                     │
│  Prometheus Configuration                           │
│  ┌───────────────────────────────────────────────┐ │
│  │ - job_name: 'rs-orders'                       │ │
│  │   static_configs:                             │ │
│  │     - targets: ['ec2-host:9216']              │ │
│  │   metrics_path: '/metrics'                    │ │
│  └───────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Backup Tab
```
┌─────────────────────────────────────────────────────┐
│  Backup Configuration                               │
│                                                     │
│  Backup enrollment is managed via CR spec.          │
│  Check your deployment's CR for backup config.      │
│                                                     │
│  [Backup Status: Check CR]                          │
└─────────────────────────────────────────────────────┘
```

---

## Modal: Scale Deployment

**Triggered by**: "Scale Members" button

```
┌──────────────────────────────────────────────────┐
│  Scale Deployment                    [×]         │
├──────────────────────────────────────────────────┤
│                                                  │
│  ℹ️ Current members: 3                           │
│                                                  │
│  New Member Count *                              │
│  [5__________]                                   │
│  Recommended: odd number >= 3                    │
│                                                  │
│  ⚠️  Even number of members can cause voting     │
│     issues in split-brain scenarios              │
│                                                  │
│         [Cancel]  [Scale Deployment]             │
└──────────────────────────────────────────────────┘
```

---

## Modal: Upgrade Version

**Triggered by**: "Upgrade Version" button

```
┌──────────────────────────────────────────────────┐
│  Upgrade MongoDB Version             [×]         │
├──────────────────────────────────────────────────┤
│                                                  │
│  ℹ️ Current version: 8.0.3                       │
│                                                  │
│  New MongoDB Version *                           │
│  [8.0.17-ent_]                                   │
│  Must be higher than current version             │
│                                                  │
│         [Cancel]  [Upgrade Version]              │
└──────────────────────────────────────────────────┘
```

**With Downgrade Attempt**:
```
┌──────────────────────────────────────────────────┐
│  Upgrade MongoDB Version             [×]         │
├──────────────────────────────────────────────────┤
│                                                  │
│  ℹ️ Current version: 8.0.3                       │
│                                                  │
│  ⚠️  Downgrade detected! Downgrades not allowed  │
│                                                  │
│  New MongoDB Version *                           │
│  [7.0.14_____]  ❌                               │
│  Downgrade not allowed                           │
│                                                  │
│      [Cancel]  [Upgrade Version] (disabled)      │
└──────────────────────────────────────────────────┘
```

---

## Modal: Confirm Action

**For Shutdown**:
```
┌──────────────────────────────────────────────────┐
│  Shutdown Deployment                 [×]         │
├──────────────────────────────────────────────────┤
│                                                  │
│  Are you sure you want to shutdown this          │
│  deployment? All MongoDB processes will be       │
│  stopped.                                        │
│                                                  │
│         [Cancel]  [Shutdown]                     │
│                   (red button)                   │
└──────────────────────────────────────────────────┘
```

**For Start**:
```
┌──────────────────────────────────────────────────┐
│  Start Deployment                    [×]         │
├──────────────────────────────────────────────────┤
│                                                  │
│  Are you sure you want to start this             │
│  deployment?                                     │
│                                                  │
│         [Cancel]  [Start]                        │
│                   (green button)                 │
└──────────────────────────────────────────────────┘
```

**For Restart**:
```
┌──────────────────────────────────────────────────┐
│  Restart Deployment                  [×]         │
├──────────────────────────────────────────────────┤
│                                                  │
│  Are you sure you want to restart this           │
│  deployment? This will perform a rolling         │
│  restart of all MongoDB processes.               │
│                                                  │
│         [Cancel]  [Restart]                      │
└──────────────────────────────────────────────────┘
```

---

## Toast Notifications

**Success** (Green, top-right):
```
┌────────────────────────────────────┐
│ ✓ Tenant created successfully      │
│   Tenant t-demo has been created   │
│                              [×]   │
└────────────────────────────────────┘
```

**Error** (Red, top-right):
```
┌────────────────────────────────────┐
│ ⚠ Failed to create deployment      │
│   Deployment ID already exists     │
│                              [×]   │
└────────────────────────────────────┘
```

**Warning** (Yellow, top-right):
```
┌────────────────────────────────────┐
│ ⚠ Configuration warning            │
│   Even member count can cause      │
│   voting issues                    │
│                              [×]   │
└────────────────────────────────────┘
```

**Auto-dismiss**: After 5 seconds

---

## Page 4: About

**URL**: `http://localhost:3000/about`

```
┌─────────────────────────────────────────────────────────────┐
│  About AtlasForge UI                                        │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Overview                                           │   │
│  │                                                     │   │
│  │  AtlasForge UI is a MongoDB-themed web interface   │   │
│  │  for managing your MDBaaS control plane...         │   │
│  │                                                     │   │
│  │  Features                                           │   │
│  │  • Tenant management                                │   │
│  │  • Deployment lifecycle                             │   │
│  │  • Real-time monitoring                             │   │
│  │  • Connection management                            │   │
│  │  • Prometheus integration                           │   │
│  │                                                     │   │
│  │  Deployment Types                                   │   │
│  │  [Standalone] [Replica Set] [Sharded Cluster]      │   │
│  │                                                     │   │
│  │  Configuration                                      │   │
│  │  API Base URL: http://ec2-...                      │   │
│  │  Environment: [DEV]                                 │   │
│  │                                                     │   │
│  │  Version 0.1.0                                      │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Responsive Behavior

### Desktop (> 1024px)
- 3-column grid for tenant cards
- Full sidebar visible
- All table columns visible

### Tablet (768px - 1024px)
- 2-column grid for tenant cards
- Sidebar collapsible
- Some table columns hidden

### Mobile (< 768px)
- 1-column layout
- Hamburger menu for sidebar
- Table switches to card view
- Buttons stack vertically

---

## Keyboard Shortcuts (Future Feature)

- `Ctrl/Cmd + K` - Quick search
- `Esc` - Close modal
- `Ctrl/Cmd + R` - Refresh current page
- `Ctrl/Cmd + N` - New tenant/deployment (context-aware)

---

## Accessibility

- All interactive elements keyboard accessible
- ARIA labels on buttons and inputs
- Color contrast meets WCAG AA standards
- Screen reader compatible
- Focus indicators visible

---

## User Flows

### Create First Tenant → Deployment → Connect

1. **Home page** → Click "Onboard Tenant"
2. **Modal** → Fill form → Click "Create Tenant"
3. **Toast** → "Tenant created successfully"
4. **Home page** → Click tenant card
5. **Tenant details** → Click "Create Deployment"
6. **Modal** → Fill form (ReplicaSet, 3 members) → Click "Create"
7. **Toast** → "Deployment created successfully"
8. **Tenant details** → Table shows deployment (status: Provisioning → Running)
9. **Tenant details** → Click "View Details"
10. **Deployment details** → View connection info → Click "Copy" on MongoDB URI
11. **Toast** → "MongoDB URI copied to clipboard"

### Scale Existing Deployment

1. **Deployment details** → Click "Scale Members"
2. **Modal** → Enter new count (e.g., 5) → Click "Scale Deployment"
3. **Toast** → "Scaling initiated"
4. **Deployment details** → Status badge changes to "Scaling (3/5)"
5. **Wait 15 seconds** → Auto-refresh updates status
6. **Deployment details** → Status badge shows "Running (5/5)"

### Upgrade MongoDB Version

1. **Deployment details** → Click "Upgrade Version"
2. **Modal** → Enter new version (e.g., 8.0.17-ent) → Click "Upgrade"
3. **Toast** → "Version upgrade initiated"
4. **Deployment details** → Status changes to "Scaling"
5. **Wait** → Auto-refresh until complete
6. **Deployment details** → Version field shows "8.0.17-ent"

---

This UI guide provides a visual reference for developers and users to understand the AtlasForge UI layout and functionality.
