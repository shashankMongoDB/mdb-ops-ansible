import { useEffect, useState } from 'react';
import { ArrowPathIcon, ClipboardDocumentIcon, CheckIcon } from '@heroicons/react/24/outline';
import { deploymentsApi } from '@/lib/api';
import { useToast } from './Toast';
import { EnableCommunityBackupModal } from './EnableCommunityBackupModal';

interface CommunityBackupPanelProps {
  tenantId: string;
  deploymentId: string;
}

interface BackupStatus {
  enabled: boolean;
  status: string;
  schedule?: string | null;
  lastSuccessfulTime?: string | null;
  s3Path?: string | null;
  retentionDays?: number | null;
  message?: string | null;
}

export function CommunityBackupPanel({ tenantId, deploymentId }: CommunityBackupPanelProps) {
  const [status, setStatus] = useState<BackupStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [copiedS3, setCopiedS3] = useState(false);
  const [showEnableModal, setShowEnableModal] = useState(false);
  
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
        'Backup Enabled',
        'Backup has been enabled and will run on schedule'
      );
      setShowEnableModal(false);
      await loadStatus();
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
      {/* Info Banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
        <h4 className="text-sm font-semibold text-blue-900 mb-2">Community MongoDB Backup</h4>
        <p className="text-sm text-blue-800 mb-2">
          Backups use <strong>mongodump</strong> to create compressed archives and upload them to S3.
        </p>
        <p className="text-xs text-blue-700">
          <strong>S3 Permissions Required:</strong> The backup CronJob needs <code>s3:PutObject</code>, <code>s3:ListBucket</code>, and <code>s3:DeleteObject</code> on the S3 bucket/prefix below.
        </p>
      </div>

      {/* Status Card */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-semibold text-mongodb-forest">Backup Status</h3>
          <button onClick={loadStatus} className="text-mongodb-green hover:text-mongodb-green-dark" disabled={loading}>
            <ArrowPathIcon className="h-5 w-5" />
          </button>
        </div>

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

          {/* S3 Path */}
          {status.s3Path && (
            <div>
              <label className="text-xs text-gray-500 block mb-1">S3 Backup Location</label>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-gray-50 p-2 rounded border border-gray-200 font-mono text-xs break-all">
                  {status.s3Path}
                </div>
                <button
                  onClick={handleCopyS3Path}
                  className="flex-shrink-0 text-mongodb-green hover:text-mongodb-green-dark"
                  title="Copy S3 path"
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

      {/* Restore Instructions */}
      {status.enabled && (
        <div className="card bg-gray-50">
          <h4 className="text-sm font-semibold text-gray-900 mb-2">Restore Instructions</h4>
          <p className="text-xs text-gray-600 mb-2">
            To restore from a backup:
          </p>
          <ol className="list-decimal list-inside text-xs text-gray-600 space-y-1">
            <li>Download the backup archive from S3: <code className="bg-gray-200 px-1 py-0.5 rounded">aws s3 cp s3://... ./dump.tar.gz</code></li>
            <li>Extract: <code className="bg-gray-200 px-1 py-0.5 rounded">tar -xzf dump.tar.gz</code></li>
            <li>Restore with mongorestore: <code className="bg-gray-200 px-1 py-0.5 rounded">mongorestore --uri="..." ./dump-YYYYMMDD-HHMMSS/</code></li>
          </ol>
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
    </div>
  );
}
