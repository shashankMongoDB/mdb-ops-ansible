# Prometheus Password Reveal & Rotate Implementation

## Overview

Implemented one-time password reveal + rotate functionality for Prometheus monitoring with improved clipboard copy support. Users can now:
- View Prometheus config with **masked password by default**
- **Reveal password once** (stored as firstViewedAt timestamp)
- **Rotate password** to generate new credentials
- **Reliable copy-to-clipboard** with fallback for older browsers

**Works identically for both Enterprise and Community deployments.**

---

## Backend Implementation

### 1. New K8s Client Helper (`k8s_client.py`)

#### `update_secret_data(namespace, name, key, value)`
```python
def update_secret_data(self, namespace: str, name: str, key: str, value: str) -> None:
    """
    Update a specific key in an existing secret.
    Creates the key if it doesn't exist, updates if it does.
    """
    import base64
    
    try:
        secret = self.core_v1.read_namespaced_secret(name=name, namespace=namespace)
        
        # Encode the new value
        encoded_value = base64.b64encode(value.encode('utf-8')).decode('utf-8')
        
        # Update the secret data
        if secret.data is None:
            secret.data = {}
        secret.data[key] = encoded_value
        
        # Patch the secret
        self.core_v1.replace_namespaced_secret(name=name, namespace=namespace, body=secret)
    except ApiException as e:
        if e.status == 404:
            raise ValueError(f"Secret {name} not found in namespace {namespace}")
        raise
```

---

### 2. Updated Monitoring Service (`monitoring_service.py`)

#### New Utility Functions

**`generate_strong_password(length=20)`**
```python
def generate_strong_password(length: int = 20) -> str:
    """
    Generate a strong random password.
    """
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))
```

#### Updated `get_prometheus_scrape_config()` - Always Masked

**Changed Behavior:**
- **Old**: Returned full password on first view, masked afterwards
- **New**: ALWAYS returns masked password
- **New field**: `canRevealPassword` (true if `firstViewedAt` is null)

```python
def get_prometheus_scrape_config(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Get Prometheus scrape configuration with MASKED password.
    
    Returns:
    - jobName, metricsPath, username, passwordMasked
    - targets, labels, workerNodeIps, nodePort
    - canRevealPassword: true if firstViewedAt is null
    """
    # ... load tenant, deployment, enable prometheus if needed ...
    
    # Read password from secret and ALWAYS mask it
    password_raw = k8s.get_secret_data(namespace, secret_name, secret_key)
    password_masked = mask_password(password_raw)

    # Check if can reveal password
    prometheus_meta = deployment.get("prometheus", {})
    first_viewed_at = prometheus_meta.get("firstViewedAt")
    can_reveal_password = (first_viewed_at is None)

    # ... get service, worker IPs, build targets ...

    return {
        "jobName": job_name,
        "metricsPath": "/metrics",
        "username": username,
        "passwordMasked": password_masked,  # Always masked!
        "targets": targets,
        "labels": labels,
        "workerNodeIps": worker_ips,
        "nodePort": node_port,
        "canRevealPassword": can_reveal_password
    }
```

#### New `reveal_prometheus_password()` - One-Time Reveal

```python
def reveal_prometheus_password(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Reveal the full Prometheus password ONCE.
    
    Only works if firstViewedAt is null.
    After revealing, sets firstViewedAt to now.
    
    Returns: { username, password } with FULL password.
    """
    # ... load tenant, deployment ...

    # Check if already revealed
    prometheus_meta = deployment.get("prometheus", {})
    first_viewed_at = prometheus_meta.get("firstViewedAt")
    
    if first_viewed_at is not None:
        raise ValueError("Password already revealed. Rotate to generate a new one.")

    # ... get CR, read prometheus config ...

    # Read full password from secret
    password = k8s.get_secret_data(namespace, secret_name, secret_key)

    # Mark as revealed
    repo.update_deployment(tenant_id, deployment_id, {
        "prometheus.firstViewedAt": datetime.now(timezone.utc).isoformat()
    })

    return {
        "username": username,
        "password": password  # FULL PASSWORD
    }
```

#### New `rotate_prometheus_password()` - Generate New Password

```python
def rotate_prometheus_password(tenant_id: str, deployment_id: str) -> Dict[str, Any]:
    """
    Rotate Prometheus password.
    
    Generates a new random password, updates mongodb-admin-secret in K8s,
    resets firstViewedAt to null, and optionally increments passwordVersion.
    
    Returns success message.
    """
    # ... load tenant, deployment, get CR ...

    # Generate new password
    new_password = generate_strong_password()

    # Update secret in K8s
    k8s.update_secret_data(namespace, secret_name, secret_key, new_password)

    # Reset firstViewedAt and increment version
    prometheus_meta = deployment.get("prometheus", {})
    password_version = prometheus_meta.get("passwordVersion", 0)
    
    repo.update_deployment(tenant_id, deployment_id, {
        "prometheus.firstViewedAt": None,  # Reset!
        "prometheus.passwordVersion": password_version + 1,
        "prometheus.lastRotatedAt": datetime.now(timezone.utc).isoformat()
    })

    return {
        "message": "Password rotated successfully. You can now reveal the new password once.",
        "passwordVersion": password_version + 1
    }
```

---

### 3. Deployment Document Schema (MongoDB)

**Prometheus Subdocument:**
```json
{
  "_id": "rs-orders",
  "tenantId": "t-acme",
  "deploymentId": "rs-orders",
  "prometheusEnabled": true,
  "prometheus": {
    "firstViewedAt": "2026-02-11T10:30:00Z" | null,
    "passwordVersion": 2,
    "lastRotatedAt": "2026-02-11T09:00:00Z"
  }
}
```

**Fields:**
- `firstViewedAt`: ISO timestamp when password was first revealed, or null if not yet revealed
- `passwordVersion`: Incremented on each rotation (starts at 0)
- `lastRotatedAt`: ISO timestamp of last password rotation

---

### 4. New FastAPI Endpoints (`main.py`)

#### A) GET `/tenants/{tenantId}/deployments/{deploymentId}/monitoring/prometheus/config`

**Updated to return masked password:**
```python
@app.get(
    "/tenants/{tenantId}/deployments/{deploymentId}/monitoring/prometheus/config",
    response_model=PrometheusScrapeConfigResponse
)
def get_prometheus_scrape_config(...):
    """
    Get Prometheus scrape configuration with MASKED password.
    
    Returns:
    - passwordMasked (always masked)
    - canRevealPassword (true if firstViewedAt is null)
    """
```

**Response Example:**
```json
{
  "jobName": "mongo-rs-orders",
  "metricsPath": "/metrics",
  "username": "prometheus-user",
  "passwordMasked": "***************123",
  "targets": ["172.31.23.201:31586"],
  "labels": {"app": "mongo-rs-orders"},
  "workerNodeIps": ["172.31.23.201", "172.31.22.150"],
  "nodePort": 31586,
  "canRevealPassword": true
}
```

#### B) POST `/tenants/{tenantId}/deployments/{deploymentId}/monitoring/prometheus/reveal`

```python
@app.post(
    "/tenants/{tenantId}/deployments/{deploymentId}/monitoring/prometheus/reveal",
    response_model=PrometheusPasswordRevealResponse
)
def reveal_prometheus_password(...):
    """
    Reveal the full Prometheus password ONCE.
    
    Only works if firstViewedAt is null.
    After revealing, cannot reveal again until rotated.
    """
```

**Success Response (200):**
```json
{
  "username": "prometheus-user",
  "password": "SuperSecretPass123"
}
```

**Error Response (400) - Already Revealed:**
```json
{
  "detail": "Password already revealed. Rotate to generate a new one."
}
```

#### C) POST `/tenants/{tenantId}/deployments/{deploymentId}/monitoring/prometheus/rotate`

```python
@app.post(
    "/tenants/{tenantId}/deployments/{deploymentId}/monitoring/prometheus/rotate",
    response_model=PrometheusPasswordRotateResponse
)
def rotate_prometheus_password(...):
    """
    Rotate the Prometheus password.
    
    Generates new password, updates K8s secret, resets firstViewedAt to null.
    """
```

**Success Response (200):**
```json
{
  "message": "Password rotated successfully. You can now reveal the new password once.",
  "passwordVersion": 2
}
```

---

### 5. New DTOs (`dto.py`)

```python
class PrometheusScrapeConfigResponse(BaseModel):
    jobName: str
    metricsPath: str
    username: str
    passwordMasked: str  # Changed from "password"
    targets: list[str]
    labels: dict
    workerNodeIps: list[str]
    nodePort: int
    canRevealPassword: bool  # Changed from "isFirstView"


class PrometheusPasswordRevealResponse(BaseModel):
    username: str
    password: str  # Full password


class PrometheusPasswordRotateResponse(BaseModel):
    message: str
    passwordVersion: int
```

---

## UI Implementation

### 1. Updated Types (`types.ts`)

```typescript
export interface PrometheusScrapeConfig {
  jobName: string;
  metricsPath: string;
  username: string;
  passwordMasked: string;  // Changed
  targets: string[];
  labels: Record<string, string>;
  workerNodeIps: string[];
  nodePort: number;
  canRevealPassword: boolean;  // Changed
}

export interface PrometheusPasswordReveal {
  username: string;
  password: string;
}

export interface PrometheusPasswordRotate {
  message: string;
  passwordVersion: number;
}
```

---

### 2. Updated API Client (`api.ts`)

```typescript
async getPrometheusScrapeConfig(tenantId: string, deploymentId: string): Promise<PrometheusScrapeConfig> {
  const response = await api.get<PrometheusScrapeConfig>(
    `/tenants/${tenantId}/deployments/${deploymentId}/monitoring/prometheus/config`
  );
  return response.data;
}

async revealPrometheusPassword(tenantId: string, deploymentId: string): Promise<PrometheusPasswordReveal> {
  const response = await api.post<PrometheusPasswordReveal>(
    `/tenants/${tenantId}/deployments/${deploymentId}/monitoring/prometheus/reveal`
  );
  return response.data;
}

async rotatePrometheusPassword(tenantId: string, deploymentId: string): Promise<PrometheusPasswordRotate> {
  const response = await api.post<PrometheusPasswordRotate>(
    `/tenants/${tenantId}/deployments/${deploymentId}/monitoring/prometheus/rotate`
  );
  return response.data;
}
```

---

### 3. Completely Rewritten PrometheusCard Component

**Key Features:**
1. **Shows masked password by default**
2. **"Reveal Password Once" button** (only if `canRevealPassword: true`)
3. **"Rotate Password" button** (always available)
4. **Revealed password display** (readonly input with copy button)
5. **Fixed copy-to-clipboard** with fallback
6. **Warning messages** for revealed password
7. **Confirmation modal** for rotate action

**Component Structure:**

```tsx
export function PrometheusCard({ tenantId, deploymentId }: PrometheusCardProps) {
  const [config, setConfig] = useState<PrometheusScrapeConfig | null>(null);
  const [revealedPassword, setRevealedPassword] = useState<string | null>(null);
  const [revealing, setRevealing] = useState(false);
  const [rotating, setRotating] = useState(false);
  const [showRotateConfirm, setShowRotateConfirm] = useState(false);

  // Load config on mount
  const loadConfig = async () => {
    const data = await deploymentsApi.getPrometheusScrapeConfig(tenantId, deploymentId);
    setConfig(data);
  };

  // Build YAML with provided password (masked or revealed)
  const buildYamlConfig = (password: string) => {
    return `job_name: "${config.jobName}"
metrics_path: ${config.metricsPath}
basic_auth:
  username: ${config.username}
  password: ${password}
static_configs:
  - targets:
${config.targets.map(t => `    - "${t}"`).join('\n')}
    labels:
${Object.entries(config.labels).map(([k, v]) => `        ${k}: "${v}"`).join('\n')}`;
  };

  // Fixed copy with fallback
  const handleCopy = async () => {
    const password = revealedPassword || config.passwordMasked;
    const yamlConfig = buildYamlConfig(password);
    
    try {
      // Try modern clipboard API first
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(yamlConfig);
        showSuccess('Copied!', 'Configuration copied to clipboard');
      } else {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = yamlConfig;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        const successful = document.execCommand('copy');
        document.body.removeChild(textarea);
        
        if (successful) {
          showSuccess('Copied!', 'Configuration copied to clipboard');
        } else {
          throw new Error('Copy command failed');
        }
      }
    } catch (err) {
      showError('Failed to copy', 'Could not copy to clipboard. Please select and copy manually.');
    }
  };

  // Reveal password once
  const handleReveal = async () => {
    const result = await deploymentsApi.revealPrometheusPassword(tenantId, deploymentId);
    setRevealedPassword(result.password);
    showWarning('Password Revealed', 'Copy and save now. Won\'t be shown again until rotated.');
    await loadConfig(); // Reload to update canRevealPassword flag
  };

  // Rotate password
  const handleRotate = async () => {
    const result = await deploymentsApi.rotatePrometheusPassword(tenantId, deploymentId);
    showSuccess('Password Rotated', result.message);
    await loadConfig(); // Reload to get new masked password
  };

  const displayPassword = revealedPassword || config.passwordMasked;

  return (
    <div className="card">
      <h3>Prometheus Scrape Configuration</h3>

      {/* Warning if password revealed */}
      {revealedPassword && (
        <div className="bg-yellow-50 border border-yellow-200 p-3">
          ⚠️ Copy and save this password now. You won't see it again.
        </div>
      )}

      {/* Instructions */}
      <div className="bg-blue-50 border p-4">
        <ol>
          <li>Copy the configuration below</li>
          <li>Add it to your prometheus.yml</li>
          <li>Restart your Prometheus server</li>
          <li>Verify target health in Prometheus UI</li>
        </ol>
      </div>

      {/* Worker Node IPs */}
      <div>
        <label>Available Worker Node IPs:</label>
        {config.workerNodeIps.map(ip => <span key={ip}>{ip}</span>)}
        <p>NodePort: {config.nodePort}</p>
      </div>

      {/* Revealed Password Display */}
      {revealedPassword && (
        <div>
          <label>Full Password (copy now):</label>
          <input type="text" value={revealedPassword} readOnly />
          <button onClick={() => navigator.clipboard.writeText(revealedPassword)}>
            Copy
          </button>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        {config.canRevealPassword && !revealedPassword && (
          <button onClick={handleReveal} disabled={revealing}>
            Reveal Password Once
          </button>
        )}
        <button onClick={() => setShowRotateConfirm(true)} disabled={rotating}>
          Rotate Password
        </button>
      </div>

      {/* YAML Configuration */}
      <div>
        <button onClick={handleCopy}>Copy Config</button>
        <pre>{buildYamlConfig(displayPassword)}</pre>
      </div>

      {/* Footer Note */}
      <p>After updating prometheus.yml, restart your Prometheus server and verify target health.</p>
    </div>
  );
}
```

---

## User Experience Flow

### Initial Load

**User opens Prometheus tab:**
1. UI calls `GET /.../ prometheus/config`
2. Backend returns:
   - `passwordMasked: "***************123"`
   - `canRevealPassword: true`
3. UI shows:
   - YAML with masked password
   - "Reveal Password Once" button (enabled)
   - "Rotate Password" button (enabled)

---

### Revealing Password (First Time)

**User clicks "Reveal Password Once":**
1. UI calls `POST /.../prometheus/reveal`
2. Backend:
   - Checks `firstViewedAt` (null → OK)
   - Reads full password from `mongodb-admin-secret`
   - Sets `firstViewedAt` to now
   - Returns full password
3. UI:
   - Shows yellow warning: "Copy and save now"
   - Displays password in readonly input
   - Updates YAML with full password
   - Button changes to disabled

**User clicks "Reveal Password Once" again:**
1. UI calls `POST /.../prometheus/reveal`
2. Backend returns `400: "Password already revealed. Rotate to generate a new one."`
3. UI shows error toast

---

### Rotating Password

**User clicks "Rotate Password":**
1. UI shows confirmation modal
2. User confirms
3. UI calls `POST /.../prometheus/rotate`
4. Backend:
   - Generates new password: `generate_strong_password()`
   - Updates `mongodb-admin-secret` in K8s
   - Sets `firstViewedAt = null`
   - Increments `passwordVersion`
5. UI:
   - Shows success: "Password rotated successfully"
   - Reloads config
   - "Reveal Password Once" button enabled again
   - YAML shows new masked password

---

### Copying Configuration

**User clicks "Copy Config":**
1. UI tries modern clipboard API:
   ```typescript
   await navigator.clipboard.writeText(yamlConfig);
   ```
2. If fails, fallback to legacy method:
   ```typescript
   const textarea = document.createElement('textarea');
   textarea.value = yamlConfig;
   document.body.appendChild(textarea);
   textarea.select();
   document.execCommand('copy');
   document.body.removeChild(textarea);
   ```
3. Success toast or error toast

---

## Security Considerations

### Password Handling

**1. One-Time Reveal**
- Password shown in full only once
- `firstViewedAt` timestamp prevents re-reveal
- User warned to copy and save immediately

**2. No Logging**
```python
# NEVER log passwords
# ❌ logger.info(f"Password: {password}")
# ✅ logger.info("Password retrieved from secret")
```

**3. Masked by Default**
- GET /config always returns masked password
- Reveal requires explicit POST call
- YAML displays masked password until revealed

**4. Rotation**
- Generates cryptographically strong password
- Updates K8s secret atomically
- Resets reveal flag for new password

---

## Enterprise vs Community Support

**No Differences in User Experience:**

| Feature | Enterprise | Community |
|---------|-----------|-----------|
| **GET /config** | ✅ Masked password | ✅ Masked password |
| **POST /reveal** | ✅ One-time reveal | ✅ One-time reveal |
| **POST /rotate** | ✅ Generate new password | ✅ Generate new password |
| **Secret Updated** | `mongodb-admin-secret` | `mongodb-admin-secret` |
| **UI Display** | Identical | Identical |

**Backend Plan Detection:**
```python
plan = tenant.get("plan", "enterprise")

if plan == "community":
    cr = k8s.get_mongodb_community_cr(namespace, deployment_id)
else:
    cr = k8s.get_mongodb_enterprise_cr(namespace, deployment_id)
```

---

## Postman Collection Updates

### New Requests Added

**1. Reveal Prometheus Password (Enterprise)**
```
POST {{baseUrl}}/tenants/t-acme/deployments/rs-orders/monitoring/prometheus/reveal
```
Response:
```json
{
  "username": "prometheus-user",
  "password": "SuperSecretPass123"
}
```

**2. Reveal Prometheus Password (Community)**
```
POST {{baseUrl}}/tenants/t-initech/deployments/rs-test/monitoring/prometheus/reveal
```

**3. Rotate Prometheus Password (Enterprise)**
```
POST {{baseUrl}}/tenants/t-acme/deployments/rs-orders/monitoring/prometheus/rotate
```
Response:
```json
{
  "message": "Password rotated successfully. You can now reveal the new password once.",
  "passwordVersion": 2
}
```

**4. Rotate Prometheus Password (Community)**
```
POST {{baseUrl}}/tenants/t-initech/deployments/rs-test/monitoring/prometheus/rotate
```

### Updated Responses

**GET /config responses changed:**
- `password` → `passwordMasked`
- `isFirstView` → `canRevealPassword`

---

## Testing Checklist

### Backend API

```bash
# 1. Get config (masked password)
curl GET /tenants/t-acme/deployments/rs-orders/monitoring/prometheus/config
# Expected: passwordMasked: "****ABCD", canRevealPassword: true

# 2. Reveal password (first time)
curl -X POST /tenants/t-acme/deployments/rs-orders/monitoring/prometheus/reveal
# Expected: 200, full password

# 3. Reveal password (second time)
curl -X POST /tenants/t-acme/deployments/rs-orders/monitoring/prometheus/reveal
# Expected: 400, "Password already revealed"

# 4. Get config again
curl GET /tenants/t-acme/deployments/rs-orders/monitoring/prometheus/config
# Expected: passwordMasked: "****ABCD", canRevealPassword: false

# 5. Rotate password
curl -X POST /tenants/t-acme/deployments/rs-orders/monitoring/prometheus/rotate
# Expected: 200, passwordVersion: 2

# 6. Get config after rotate
curl GET /tenants/t-acme/deployments/rs-orders/monitoring/prometheus/config
# Expected: new masked password, canRevealPassword: true
```

### UI Testing

**Enterprise Deployment:**
1. Open Prometheus tab
2. Verify masked password shown
3. Verify "Reveal Password Once" button visible
4. Click reveal → see full password + warning
5. Verify button becomes disabled
6. Click "Copy Config" → verify clipboard
7. Refresh page → verify password still masked
8. Click "Rotate Password" → confirm
9. Verify success message
10. Verify "Reveal Password Once" enabled again

**Community Deployment:**
1. Repeat all steps above
2. Verify identical behavior

**Clipboard Testing:**
1. Modern browser (Chrome/Firefox) → navigator.clipboard.writeText
2. Older browser → document.execCommand fallback
3. Copy full config with revealed password
4. Copy config with masked password

---

## Files Modified/Created

### Backend
1. ✅ `app/services/k8s_client.py`
   - Added `update_secret_data()`

2. ✅ `app/services/monitoring_service.py`
   - Added `generate_strong_password()`
   - Updated `get_prometheus_scrape_config()` (always masked)
   - Added `reveal_prometheus_password()`
   - Added `rotate_prometheus_password()`

3. ✅ `app/models/dto.py`
   - Updated `PrometheusScrapeConfigResponse`
   - Added `PrometheusPasswordRevealResponse`
   - Added `PrometheusPasswordRotateResponse`

4. ✅ `app/main.py`
   - Updated GET `/monitoring/prometheus/config`
   - Added POST `/monitoring/prometheus/reveal`
   - Added POST `/monitoring/prometheus/rotate`

### Frontend
1. ✅ `src/lib/types.ts`
   - Updated `PrometheusScrapeConfig`
   - Added `PrometheusPasswordReveal`
   - Added `PrometheusPasswordRotate`

2. ✅ `src/lib/api.ts`
   - Added `revealPrometheusPassword()`
   - Added `rotatePrometheusPassword()`

3. ✅ `src/components/PrometheusCard.tsx`
   - Completely rewritten with reveal/rotate
   - Fixed copy-to-clipboard with fallback
   - Added password display and warnings

### Documentation
1. ✅ `MongoDB_Control_Plane.postman_collection.json`
   - Added 4 new requests (reveal + rotate for both plans)
   - Updated GET /config response examples

---

## Summary

✅ **Password always masked** in GET /config endpoint  
✅ **One-time reveal** with POST /reveal (sets firstViewedAt)  
✅ **Password rotation** with POST /rotate (resets firstViewedAt)  
✅ **Fixed clipboard copy** with modern API + fallback  
✅ **Warning messages** for password reveal  
✅ **Confirmation modal** for rotation  
✅ **Password versioning** (tracks rotation count)  
✅ **Works identically** for Enterprise and Community  
✅ **No plaintext logging** of passwords  
✅ **Secure K8s secret updates**  

**Users can now safely manage Prometheus passwords with one-time reveal and rotation!** 🔐🚀
