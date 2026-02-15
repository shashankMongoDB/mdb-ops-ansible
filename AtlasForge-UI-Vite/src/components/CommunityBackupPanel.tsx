import { useEffect, useState } from 'react';
import { ArrowPathIcon, ClipboardDocumentIcon, CheckIcon } from '@heroicons/react/24/outline';
import { deploymentsApi } from '@/lib/api';
import { useToast } from './Toast';
import { EnableCommunityBackupModal } from './EnableCommunityBackupModal';
import { RestoreBackupModal } from './RestoreBackupModal';

interface CommunityBackupPanelProps {
  tenantId: string;
  deploymentId: string;
}

interface BackupSnapshot {
  filename: string;
  size: number;
  sizeFormatted: string;
  lastModified: string;
  timestamp: string;
  s3Key: string;
  s3Uri: string;
}

interface BackupStatus {
  enabled: boolean;
  type?: string | null;  // "s3" or "filesystem"
  status: string;
  schedule?: string | null;
  lastSuccessfulTime?: string | null;
  s3Path?: string | null;
  target?: string | null;  // For filesystem: "host:/path"
  retentionDays?: number | null;
  snapshots?: BackupSnapshot[];
  message?: string | null;
}

export function CommunityBackupPanel({ tenantId, deploymentId }: CommunityBackupPanelProps) {
  const [status, setStatus] = useState<BackupStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [copiedS3, setCopiedS3] = useState(false);
  const [showEnableModal, setShowEnableModal] = useState(false);
  const [showRestoreModal, setShowRestoreModal] = useState(false);
  const [selectedSnapshot, setSelectedSnapshot] = useState<BackupSnapshot | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const snapshotsPerPage = 10;
  
  const { showSuccess, showError } = useToast();

  useEffect(() => {
    loadStatus();
  }, [tenantId, deploymentId]);

  const loadStatus = async () => {
    try {
      setLoading(true);
      const data = await deploymentsApi.getCommunityBackupStatus(tenantId, deploymentId);
      setStatus(data);
    } catch (error: any) {
      showError('Failed to load backup status', error.detail);
    } finally {
      setLoading(false);
    }
  };

  const handleEnableBackup = async (config: any) => {
    setUpdating(true);
    try {
      await deploymentsApi.updateCommunityBackup(tenantId, deploymentId, {
        enabled: true,
        ...config
      });
      showSuccess(
        'Backup Configuration Started',
        'Backup resources are being created in the background. The CronJob will be ready within 1-2 minutes.'
      );
      setShowEnableModal(false);
      // Wait a bit before refreshing to let resources be created
      setTimeout(() => loadStatus(), 2000);
    } catch (error: any) {
      showError('Failed to enable backup', error.detail);
    } finally {
      setUpdating(false);
    }
  };

  const handleDisableBackup = async () => {
    const confirmed = window.confirm(
      'Disable backup? The CronJob will be suspended but existing backups will remain in S3.'
    );
    
    if (!confirmed) return;
    
    setUpdating(true);
    try {
      await deploymentsApi.updateCommunityBackup(tenantId, deploymentId, { enabled: false });
      showSuccess('Backup Disabled', 'Backup has been disabled');
      await loadStatus();
    } catch (error: any) {
      showError('Failed to disable backup', error.detail);
    } finally {
      setUpdating(false);
    }
  };

  const handleCopyS3Path = async () => {
    if (!status?.s3Path) return;
    
    try {
      await navigator.clipboard.writeText(status.s3Path);
      setCopiedS3(true);
      setTimeout(() => setCopiedS3(false), 2000);
    } catch (err) {
      showError('Failed to copy', 'Could not copy S3 path to clipboard');
    }
  };

  const formatDateTime = (isoString: string | null) => {
    if (!isoString) return 'Never';
    return new Date(isoString).toLocaleString();
  };

  if (loading) {
    return (
      <div className="card">
        <div className="text-gray-500">Loading backup information...</div>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="card">
        <h3 className="text-xl font-semibold text-mongodb-forest mb-4">Community Backup</h3>
        <p className="text-gray-500">Backup status unavailable</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Info Banner - Context aware based on backup state */}
      <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
        <h4 className="text-sm font-semibold text-blue-900 mb-2">
          Community MongoDB Backup {status?.enabled && status?.type && `- ${status.type.toUpperCase()} Mode`}
        </h4>
        
        {/* When backup is NOT enabled - show both options */}
        {(!status?.enabled || status?.status === 'SUSPENDED' || status?.status === 'NOT_CONFIGURED') ? (
          <>
            <p className="text-sm text-blue-800 mb-3">
              Automated backups for Community MongoDB deployments. Choose your backup target:
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="bg-white rounded-md p-3 border border-blue-200">
                <h5 className="font-semibold text-blue-900 text-xs mb-1">📦 S3 Backup</h5>
                <p className="text-xs text-blue-700 mb-1">
                  Upload to Amazon S3 for durable, off-cluster storage. Ideal for production environments.
                </p>
                <p className="text-xs text-blue-600">
                  <strong>Requires:</strong> S3 bucket with IAM permissions (PutObject, ListBucket, DeleteObject)
                </p>
              </div>
              <div className="bg-white rounded-md p-3 border border-blue-200">
                <h5 className="font-semibold text-blue-900 text-xs mb-1">💾 Filesystem Backup</h5>
                <p className="text-xs text-blue-700 mb-1">
                  Write to NFS/EFS mounted storage. Useful for on-premises or air-gapped environments.
                </p>
                <p className="text-xs text-blue-600">
                  <strong>Requires:</strong> NFS/EFS accessible from K8s with write permissions
                </p>
              </div>
            </div>
            <p className="text-xs text-blue-700 mt-3">
              <strong>How it works:</strong> A Kubernetes CronJob runs <code className="bg-blue-100 px-1 rounded">mongodump</code> on schedule, 
              compresses the data, and stores it to your chosen target. Old backups are cleaned up per retention policy.
            </p>
          </>
        ) : (
          <>
            {/* When S3 backup is enabled - show S3 info only */}
            {status.type === 's3' && (
              <>
                <p className="text-sm text-blue-800 mb-2">
                  Backups use <strong>mongodump</strong> to create compressed archives and upload them to Amazon S3 for durable storage.
                </p>
                <div className="bg-white rounded-md p-3 border border-blue-200">
                  <h5 className="font-semibold text-blue-900 text-xs mb-2">S3 Configuration</h5>
                  <ul className="text-xs text-blue-700 space-y-1">
                    <li>• Backups are encrypted and stored off-cluster</li>
                    <li>• Automatic retention cleanup after {status.retentionDays} days</li>
                    <li>• Runs on schedule: <code className="bg-blue-100 px-1 rounded">{status.schedule}</code></li>
                  </ul>
                  <p className="text-xs text-blue-600 mt-2">
                    <strong>Required Permissions:</strong> <code className="bg-blue-100 px-1 rounded">s3:PutObject</code>, 
                    <code className="bg-blue-100 px-1 rounded ml-1">s3:ListBucket</code>, 
                    <code className="bg-blue-100 px-1 rounded ml-1">s3:DeleteObject</code>
                  </p>
                </div>
              </>
            )}
            
            {/* When Filesystem backup is enabled - show Filesystem info only */}
            {status.type === 'filesystem' && (
              <>
                <p className="text-sm text-blue-800 mb-2">
                  Backups use <strong>mongodump</strong> to create compressed archives and write them directly to NFS/EFS storage.
                </p>
                <div className="bg-white rounded-md p-3 border border-blue-200">
                  <h5 className="font-semibold text-blue-900 text-xs mb-2">Filesystem Configuration</h5>
                  <ul className="text-xs text-blue-700 space-y-1">
                    <li>• Backups stored on mounted NFS/EFS volume</li>
                    <li>• Automatic retention cleanup after {status.retentionDays} days</li>
                    <li>• Runs on schedule: <code className="bg-blue-100 px-1 rounded">{status.schedule}</code></li>
                    <li>• Target: <code className="bg-blue-100 px-1 rounded">{status.target}</code></li>
                  </ul>
                  <p className="text-xs text-blue-600 mt-2">
                    <strong>Requirements:</strong> Network access to NFS/EFS and write permissions to the target path
                  </p>
                </div>
              </>
            )}
          </>
        )}
      </div>

      {/* Status Card */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-semibold text-mongodb-forest">Backup Status</h3>
          <button onClick={loadStatus} className="text-mongodb-green hover:text-mongodb-green-dark" disabled={loading} title="Refresh status">
            <ArrowPathIcon className="h-5 w-5" />
          </button>
        </div>

        {/* Info Message for newly enabled backups */}
        {status.enabled && !status.lastSuccessfulTime && (
          <div className="bg-blue-50 border border-blue-200 rounded-md p-3 mb-4">
            <p className="text-xs text-blue-800">
              ⏳ <strong>Backup setup in progress:</strong> The backup user and CronJob are being configured. 
              The first backup will run according to the schedule below. You can manually trigger a backup using kubectl if needed.
            </p>
          </div>
        )}

        <div className="space-y-4">
          {/* Status Badge */}
          <div className="flex items-center gap-3">
            <span className={`badge ${status.enabled ? 'badge-green' : 'badge-gray'}`}>
              {status.enabled ? 'Enabled' : 'Disabled'}
            </span>
            <span className={`badge ${
              status.status === 'ACTIVE' ? 'badge-green' :
              status.status === 'SUSPENDED' ? 'badge-gray' :
              'badge-gray'
            }`}>
              {status.status}
            </span>
          </div>

          {/* Details Grid */}
          {status.enabled && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-gray-500 block mb-1">Schedule</label>
                <p className="text-sm font-medium font-mono">{status.schedule || 'Not set'}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500 block mb-1">Retention</label>
                <p className="text-sm font-medium">{status.retentionDays || 7} days</p>
              </div>
              <div className="col-span-2">
                <label className="text-xs text-gray-500 block mb-1">Last Successful Backup</label>
                <p className="text-sm font-medium">{formatDateTime(status.lastSuccessfulTime || null)}</p>
              </div>
            </div>
          )}

          {/* Backup Location */}
          {(status.s3Path || status.target) && (
            <div>
              <label className="text-xs text-gray-500 block mb-1">
                {status.type === 'filesystem' ? 'Filesystem Backup Location' : 'S3 Backup Location'}
              </label>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-gray-50 p-2 rounded border border-gray-200 font-mono text-xs break-all">
                  {status.type === 'filesystem' ? status.target : status.s3Path}
                </div>
                <button
                  onClick={handleCopyS3Path}
                  className="flex-shrink-0 text-mongodb-green hover:text-mongodb-green-dark"
                  title="Copy path"
                >
                  {copiedS3 ? (
                    <CheckIcon className="h-5 w-5" />
                  ) : (
                    <ClipboardDocumentIcon className="h-5 w-5" />
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Toggle Button */}
          <div className="pt-4 border-t">
            {status.enabled ? (
              <button
                onClick={handleDisableBackup}
                disabled={updating}
                className="btn btn-secondary"
              >
                {updating ? 'Disabling...' : 'Disable Backup'}
              </button>
            ) : (
              <button
                onClick={() => setShowEnableModal(true)}
                disabled={updating}
                className="btn btn-primary"
              >
                Enable Backup
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Message */}
      {status.message && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
          <p className="text-sm text-yellow-800">{status.message}</p>
        </div>
      )}

      {/* Snapshots List */}
      {status.enabled && status.type === 's3' && status.snapshots && status.snapshots.length > 0 && (() => {
        const totalPages = Math.ceil(status.snapshots.length / snapshotsPerPage);
        const startIndex = (currentPage - 1) * snapshotsPerPage;
        const endIndex = startIndex + snapshotsPerPage;
        const currentSnapshots = status.snapshots.slice(startIndex, endIndex);

        return (
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-mongodb-forest">Backup Snapshots</h3>
              <button onClick={loadStatus} className="text-mongodb-green hover:text-mongodb-green-dark text-sm" title="Refresh snapshots">
                <ArrowPathIcon className="h-4 w-4" />
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Snapshot
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Timestamp
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Size
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {currentSnapshots.map((snapshot) => (
                    <tr key={snapshot.filename} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-mono text-gray-900">
                        {snapshot.filename}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {snapshot.timestamp}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {snapshot.sizeFormatted}
                      </td>
                      <td className="px-4 py-3 text-right text-sm">
                        <button
                          onClick={() => {
                            setSelectedSnapshot(snapshot);
                            setShowRestoreModal(true);
                          }}
                          className="text-mongodb-green hover:text-mongodb-green-dark text-sm font-medium"
                          title="Restore from this snapshot"
                        >
                          Restore
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between mt-4 pt-4 border-t">
              <p className="text-xs text-gray-500">
                Showing {startIndex + 1}-{Math.min(endIndex, status.snapshots.length)} of {status.snapshots.length} snapshots | Retention: {status.retentionDays} days
              </p>
              
              {totalPages > 1 && (
                <div className="flex gap-2">
                  <button
                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Previous
                  </button>
                  <span className="px-3 py-1 text-sm text-gray-700">
                    Page {currentPage} of {totalPages}
                  </span>
                  <button
                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                    className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                  </button>
                </div>
              )}
            </div>
          </div>
        );
      })()}

      {/* Restore Instructions */}
      {status.enabled && (
        <div className="card bg-gray-50">
          <h4 className="text-sm font-semibold text-gray-900 mb-2">Restore Instructions</h4>
          <p className="text-xs text-gray-600 mb-2">
            To restore from a backup:
          </p>
          {status.type === 's3' ? (
            <ol className="list-decimal list-inside text-xs text-gray-600 space-y-1">
              <li>Download the backup archive from S3: <code className="bg-gray-200 px-1 py-0.5 rounded">aws s3 cp s3://... ./dump.gz</code></li>
              <li>Restore with mongorestore: <code className="bg-gray-200 px-1 py-0.5 rounded">mongorestore --uri="..." --archive=./dump.gz --gzip</code></li>
            </ol>
          ) : (
            <ol className="list-decimal list-inside text-xs text-gray-600 space-y-1">
              <li>Access the filesystem backup location: <code className="bg-gray-200 px-1 py-0.5 rounded">{status.target}</code></li>
              <li>Copy the backup file to your local machine</li>
              <li>Restore with mongorestore: <code className="bg-gray-200 px-1 py-0.5 rounded">mongorestore --uri="..." --archive=./dump-YYYYMMDD-HHMMSS.gz --gzip</code></li>
            </ol>
          )}
        </div>
      )}

      {/* Enable Backup Modal */}
      <EnableCommunityBackupModal
        open={showEnableModal}
        onClose={() => setShowEnableModal(false)}
        onSubmit={handleEnableBackup}
        loading={updating}
        deploymentId={deploymentId}
      />

      {/* Restore Backup Modal */}
      {selectedSnapshot && (
        <RestoreBackupModal
          isOpen={showRestoreModal}
          onClose={() => {
            setShowRestoreModal(false);
            setSelectedSnapshot(null);
          }}
          tenantId={tenantId}
          deploymentId={deploymentId}
          snapshot={selectedSnapshot}
          onRestoreStarted={() => {
            loadStatus();
          }}
        />
      )}
    </div>
  );
}
