import { useEffect, useState } from 'react';
import { ClockIcon, DocumentDuplicateIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import { deploymentsApi } from '@/lib/api';
import { useToast } from './Toast';
import { ConfirmModal } from './ConfirmModal';
import type { BackupStatus, BackupPolicy, BackupSnapshot } from '@/lib/types';

// Type guard to ensure all API methods exist
if (!deploymentsApi.startBackup || !deploymentsApi.stopBackup || !deploymentsApi.restoreBackup) {
  console.error('Missing backup API methods');
}

interface BackupPanelProps {
  tenantId: string;
  deploymentId: string;
  tenantPlan: 'enterprise' | 'community';
}

export function BackupPanel({ tenantId, deploymentId, tenantPlan }: BackupPanelProps) {
  const [status, setStatus] = useState<BackupStatus | null>(null);
  const [policies, setPolicies] = useState<BackupPolicy[]>([]);
  const [snapshots, setSnapshots] = useState<BackupSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [showPolicyModal, setShowPolicyModal] = useState(false);
  const [selectedPolicy, setSelectedPolicy] = useState<string>('');
  const [changingPolicy, setChangingPolicy] = useState(false);
  
  const [showSnapshotConfirm, setShowSnapshotConfirm] = useState(false);
  const [triggeringSnapshot, setTriggeringSnapshot] = useState(false);
  
  const [showEnableConfirm, setShowEnableConfirm] = useState(false);
  const [enablingBackup, setEnablingBackup] = useState(false);
  
  const [autoRefresh, setAutoRefresh] = useState(false);
  
  // Start/Stop backup state
  const [startingBackup, setStartingBackup] = useState(false);
  const [stoppingBackup, setStoppingBackup] = useState(false);
  const [showStartConfirm, setShowStartConfirm] = useState(false);
  const [showStopConfirm, setShowStopConfirm] = useState(false);
  
  // Restore state
  const [showRestoreConfirm, setShowRestoreConfirm] = useState(false);
  const [selectedSnapshot, setSelectedSnapshot] = useState<string | null>(null);
  const [restoringBackup, setRestoringBackup] = useState(false);
  
  const { showSuccess, showError: showErrorToast } = useToast();

  useEffect(() => {
    loadData();
  }, [tenantId, deploymentId]);

  // Auto-refresh when status is NOT_READY (waiting for OM project)
  useEffect(() => {
    const isWaiting = !status?.backupEnabled && status?.status === 'NOT_READY';
    
    if (isWaiting && autoRefresh) {
      const timer = setTimeout(() => {
        loadData();
      }, 5000); // Check every 5 seconds
      
      return () => clearTimeout(timer);
    } else if (!isWaiting && autoRefresh) {
      // Stop auto-refresh when status changes to ready
      setAutoRefresh(false);
    }
  }, [status, autoRefresh]);

  const loadData = async () => {
    if (tenantPlan === 'community') {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      // Load status and snapshots in parallel
      const [statusData, snapshotsData] = await Promise.all([
        deploymentsApi.getBackupStatus(tenantId, deploymentId),
        deploymentsApi.listBackupSnapshots(tenantId, deploymentId)
      ]);
      
      setStatus(statusData);
      setSnapshots(snapshotsData);
    } catch (error: any) {
      const errorMsg = error.detail || error.message || 'Failed to load backup data';
      setError(errorMsg);
      showErrorToast('Failed to load backup data', errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const loadPolicies = async () => {
    try {
      const policiesData = await deploymentsApi.listBackupPolicies(tenantId);
      setPolicies(policiesData);
    } catch (error: any) {
      showErrorToast('Failed to load policies', error.detail || 'Could not fetch backup policies');
    }
  };

  const handleEnableBackup = async () => {
    setEnablingBackup(true);
    setShowEnableConfirm(false);
    
    try {
      await deploymentsApi.updateBackup(tenantId, deploymentId, true);
      showSuccess('Backup Enabled', 'Backup has been enabled. Waiting for Ops Manager to initialize...');
      setAutoRefresh(true); // Start auto-refresh
      await loadData();
    } catch (error: any) {
      showErrorToast('Failed to enable backup', error.detail);
    } finally {
      setEnablingBackup(false);
    }
  };

  const handleOpenPolicyModal = async () => {
    await loadPolicies();
    setShowPolicyModal(true);
  };

  const handleChangePolicy = async () => {
    if (!selectedPolicy) return;
    
    setChangingPolicy(true);
    try {
      await deploymentsApi.setBackupPolicy(tenantId, deploymentId, selectedPolicy);
      showSuccess('Policy Updated', 'Backup policy has been changed successfully');
      setShowPolicyModal(false);
      await loadData();
    } catch (error: any) {
      showErrorToast('Failed to change policy', error.detail);
    } finally {
      setChangingPolicy(false);
    }
  };

  const handleTriggerSnapshot = async () => {
    setTriggeringSnapshot(true);
    setShowSnapshotConfirm(false);
    
    try {
      await deploymentsApi.triggerBackupSnapshot(tenantId, deploymentId);
      showSuccess('Snapshot Triggered', 'On-demand snapshot has been initiated');
      await loadData();
    } catch (error: any) {
      showErrorToast('Failed to trigger snapshot', error.detail);
    } finally {
      setTriggeringSnapshot(false);
    }
  };

  const handleStartBackup = async () => {
    setStartingBackup(true);
    setShowStartConfirm(false);
    
    try {
      await deploymentsApi.startBackup(tenantId, deploymentId);
      showSuccess('Backup Started', 'Backup has been started in Ops Manager');
      await loadData();
    } catch (error: any) {
      showErrorToast('Failed to start backup', error.detail);
    } finally {
      setStartingBackup(false);
    }
  };

  const handleStopBackup = async () => {
    setStoppingBackup(true);
    setShowStopConfirm(false);
    
    try {
      await deploymentsApi.stopBackup(tenantId, deploymentId);
      showSuccess('Backup Stopped', 'Backup has been stopped in Ops Manager');
      await loadData();
    } catch (error: any) {
      showErrorToast('Failed to stop backup', error.detail);
    } finally {
      setStoppingBackup(false);
    }
  };

  const handleRestoreSnapshot = async () => {
    if (!selectedSnapshot) return;
    
    setRestoringBackup(true);
    setShowRestoreConfirm(false);
    
    try {
      await deploymentsApi.restoreBackup(tenantId, deploymentId, selectedSnapshot);
      showSuccess(
        'Restore Job Submitted', 
        'Restore job has been submitted in Ops Manager. Monitor progress in the Ops Manager UI.'
      );
      setSelectedSnapshot(null);
      await loadData();
    } catch (error: any) {
      showErrorToast('Failed to restore snapshot', error.detail);
    } finally {
      setRestoringBackup(false);
    }
  };

  const formatDateTime = (isoString: string | null) => {
    if (!isoString) return 'Never';
    return new Date(isoString).toLocaleString();
  };

  // Community plan - show not available message
  if (tenantPlan === 'community') {
    return (
      <div className="card">
        <h3 className="text-xl font-semibold text-mongodb-forest mb-4">Backup Configuration</h3>
        <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
          <p className="text-sm text-yellow-800">
            <span className="font-medium">Enterprise Feature:</span> Backup via Ops Manager is only available for Enterprise deployments. 
            Community deployments use alternative backup mechanisms.
          </p>
        </div>
        
        <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
          <p className="text-sm text-blue-800 font-medium mb-2">Prerequisites for Enterprise Backup:</p>
          <ul className="text-sm text-blue-800 list-disc list-inside space-y-1">
            <li>Ops Manager blockstore configured</li>
            <li>Oplog store configured</li>
            <li>Backup daemons running</li>
            <li>Valid Ops Manager license</li>
          </ul>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="card">
        <div className="text-gray-500">Loading backup configuration...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <h3 className="text-xl font-semibold text-mongodb-forest mb-4">Backup Configuration</h3>
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-sm text-red-800">Error: {error}</p>
          <button onClick={loadData} className="btn-secondary mt-3">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="card">
        <h3 className="text-xl font-semibold text-mongodb-forest mb-4">Backup Configuration</h3>
        <p className="text-gray-500">No backup data available</p>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-6">
        {/* Status Card */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-semibold text-mongodb-forest">Backup Status</h3>
            <button onClick={loadData} className="text-mongodb-green hover:text-mongodb-green-dark">
              <ArrowPathIcon className="h-5 w-5" />
            </button>
          </div>

          {!status.backupEnabled && status.status === 'NOT_READY' ? (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <span className="badge badge-blue">Initializing</span>
                <div className="flex items-center gap-1">
                  <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                  {autoRefresh && <span className="text-xs text-gray-500">Auto-refreshing...</span>}
                </div>
              </div>
              <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
                <p className="text-sm text-blue-800 mb-2">
                  <span className="font-medium">Discovering Ops Manager Project:</span> 
                  Looking up the Ops Manager project to retrieve backup configuration.
                </p>
                <p className="text-sm text-blue-700">
                  Project should already exist. If this persists, the project may not be visible in Ops Manager yet.
                </p>
              </div>
              <div className="mt-4 flex gap-2">
                <button
                  onClick={loadData}
                  className="btn-secondary text-sm"
                >
                  Check Again
                </button>
                <button
                  onClick={() => setAutoRefresh(!autoRefresh)}
                  className={`text-sm px-3 py-2 rounded ${autoRefresh ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'}`}
                >
                  {autoRefresh ? 'Stop Auto-Refresh' : 'Enable Auto-Refresh'}
                </button>
              </div>
            </div>
          ) : !status.backupEnabled ? (
            <div>
              <span className="badge badge-gray">Disabled</span>
              <p className="text-sm text-gray-600 mt-3 mb-4">
                Backup is not enabled for this deployment. Enable backup to start automated backups via Ops Manager.
              </p>
              <button
                onClick={() => setShowEnableConfirm(true)}
                disabled={enablingBackup}
                className="btn-primary"
              >
                {enablingBackup ? 'Enabling...' : 'Enable Backup'}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="badge badge-green">Enabled</span>
                  <span className={`badge ${
                    status.status === 'ACTIVE' || status.status === 'STARTED' ? 'badge-green' :
                    status.status === 'STOPPED' ? 'badge-gray' :
                    status.status === 'ERROR' ? 'badge-red' :
                    'badge-gray'
                  }`}>
                    {status.status}
                  </span>
                </div>
                <div className="flex gap-2">
                  {status.status !== 'STARTED' && status.status !== 'ACTIVE' && (
                    <button
                      onClick={() => setShowStartConfirm(true)}
                      disabled={startingBackup}
                      className="btn-primary text-sm"
                    >
                      {startingBackup ? 'Starting...' : 'Start Backup'}
                    </button>
                  )}
                  {(status.status === 'STARTED' || status.status === 'ACTIVE') && (
                    <button
                      onClick={() => setShowStopConfirm(true)}
                      disabled={stoppingBackup}
                      className="btn-secondary text-sm"
                    >
                      {stoppingBackup ? 'Stopping...' : 'Stop Backup'}
                    </button>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-gray-500 block mb-1">Policy</label>
                  <p className="text-sm font-medium">{status.policyName || 'None'}</p>
                </div>
                <div>
                  <label className="text-xs text-gray-500 block mb-1">Last Snapshot</label>
                  <p className="text-sm font-medium">{formatDateTime(status.lastSnapshotTime)}</p>
                </div>
                <div>
                  <label className="text-xs text-gray-500 block mb-1">Point-in-Time Restore</label>
                  <p className="text-sm font-medium">
                    {status.pitrEnabled ? (
                      <span className="text-green-600">Enabled</span>
                    ) : (
                      <span className="text-gray-500">Disabled</span>
                    )}
                  </p>
                </div>
              </div>

              <div className="flex gap-2 pt-4 border-t">
                <button
                  onClick={handleOpenPolicyModal}
                  className="btn-secondary text-sm"
                >
                  Change Policy
                </button>
                <button
                  onClick={() => setShowSnapshotConfirm(true)}
                  disabled={triggeringSnapshot}
                  className="btn-primary text-sm flex items-center gap-2"
                >
                  <DocumentDuplicateIcon className="h-4 w-4" />
                  {triggeringSnapshot ? 'Taking Snapshot...' : 'Take Snapshot Now'}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Snapshots Card */}
        {status.backupEnabled && snapshots.length > 0 && (
          <div className="card">
            <h3 className="text-xl font-semibold text-mongodb-forest mb-4">Recent Snapshots</h3>
            
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Expires</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {snapshots.map((snapshot) => (
                    <tr key={snapshot.snapshotId}>
                      <td className="px-4 py-3 text-sm text-gray-900">
                        <div className="flex items-center gap-2">
                          <ClockIcon className="h-4 w-4 text-gray-400" />
                          {formatDateTime(snapshot.createdAt)}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <span className={`badge ${
                          snapshot.type === 'on-demand' ? 'badge-blue' : 'badge-gray'
                        }`}>
                          {snapshot.type}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <span className={`badge ${
                          snapshot.status === 'COMPLETED' ? 'badge-green' :
                          snapshot.status === 'IN_PROGRESS' ? 'badge-blue' :
                          snapshot.status === 'FAILED' ? 'badge-red' :
                          'badge-gray'
                        }`}>
                          {snapshot.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {formatDateTime(snapshot.expiresAt)}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {snapshot.status === 'COMPLETED' && (
                          <button
                            onClick={() => {
                              setSelectedSnapshot(snapshot.snapshotId);
                              setShowRestoreConfirm(true);
                            }}
                            disabled={restoringBackup}
                            className="text-mongodb-green hover:text-mongodb-green-dark text-sm font-medium"
                          >
                            Restore
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Policy Selection Modal */}
      {showPolicyModal && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-semibold mb-4">Change Backup Policy</h3>
            
            {policies.length === 0 ? (
              <p className="text-sm text-gray-600 mb-4">No policies available</p>
            ) : (
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select Policy:
                </label>
                <select
                  value={selectedPolicy}
                  onChange={(e) => setSelectedPolicy(e.target.value)}
                  className="input"
                >
                  <option value="">Choose a policy...</option>
                  {policies.map((policy) => (
                    <option key={policy.policyId} value={policy.policyId}>
                      {policy.name} - {policy.frequency}
                    </option>
                  ))}
                </select>
                {selectedPolicy && policies.find(p => p.policyId === selectedPolicy) && (
                  <p className="text-xs text-gray-500 mt-2">
                    {policies.find(p => p.policyId === selectedPolicy)?.description}
                  </p>
                )}
              </div>
            )}

            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowPolicyModal(false)}
                className="btn-secondary"
                disabled={changingPolicy}
              >
                Cancel
              </button>
              <button
                onClick={handleChangePolicy}
                disabled={!selectedPolicy || changingPolicy}
                className="btn-primary"
              >
                {changingPolicy ? 'Changing...' : 'Change Policy'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Enable Backup Confirmation */}
      <ConfirmModal
        open={showEnableConfirm}
        onClose={() => setShowEnableConfirm(false)}
        onConfirm={handleEnableBackup}
        title="Enable Backup"
        message="Enable automated backups via Ops Manager for this deployment? Ensure Ops Manager is properly configured with blockstore, oplog store, and backup daemons."
        confirmText="Enable"
        loading={enablingBackup}
      />

      {/* Snapshot Confirmation */}
      <ConfirmModal
        open={showSnapshotConfirm}
        onClose={() => setShowSnapshotConfirm(false)}
        onConfirm={handleTriggerSnapshot}
        title="Take Snapshot Now"
        message="Trigger an on-demand backup snapshot? This snapshot will be retained for 7 days."
        confirmText="Take Snapshot"
        loading={triggeringSnapshot}
      />

      {/* Start Backup Confirmation */}
      <ConfirmModal
        open={showStartConfirm}
        onClose={() => setShowStartConfirm(false)}
        onConfirm={handleStartBackup}
        title="Start Backup"
        message="Start backup for this deployment in Ops Manager? This will enable automated snapshots according to the assigned backup policy."
        confirmText="Start Backup"
        loading={startingBackup}
      />

      {/* Stop Backup Confirmation */}
      <ConfirmModal
        open={showStopConfirm}
        onClose={() => setShowStopConfirm(false)}
        onConfirm={handleStopBackup}
        title="Stop Backup"
        message="Stop backup for this deployment in Ops Manager? This will pause automated snapshots. Existing snapshots will be retained."
        confirmText="Stop Backup"
        loading={stoppingBackup}
      />

      {/* Restore Confirmation */}
      <ConfirmModal
        open={showRestoreConfirm}
        onClose={() => {
          setShowRestoreConfirm(false);
          setSelectedSnapshot(null);
        }}
        onConfirm={handleRestoreSnapshot}
        title="Restore from Snapshot"
        message={`Restore this deployment from snapshot ${selectedSnapshot}? This will create a restore job in Ops Manager. Monitor progress in the Ops Manager UI.`}
        confirmText="Restore"
        loading={restoringBackup}
      />
    </>
  );
}
