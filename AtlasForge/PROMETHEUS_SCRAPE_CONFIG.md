# Prometheus Scrape Configuration Feature

## Overview

Extended the MDBaaS control plane to provide **ready-to-use Prometheus scrape configuration** for MongoDB deployments. Users can now:
- Get a complete `prometheus.yml` scrape config snippet
- View available worker node IPs for targeting
- Copy credentials (full password shown only once)
- See clear instructions for setting up Prometheus monitoring

**Works for both Enterprise (`MongoDB`) and Community (`MongoDBCommunity`) deployments.**

---

## Backend Implementation

### 1. New K8s Client Helpers (`k8s_client.py`)

#### `list_worker_node_ips()` → `List[str]`
```python
def list_worker_node_ips(self) -> List[str]:
    """
    List all worker node IPs (excluding control-plane nodes).
    Returns list of InternalIP addresses from worker nodes.
    """
    nodes = self.core_v1.list_node()
    worker_ips = []
    
    for node in nodes.items:
        # Check if node has control-plane taint
        is_control_plane = False
        if node.spec.taints:
            for taint in node.spec.taints:
                if taint.key in ["node-role.kubernetes.io/control-plane", 
                                "node-role.kubernetes.io/master"]:
                    is_control_plane = True
                    break
        
        # Skip control-plane nodes
        if is_control_plane:
            continue
        
        # Get InternalIP from node addresses
        if node.status and node.status.addresses:
            for addr in node.status.addresses:
                if addr.type == "InternalIP":
                    worker_ips.append(addr.address)
                    break
    
    return worker_ips
```

#### `get_secret_data(namespace, name, key)` → `Optional[str]`
```python
def get_secret_data(self, namespace: str, name: str, key: str = "password") -> Optional[str]:
    """
    Read a secret and return decoded value for a specific key.
    Returns None if secret or key not found.
    """
    import base64
    
    secret = self.core_v1.read_namespaced_secret(name=name, namespace=namespace)
    if secret.data and key in secret.data:
        # Decode base64 data
        return base64.b64decode(secret.data[key]).decode('utf-8')
    return None
```

---

### 2. New Monitoring Service Function (`monitoring_service.py`)

#### `get_prometheus_scrape_config(tenant_id, deployment_id)` → `Dict[str, Any]`

**Key Features:**
1. **Auto-enable Prometheus** if not already enabled
2. **Plan-aware CR access** (Enterprise vs Community)
3. **Password masking** after first view
4. **Worker node discovery** for scrape targets
5. **Ready-to-use YAML** configuration

**Implementation:**

```python
def mask_password(pw: str) -> str:
    """Mask password showing only last 4 characters."""
    if not pw or len(pw) <= 4:
        return "****"
    return "*" * (len(pw) - 4) + pw[-4:]


def get_prometheus_scrape_config(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Get ready-to-use Prometheus scrape configuration.
    
    - Password shown in full only on first view (prometheus.firstViewedAt == null)
    - Subsequent views show masked password
    - Automatically enables Prometheus if disabled
    - Works for both Enterprise and Community deployments
    """
    repo = get_repo()
    k8s = get_k8s_client()

    tenant = repo.get_tenant(tenant_id)
    deployment = repo.get_deployment(tenant_id, deployment_id)
    
    namespace = tenant["namespace"]
    plan = tenant.get("plan", "enterprise")

    # Auto-enable Prometheus if not already enabled
    prometheus_enabled = deployment.get("prometheusEnabled", False)
    if not prometheus_enabled:
        # Get CR based on plan
        if plan == "community":
            cr = k8s.get_mongodb_community_cr(namespace, deployment_id)
        else:
            cr = k8s.get_mongodb_enterprise_cr(namespace, deployment_id)
        
        # Check if prometheus configured in CR
        cr_has_prometheus = cr.get("spec", {}).get("prometheus") is not None
        
        if not cr_has_prometheus:
            # Patch CR to enable prometheus
            patch = {
                "spec": {
                    "prometheus": {
                        "username": "prometheus-user",
                        "passwordSecretRef": {"name": "mongodb-admin-secret"}
                    }
                }
            }
            
            if plan == "community":
                k8s.patch_mongodb_community_cr(namespace, deployment_id, patch)
            else:
                k8s.patch_mongodb_enterprise_cr(namespace, deployment_id, patch)

            k8s.ensure_metrics_service(namespace, deployment_id, {"app": f"{deployment_id}-svc"})
            repo.update_deployment(tenant_id, deployment_id, {"prometheusEnabled": True})

    # Read prometheus config from CR
    prometheus_spec = cr.get("spec", {}).get("prometheus", {})
    username = prometheus_spec.get("username", "prometheus-user")
    password_secret_ref = prometheus_spec.get("passwordSecretRef", {})
    secret_name = password_secret_ref.get("name", "mongodb-admin-secret")
    secret_key = password_secret_ref.get("key", "password")

    # Read password from secret
    password_raw = k8s.get_secret_data(namespace, secret_name, secret_key)

    # Check if first view
    prometheus_meta = deployment.get("prometheus", {})
    first_viewed_at = prometheus_meta.get("firstViewedAt")
    
    if first_viewed_at is None:
        # First view - show full password
        password = password_raw
        repo.update_deployment(tenant_id, deployment_id, {
            "prometheus.firstViewedAt": datetime.now(timezone.utc).isoformat()
        })
        is_first_view = True
    else:
        # Subsequent view - mask password
        password = mask_password(password_raw)
        is_first_view = False

    # Get metrics service and NodePort
    service_name = f"{deployment_id}-metrics"
    svc_info = k8s.get_service(namespace, service_name)
    
    node_port = None
    ports = svc_info.get("ports", [])
    if ports and len(ports) > 0:
        node_port = ports[0].get("nodePort")

    # Get worker node IPs
    worker_ips = k8s.list_worker_node_ips()

    # Build targets (use first worker IP)
    targets = [f"{worker_ips[0]}:{node_port}"]

    # Build job name and labels
    job_name = f"mongo-{deployment_id}"
    labels = {"app": job_name}

    return {
        "jobName": job_name,
        "metricsPath": "/metrics",
        "username": username,
        "password": password,
        "targets": targets,
        "labels": labels,
        "workerNodeIps": worker_ips,
        "nodePort": node_port,
        "isFirstView": is_first_view
    }
```

**Password Masking Logic:**
- **First view**: `prometheus.firstViewedAt` is `null` → show full password, update timestamp
- **Subsequent views**: `prometheus.firstViewedAt` exists → mask password (`****ABCD`)

**Database Update:**
```python
repo.update_deployment(tenant_id, deployment_id, {
    "prometheus.firstViewedAt": "2026-02-10T14:30:00Z"
})
```

---

### 3. New FastAPI Endpoint (`main.py`)

```python
@app.get(
    "/tenants/{tenantId}/deployments/{deploymentId}/monitoring/prometheus/config",
    response_model=PrometheusScrapeConfigResponse
)
def get_prometheus_scrape_config(
    tenantId: str = Path(..., description="Tenant identifier"),
    deploymentId: str = Path(..., description="Deployment identifier")
):
    """
    Get ready-to-use Prometheus scrape configuration for a deployment.
    
    Returns YAML-ready configuration including:
    - Job name and metrics path
    - Basic auth credentials (full password on first view, masked afterwards)
    - Target endpoints (worker-ip:nodePort)
    - List of all worker node IPs
    - Labels for scraped metrics
    
    Automatically enables Prometheus metrics if not already enabled.
    Works for both Enterprise (MongoDB) and Community (MongoDBCommunity) deployments.
    """
    try:
        result = monitoring_service.get_prometheus_scrape_config(
            tenant_id=tenantId,
            deployment_id=deploymentId
        )
        return result
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error getting Prometheus scrape config")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
```

---

### 4. New DTO (`dto.py`)

```python
class PrometheusScrapeConfigResponse(BaseModel):
    jobName: str = Field(..., description="Prometheus job name for this deployment")
    metricsPath: str = Field(..., description="Metrics endpoint path (e.g., /metrics)")
    username: str = Field(..., description="Basic auth username for Prometheus")
    password: str = Field(..., description="Password (full on first view, masked afterwards)")
    targets: list[str] = Field(..., description="List of scrape targets (node-ip:port)")
    labels: dict = Field(..., description="Labels to apply to scraped metrics")
    workerNodeIps: list[str] = Field(..., description="All available worker node IPs")
    nodePort: int = Field(..., description="NodePort for metrics service")
    isFirstView: bool = Field(..., description="True if password is shown in full for the first time")
```

---

### 5. API Response Example

**First View (Full Password):**
```json
{
  "jobName": "mongo-rs-orders",
  "metricsPath": "/metrics",
  "username": "prometheus-user",
  "password": "SuperSecretPass123",
  "targets": ["172.31.23.201:31586"],
  "labels": {"app": "mongo-rs-orders"},
  "workerNodeIps": ["172.31.23.201", "172.31.22.150", "172.31.25.88"],
  "nodePort": 31586,
  "isFirstView": true
}
```

**Subsequent Views (Masked Password):**
```json
{
  "jobName": "mongo-rs-orders",
  "metricsPath": "/metrics",
  "username": "prometheus-user",
  "password": "***************123",
  "targets": ["172.31.23.201:31586"],
  "labels": {"app": "mongo-rs-orders"},
  "workerNodeIps": ["172.31.23.201", "172.31.22.150", "172.31.25.88"],
  "nodePort": 31586,
  "isFirstView": false
}
```

---

## UI Implementation

### 1. New API Client Method (`api.ts`)

```typescript
async getPrometheusScrapeConfig(tenantId: string, deploymentId: string): Promise<PrometheusScrapeConfig> {
  try {
    const response = await api.get<PrometheusScrapeConfig>(
      `/tenants/${tenantId}/deployments/${deploymentId}/monitoring/prometheus/config`
    );
    return response.data;
  } catch (error) {
    return handleError(error);
  }
}
```

---

### 2. New TypeScript Interface (`types.ts`)

```typescript
export interface PrometheusScrapeConfig {
  jobName: string;
  metricsPath: string;
  username: string;
  password: string;
  targets: string[];
  labels: Record<string, string>;
  workerNodeIps: string[];
  nodePort: number;
  isFirstView: boolean;
}
```

---

### 3. Completely Rewritten PrometheusCard Component

**Key Features:**
1. **Auto-loads scrape config** on mount
2. **Builds YAML** dynamically from API response
3. **Copy to clipboard** functionality
4. **First-view password warning**
5. **Clear instructions** for Prometheus setup
6. **Worker node IP display**

**Component Structure:**

```tsx
export function PrometheusCard({ tenantId, deploymentId }: PrometheusCardProps) {
  const [config, setConfig] = useState<PrometheusScrapeConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Load config on mount
  useEffect(() => {
    loadConfig();
  }, [tenantId, deploymentId]);

  const loadConfig = async () => {
    const data = await deploymentsApi.getPrometheusScrapeConfig(tenantId, deploymentId);
    setConfig(data);
  };

  // Build YAML config
  const buildYamlConfig = () => {
    return `job_name: "${config.jobName}"
metrics_path: ${config.metricsPath}
basic_auth:
  username: ${config.username}
  password: ${config.password}
static_configs:
  - targets:
${config.targets.map(t => `    - "${t}"`).join('\n')}
    labels:
${Object.entries(config.labels).map(([k, v]) => `        ${k}: "${v}"`).join('\n')}`;
  };

  // Copy to clipboard
  const handleCopy = async () => {
    await navigator.clipboard.writeText(buildYamlConfig());
    setCopied(true);
    showSuccess('Copied!', 'Configuration copied to clipboard');
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="card">
      <h3>Prometheus Scrape Configuration</h3>

      {/* Password warning for first view */}
      {config.isFirstView && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3">
          <p className="text-sm text-yellow-800 font-medium">
            ⚠️ Password is shown only once in full. Please copy and store it securely.
          </p>
        </div>
      )}

      {/* Instructions */}
      <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
        <h4 className="font-medium text-blue-900 mb-2">Instructions:</h4>
        <ol className="text-sm text-blue-800 space-y-1">
          <li>Copy the configuration below and add it to your prometheus.yml</li>
          <li>You can use any worker node IP with NodePort {config.nodePort}</li>
          <li>After updating prometheus.yml, restart your Prometheus server</li>
          <li>Access your Prometheus UI to verify target health</li>
        </ol>
      </div>

      {/* Worker Node IPs */}
      <div>
        <label>Available Worker Node IPs:</label>
        <div className="flex flex-wrap gap-2">
          {config.workerNodeIps.map(ip => (
            <span key={ip} className="badge badge-gray font-mono">{ip}</span>
          ))}
        </div>
        <p className="text-xs text-gray-500">NodePort: {config.nodePort}</p>
      </div>

      {/* YAML Configuration */}
      <div>
        <div className="flex justify-between items-center">
          <label>Prometheus Configuration:</label>
          <button onClick={handleCopy} className="btn-secondary">
            {copied ? 'Copied!' : 'Copy Config'}
          </button>
        </div>
        <pre className="bg-gray-50 p-4 rounded border font-mono text-xs">
{buildYamlConfig()}
        </pre>
      </div>

      {/* Additional Details */}
      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="text-xs text-gray-500">Job Name</label>
          <p className="text-sm font-mono">{config.jobName}</p>
        </div>
        <div>
          <label className="text-xs text-gray-500">Username</label>
          <p className="text-sm font-mono">{config.username}</p>
        </div>
        <div>
          <label className="text-xs text-gray-500">Metrics Path</label>
          <p className="text-sm font-mono">{config.metricsPath}</p>
        </div>
      </div>
    </div>
  );
}
```

---

## User Experience Flow

### Opening the Prometheus Tab

**User Action:** Navigate to Deployment Details → Click **Monitoring** tab

**What Happens:**
1. UI calls `GET /tenants/{tenantId}/deployments/{deploymentId}/monitoring/prometheus/config`
2. Backend checks if Prometheus enabled:
   - **Not enabled** → Auto-enable (patch CR, create service)
   - **Already enabled** → Continue
3. Backend reads password from `mongodb-admin-secret`
4. Backend checks `deployment.prometheus.firstViewedAt`:
   - **null** → Return full password, update timestamp
   - **exists** → Return masked password
5. Backend discovers worker node IPs
6. Backend returns complete config

**UI Displays:**
- ⚠️ Yellow warning if first view (password shown once)
- 📋 Blue instruction box with 4-step setup guide
- 🖥️ Worker node IP badges with NodePort info
- 📄 Ready-to-paste YAML config with copy button
- ℹ️ Additional details (job name, username, metrics path)

---

### YAML Output Example

**Displayed in UI:**
```yaml
job_name: "mongo-rs-orders"
metrics_path: /metrics
basic_auth:
  username: prometheus-user
  password: SuperSecretPass123
static_configs:
  - targets:
    - "172.31.23.201:31586"
    labels:
        app: "mongo-rs-orders"
```

**User copies this** → pastes into their `prometheus.yml` → restarts Prometheus → verifies in Prometheus UI

---

## Security Considerations

### Password Handling

**1. No Plaintext Logging**
```python
# NEVER log passwords
# ❌ logger.info(f"Password: {password}")
# ✅ logger.info("Password retrieved from secret")
```

**2. One-Time Full Display**
- First view: Full password shown, `firstViewedAt` timestamp saved
- Subsequent views: Masked password (`****ABCD`)
- User warned to copy and store securely

**3. Secret Storage**
- Password stored in K8s Secret: `mongodb-admin-secret`
- Base64 encoded by K8s
- Never stored in control-plane MongoDB

**4. HTTPS Required**
- API should be served over HTTPS in production
- Password transmitted only over encrypted connection

---

## Enterprise vs Community Support

### No Differences in User Experience

**Both plans:**
- ✅ Same API endpoint
- ✅ Same UI component
- ✅ Same YAML output format
- ✅ Same worker node discovery
- ✅ Same password masking logic

**Internal Differences (Backend Only):**

| Feature | Enterprise | Community |
|---------|-----------|-----------|
| **CR Type** | `MongoDB` (mongodb.com) | `MongoDBCommunity` (mongodbcommunity.mongodb.com) |
| **CR Read** | `get_mongodb_enterprise_cr()` | `get_mongodb_community_cr()` |
| **CR Patch** | `patch_mongodb_enterprise_cr()` | `patch_mongodb_community_cr()` |
| **Secret** | `mongodb-admin-secret` | `mongodb-admin-secret` (same) |
| **Service** | `{deploymentId}-metrics` | `{deploymentId}-metrics` (same) |

**Plan Detection:**
```python
plan = tenant.get("plan", "enterprise")

if plan == "community":
    cr = k8s.get_mongodb_community_cr(namespace, deployment_id)
    k8s.patch_mongodb_community_cr(namespace, deployment_id, patch)
else:
    cr = k8s.get_mongodb_enterprise_cr(namespace, deployment_id)
    k8s.patch_mongodb_enterprise_cr(namespace, deployment_id, patch)
```

---

## Testing Checklist

### Backend API

```bash
# Test enterprise deployment
curl -X GET http://localhost:8001/tenants/t-acme/deployments/rs-orders/monitoring/prometheus/config

# Expected first view:
{
  "jobName": "mongo-rs-orders",
  "username": "prometheus-user",
  "password": "full-password-here",
  "isFirstView": true,
  ...
}

# Expected second view:
{
  "password": "***********here",
  "isFirstView": false,
  ...
}

# Test community deployment
curl -X GET http://localhost:8001/tenants/t-initech/deployments/rs-test/monitoring/prometheus/config

# Should work identically
```

### UI Testing

**Enterprise Deployment:**
1. Open deployment details
2. Click **Monitoring** tab
3. Verify yellow warning shown (first view)
4. Verify full password visible
5. Click "Copy Config"
6. Verify success toast
7. Refresh page
8. Verify password now masked
9. Verify warning gone

**Community Deployment:**
1. Repeat same steps as enterprise
2. Verify identical behavior
3. Verify YAML format identical

**Worker Node IPs:**
1. Verify all worker nodes listed
2. Verify control-plane nodes excluded
3. Verify NodePort displayed correctly

---

## Files Modified/Created

### Backend
1. ✅ `app/services/k8s_client.py`
   - Added `list_worker_node_ips()`
   - Added `get_secret_data()`

2. ✅ `app/services/monitoring_service.py`
   - Added `mask_password()`
   - Added `get_prometheus_scrape_config()`

3. ✅ `app/models/dto.py`
   - Added `PrometheusScrapeConfigResponse`

4. ✅ `app/main.py`
   - Added `GET /tenants/{tenantId}/deployments/{deploymentId}/monitoring/prometheus/config`

### Frontend
1. ✅ `src/lib/types.ts`
   - Added `PrometheusScrapeConfig` interface

2. ✅ `src/lib/api.ts`
   - Added `getPrometheusScrapeConfig()`

3. ✅ `src/components/PrometheusCard.tsx`
   - Completely rewritten for scrape config display

---

## Summary

✅ **New endpoint** provides ready-to-use Prometheus scrape config  
✅ **Auto-enables Prometheus** if not already enabled  
✅ **Password shown once** in full, then masked  
✅ **Worker node IPs** discovered automatically  
✅ **YAML config** ready to paste into prometheus.yml  
✅ **Copy to clipboard** with one click  
✅ **Clear instructions** for Prometheus setup  
✅ **Works identically** for Enterprise and Community deployments  
✅ **No plaintext logging** of passwords  
✅ **Secure password handling** with one-time display  

**Users can now quickly set up Prometheus monitoring with zero manual configuration!** 🎉
