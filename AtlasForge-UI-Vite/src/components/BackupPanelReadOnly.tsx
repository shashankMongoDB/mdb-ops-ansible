import { useEffect, useState } from 'react';
import { ClockIcon, ArrowPathIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import { deploymentsApi } from '@/lib/api';
import { useToast } from './Toast';
import { ConfirmModal } from './ConfirmModal';
import type { BackupStatus, BackupSnapshot } from '@/lib/types';

interface BackupPanelProps {
  tenantId: string;
  deploymentId: string;
  tenantPlan: 'enterprise' | 'community';
}

export function BackupPanel({ tenantId, deploymentId, tenantPlan }: BackupPanelProps) {
  const [status, setStatus] = useState<BackupStatus | null>(null);
  const [snapshots, setSnapshots] = useState<BackupSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [showRestoreConfirm, setShowRestoreConfirm] = useState(false);
  const [selectedSnapshot, setSelectedSnapshot] = useState<string | null>(null);
  const [restoringBackup, setRestoringBackup] = useState(false);
  
  const { showSuccess, showError: showErrorToast } = useToast();

  useEffect(() => {
    loadData();
  }, [tenantId, deploymentId]);

  const loadData = async () => {
    if (tenantPlan === 'community') {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
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
          </p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="card">
        <div className="text-gray-500">Loading backup information...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <h3 className="text-xl font-semibold text-mongodb-forest mb-4">Backup Status</h3>
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
        <h3 className="text-xl font-semibold text-mongodb-forest mb-4">Backup Status</h3>
        <p className="text-gray-500">No backup data available</p>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-6">
        {/* Info Banner */}
        <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
          <p className="text-sm text-blue-800">
            <span className="font-medium">Read-Only View:</span> This panel shows backup status, snapshots, and allows submitting restore jobs. 
            Use Ops Manager UI for backup policy changes and on-demand snapshots.
          </p>
        </div>

        {/* Status Card */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-semibold text-mongodb-forest">Backup Status</h3>
            <button onClick={loadData} className="text-mongodb-green hover:text-mongodb-green-dark">
              <ArrowPathIcon className="h-5 w-5" />
            </button>
          </div>

          {status.error && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3 mb-4 flex items-start gap-2">
              <ExclamationTriangleIcon className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-yellow-800">{status.error}</p>
            </div>
          )}

          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <span className={`badge ${
                status.backupEnabled ? 'badge-green' : 'badge-gray'
              }`}>
                {status.backupEnabled ? 'Enabled' : 'Not Configured'}
              </span>
              <span className={`badge ${
                status.status === 'ACTIVE' ? 'badge-green' :
                status.status === 'NOT_CONFIGURED' ? 'badge-gray' :
                status.status === 'ERROR' ? 'badge-red' :
                'badge-gray'
              }`}>
                {status.status}
              </span>
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
          </div>
        </div>

        {/* Snapshots Card */}
        {snapshots.length > 0 && (
          <div className="card">
            <h3 className="text-xl font-semibold text-mongodb-forest mb-4">Backup Snapshots</h3>
            
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

        {snapshots.length === 0 && status.backupEnabled && (
          <div className="card">
            <p className="text-gray-500 text-center py-8">No snapshots available yet</p>
          </div>
        )}
      </div>

      {/* Restore Confirmation */}
      <ConfirmModal
        open={showRestoreConfirm}
        onClose={() => {
          setShowRestoreConfirm(false);
          setSelectedSnapshot(null);
        }}
        onConfirm={handleRestoreSnapshot}
        title="Restore from Snapshot"
        message={`Restore this deployment from snapshot? This will create a restore job in Ops Manager. Monitor progress in the Ops Manager UI. WARNING: This will replace the current data with the snapshot data.`}
        confirmText="Restore"
        loading={restoringBackup}
      />
    </>
  );
}
