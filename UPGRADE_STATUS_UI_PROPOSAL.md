# Upgrade Version - Real-Time Status UI Proposal

## Problem Statement

Currently, when a user clicks **[Upgrade Version]**, the modal closes immediately and the user doesn't see:
- Progress of the upgrade (CR patching)
- Replica-by-replica upgrade status
- Estimated time remaining
- Potential issues during upgrade

**User is left wondering:** "Is it upgrading? How long will it take? What's happening?"

---

## Solution Options

I'll propose **3 different UI approaches** from simplest to most sophisticated:

---

## **Option 1: Modal with Progress Tracking** ⭐ (Recommended)

Keep the user in the modal and show real-time progress until upgrade completes.

### **UI Flow:**

#### **Step 1: User Initiates Upgrade**
```
┌─────────────────────────────────────────────────┐
│  Upgrade MongoDB Version                     ✕  │
├─────────────────────────────────────────────────┤
│                                                 │
│  Current Version: 8.0.18-ent                   │
│                                                 │
│  New Version:                                  │
│  ┌───────────────────────────────────────────┐ │
│  │ 8.0.19-ent (Latest)                    ▼  │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  ⚠ Warning: This will perform a rolling        │
│     upgrade of all replicas. Connections may   │
│     briefly reconnect during the upgrade.      │
│                                                 │
│              [Cancel]  [Upgrade Version]        │
└─────────────────────────────────────────────────┘
```

#### **Step 2: Upgrade In Progress (Modal Stays Open)**
```
┌─────────────────────────────────────────────────┐
│  Upgrading to 8.0.19-ent                     ✕  │
├─────────────────────────────────────────────────┤
│                                                 │
│  ⏳ Upgrade in progress...                     │
│                                                 │
│  ████████████████████░░░░░░░░░░░░░░  60%      │
│                                                 │
│  Current Status: Upgrading Replica 2 of 3      │
│                                                 │
│  Replica Status:                               │
│  ✅ rs-orders-0  │  8.0.19-ent  │  Running     │
│  ✅ rs-orders-1  │  8.0.19-ent  │  Running     │
│  ⏳ rs-orders-2  │  8.0.18-ent  │  Upgrading   │
│                                                 │
│  Estimated time remaining: ~2 minutes          │
│                                                 │
│  ℹ️  The deployment will remain available      │
│     during this rolling upgrade.               │
│                                                 │
│              [Close (runs in background)]       │
└─────────────────────────────────────────────────┘
```

#### **Step 3: Upgrade Complete**
```
┌─────────────────────────────────────────────────┐
│  Upgrade Complete                            ✕  │
├─────────────────────────────────────────────────┤
│                                                 │
│  ✅ Successfully upgraded to 8.0.19-ent        │
│                                                 │
│  ████████████████████████████████████████ 100% │
│                                                 │
│  All Replicas Upgraded:                        │
│  ✅ rs-orders-0  │  8.0.19-ent  │  Running     │
│  ✅ rs-orders-1  │  8.0.19-ent  │  Running     │
│  ✅ rs-orders-2  │  8.0.19-ent  │  Running     │
│                                                 │
│  Upgrade completed in 3m 45s                   │
│                                                 │
│  🎉 Your deployment is now running the latest  │
│     version with all replicas healthy!         │
│                                                 │
│                        [Done]                   │
└─────────────────────────────────────────────────┘
```

### **Technical Implementation:**

```typescript
// UpgradeVersionModal.tsx

const [upgradeState, setUpgradeState] = useState<'idle' | 'upgrading' | 'complete'>('idle');
const [upgradeProgress, setUpgradeProgress] = useState({
  currentReplica: 0,
  totalReplicas: 0,
  percentage: 0,
  replicas: [] as ReplicaStatus[],
  startTime: null as Date | null,
  estimatedTimeRemaining: null as string | null,
});

const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  
  setLoading(true);
  setUpgradeState('upgrading');
  
  try {
    // Start upgrade
    await deploymentsApi.upgradeVersion(tenantId, deploymentId, mongoVersion);
    
    // Start polling for status
    pollUpgradeStatus();
    
  } catch (error: any) {
    showError('Failed to upgrade version', error.detail);
    setUpgradeState('idle');
  } finally {
    setLoading(false);
  }
};

const pollUpgradeStatus = async () => {
  const startTime = new Date();
  const pollInterval = setInterval(async () => {
    try {
      const status = await deploymentsApi.getDeploymentStatus(tenantId, deploymentId);
      
      // Calculate progress
      const readyReplicas = status.readyReplicas || 0;
      const totalReplicas = status.totalReplicas || 3;
      const percentage = Math.round((readyReplicas / totalReplicas) * 100);
      
      setUpgradeProgress({
        currentReplica: readyReplicas,
        totalReplicas: totalReplicas,
        percentage,
        replicas: status.replicas || [],
        startTime,
        estimatedTimeRemaining: calculateETA(startTime, readyReplicas, totalReplicas),
      });
      
      // Check if all replicas upgraded
      const allUpgraded = status.replicas?.every(r => 
        r.version === mongoVersion && r.status === 'Running'
      );
      
      if (allUpgraded) {
        clearInterval(pollInterval);
        setUpgradeState('complete');
      }
      
    } catch (error) {
      console.error('Failed to poll upgrade status:', error);
    }
  }, 5000); // Poll every 5 seconds
  
  // Cleanup after 10 minutes
  setTimeout(() => clearInterval(pollInterval), 600000);
};
```

### **Pros:**
✅ User sees real-time progress  
✅ Clear feedback on what's happening  
✅ Shows replica-by-replica status  
✅ Can close modal and continue in background  
✅ Best user experience  

### **Cons:**
❌ More complex implementation  
❌ Requires polling backend  
❌ Modal stays open longer  

---

## **Option 2: Inline Banner on Deployment Page** 🔄

Close modal immediately, show upgrade banner on deployment detail page.

### **UI Flow:**

#### **Step 1: Click Upgrade**
Modal closes immediately after API call succeeds.

#### **Step 2: Deployment Page Shows Banner**
```
┌─────────────────────────────────────────────────────────────────┐
│  ⏳ Upgrade in Progress: 8.0.18-ent → 8.0.19-ent               │
│                                                                 │
│  ████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░  40%           │
│                                                                 │
│  Status: Upgrading replica 2 of 3 (estimated 3 min remaining)  │
│                                                                 │
│  [View Details ▼]                                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Deployment: rs-orders                              [Refresh]    │
├─────────────────────────────────────────────────────────────────┤
│  Type: ReplicaSet (3 members)                                   │
│  Version: 8.0.18-ent → 8.0.19-ent (Upgrading)                  │
│  ...                                                            │
```

**Expanded view:**
```
┌─────────────────────────────────────────────────────────────────┐
│  ⏳ Upgrade in Progress: 8.0.18-ent → 8.0.19-ent               │
│                                                                 │
│  ████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░  40%           │
│                                                                 │
│  Replica Status:                                               │
│  ┌───────────────┬──────────────┬──────────────────────────┐  │
│  │ Replica       │ Version      │ Status                   │  │
│  ├───────────────┼──────────────┼──────────────────────────┤  │
│  │ rs-orders-0   │ 8.0.19-ent   │ ✅ Running              │  │
│  │ rs-orders-1   │ 8.0.18-ent   │ ⏳ Upgrading (2m left)  │  │
│  │ rs-orders-2   │ 8.0.18-ent   │ ⏸️  Waiting             │  │
│  └───────────────┴──────────────┴──────────────────────────┘  │
│                                                                 │
│  [Hide Details ▲]                                              │
└─────────────────────────────────────────────────────────────────┘
```

### **Technical Implementation:**

```typescript
// DeploymentDetailsPage.tsx

const [upgradeInProgress, setUpgradeInProgress] = useState(false);
const [upgradeInfo, setUpgradeInfo] = useState<UpgradeInfo | null>(null);

useEffect(() => {
  // Check if upgrade in progress
  if (deployment && connectionInfo) {
    const isUpgrading = connectionInfo.replicas?.some(r => 
      r.status === 'Upgrading' || r.version !== deployment.mongoVersion
    );
    setUpgradeInProgress(isUpgrading);
    
    if (isUpgrading) {
      // Calculate upgrade progress
      const upgraded = connectionInfo.replicas.filter(r => 
        r.version === deployment.mongoVersion
      ).length;
      const total = connectionInfo.replicas.length;
      
      setUpgradeInfo({
        fromVersion: connectionInfo.replicas[0].version,
        toVersion: deployment.mongoVersion,
        progress: Math.round((upgraded / total) * 100),
        currentReplica: upgraded,
        totalReplicas: total,
      });
    }
  }
}, [deployment, connectionInfo]);

// In JSX
{upgradeInProgress && upgradeInfo && (
  <div className="mb-6 p-4 bg-blue-50 border-l-4 border-blue-400">
    <div className="flex items-start gap-3">
      <div className="animate-spin h-5 w-5 border-2 border-blue-600 border-t-transparent rounded-full" />
      <div className="flex-1">
        <h3 className="font-medium text-blue-900">
          Upgrade in Progress: {upgradeInfo.fromVersion} → {upgradeInfo.toVersion}
        </h3>
        <div className="mt-2">
          <div className="w-full bg-blue-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-500"
              style={{ width: `${upgradeInfo.progress}%` }}
            />
          </div>
        </div>
        <p className="mt-2 text-sm text-blue-800">
          Upgrading replica {upgradeInfo.currentReplica} of {upgradeInfo.totalReplicas}
        </p>
      </div>
    </div>
  </div>
)}
```

### **Pros:**
✅ Simpler implementation  
✅ User can navigate away  
✅ Non-intrusive  
✅ Uses existing polling mechanism  

### **Cons:**
❌ Less immediate feedback  
❌ User might miss the banner  
❌ Need to stay on deployment page to see progress  

---

## **Option 3: Toast Notifications with Progress** 🔔

Show toast notifications for upgrade milestones.

### **UI Flow:**

#### **Step 1: Upgrade Started**
```
┌────────────────────────────────────────────┐
│  ⏳ Upgrade Started                        │
│  Upgrading to 8.0.19-ent...                │
│  This will take approximately 5 minutes.   │
└────────────────────────────────────────────┘
```

#### **Step 2: Progress Updates (Every 33%)**
```
┌────────────────────────────────────────────┐
│  ⏳ Upgrade Progress: 33%                  │
│  Replica 1 of 3 upgraded                   │
└────────────────────────────────────────────┘
```

```
┌────────────────────────────────────────────┐
│  ⏳ Upgrade Progress: 66%                  │
│  Replica 2 of 3 upgraded                   │
└────────────────────────────────────────────┘
```

#### **Step 3: Completion**
```
┌────────────────────────────────────────────┐
│  ✅ Upgrade Complete!                      │
│  All replicas upgraded to 8.0.19-ent       │
│  Completed in 4m 32s                       │
└────────────────────────────────────────────┘
```

### **Technical Implementation:**

```typescript
// Add to deploymentsApi or create upgradeMonitor service

class UpgradeMonitor {
  private pollInterval: NodeJS.Timeout | null = null;
  
  startMonitoring(
    tenantId: string, 
    deploymentId: string, 
    targetVersion: string,
    onProgress: (progress: UpgradeProgress) => void,
    onComplete: () => void
  ) {
    let lastNotifiedProgress = 0;
    
    this.pollInterval = setInterval(async () => {
      const status = await deploymentsApi.getDeploymentStatus(tenantId, deploymentId);
      
      const upgraded = status.replicas.filter(r => r.version === targetVersion).length;
      const total = status.replicas.length;
      const progress = Math.round((upgraded / total) * 100);
      
      // Notify on 33%, 66%, 100%
      if (progress >= lastNotifiedProgress + 33) {
        lastNotifiedProgress = progress;
        onProgress({
          progress,
          currentReplica: upgraded,
          totalReplicas: total,
        });
      }
      
      if (progress === 100) {
        clearInterval(this.pollInterval!);
        onComplete();
      }
    }, 10000); // Check every 10 seconds
  }
  
  stopMonitoring() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
    }
  }
}

// Usage in UpgradeVersionModal
const monitor = new UpgradeMonitor();

const handleSubmit = async () => {
  await deploymentsApi.upgradeVersion(tenantId, deploymentId, mongoVersion);
  
  showSuccess('Upgrade started', 'Upgrading to ' + mongoVersion);
  
  monitor.startMonitoring(
    tenantId,
    deploymentId,
    mongoVersion,
    (progress) => {
      showInfo(`Upgrade ${progress.progress}% complete`, 
        `Replica ${progress.currentReplica} of ${progress.totalReplicas} upgraded`
      );
    },
    () => {
      showSuccess('Upgrade complete!', 'All replicas upgraded successfully');
    }
  );
  
  onClose();
};
```

### **Pros:**
✅ Non-intrusive  
✅ User can navigate anywhere  
✅ Simple to implement  
✅ Works well for background operations  

### **Cons:**
❌ Toasts disappear (might miss updates)  
❌ No way to see current status later  
❌ Less detailed information  

---

## **Recommendation: Option 1** ⭐

I recommend **Option 1 (Modal with Progress Tracking)** because:

1. **Best User Experience**
   - User sees exactly what's happening
   - Clear feedback on progress
   - Can close modal if needed

2. **Most Informative**
   - Shows replica-by-replica status
   - Displays version per replica
   - Shows estimated time remaining

3. **Handles Errors Better**
   - Can show error messages in modal
   - User knows immediately if something fails
   - Can retry from same modal

4. **Consistent with Industry Standards**
   - Similar to MongoDB Atlas
   - Similar to AWS, GCP upgrade flows
   - Users expect this behavior

---

## **Hybrid Approach** (Best of All Worlds) 🌟

Combine all three for the ultimate UX:

### **Flow:**
1. **Show modal with progress** (Option 1) - Primary UX
2. **Allow "Close and Continue in Background"** button
3. **If closed, show banner on deployment page** (Option 2) - Secondary UX
4. **Send toast notifications for milestones** (Option 3) - Bonus

### **User Experience:**

```
[Click Upgrade]
   ↓
[Modal shows progress with spinner and replica status]
   ↓
User has 3 choices:
   A) Stay in modal → See real-time progress → Modal shows completion
   B) Click "Close" → Modal closes → Banner shows on deployment page
   C) Navigate away → Toast notifications on milestones
```

---

## Implementation Plan

### **Phase 1: Core Progress Tracking**
1. Add backend endpoint: `GET /tenants/{tid}/deployments/{id}/upgrade-status`
2. Add polling mechanism in frontend
3. Track replica versions during upgrade

### **Phase 2: Modal Enhancement**
1. Add upgrade states to UpgradeVersionModal
2. Add progress UI components
3. Add polling logic
4. Add "Close and Continue" button

### **Phase 3: Deployment Page Integration**
1. Add upgrade banner component
2. Detect upgrade in progress
3. Show progress on deployment page

### **Phase 4: Toast Notifications** (Optional)
1. Add upgrade monitor service
2. Emit toast notifications on milestones

---

## Code Structure

```
src/
├── components/
│   ├── UpgradeVersionModal.tsx          # Enhanced with progress
│   ├── UpgradeProgressView.tsx          # New: Progress display component
│   ├── UpgradeBanner.tsx                # New: Banner for deployment page
│   └── ReplicaStatusTable.tsx           # New: Replica status table
├── lib/
│   ├── api.ts                           # Add getUpgradeStatus()
│   └── upgradeMonitor.ts                # New: Upgrade monitoring service
└── hooks/
    └── useUpgradePolling.ts             # New: Custom hook for polling
```

---

## Estimated Implementation Time

| Phase | Time | Complexity |
|-------|------|------------|
| Option 1 (Modal) | 4-6 hours | Medium |
| Option 2 (Banner) | 2-3 hours | Low |
| Option 3 (Toasts) | 2-3 hours | Low |
| **Hybrid (All 3)** | **6-8 hours** | **Medium** |

---

## Questions for You

1. **Which option do you prefer?**
   - Option 1 (Modal with progress)
   - Option 2 (Banner on page)
   - Option 3 (Toast notifications)
   - Hybrid (All three)

2. **Should user be able to cancel an in-progress upgrade?**
   - Yes → Add cancel button
   - No → Just show progress

3. **What happens if user navigates away during upgrade?**
   - Show banner on deployment page
   - Keep monitoring in background
   - Both

4. **Should we show logs/events during upgrade?**
   - Yes → Add event timeline
   - No → Just show replica status

Let me know your preference and I'll implement it! 🚀
