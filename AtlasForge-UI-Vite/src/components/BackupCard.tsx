import { useState } from 'react';
import { deploymentsApi } from '@/lib/api';
import { useToast } from './Toast';
import { ConfirmModal } from './ConfirmModal';

interface BackupCardProps {
  tenantId: string;
  deploymentId: string;
  initialEnabled?: boolean;
}

export function BackupCard({ tenantId, deploymentId, initialEnabled = false }: BackupCardProps) {
  const [enabled, setEnabled] = useState(initialEnabled);
  const [showConfirm, setShowConfirm] = useState(false);
  const [pendingEnabled, setPendingEnabled] = useState(false);
  const [updating, setUpdating] = useState(false);
  const { showSuccess, showError } = useToast();

  const handleToggle = () => {
    setPendingEnabled(!enabled);
    setShowConfirm(true);
  };

  const handleConfirm = async () => {
    setUpdating(true);
    try {
      await deploymentsApi.updateBackup(tenantId, deploymentId, pendingEnabled);
      setEnabled(pendingEnabled);
      showSuccess(
        `Backup ${pendingEnabled ? 'enabled' : 'disabled'}`,
        `Backup has been ${pendingEnabled ? 'enabled' : 'disabled'} for this deployment`
      );
    } catch (error: any) {
      showError('Failed to update backup', error.detail);
    } finally {
      setUpdating(false);
      setShowConfirm(false);
    }
  };

  return (
    <>
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-semibold text-mongodb-forest">Backup Configuration</h3>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={enabled}
              onChange={handleToggle}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-mongodb-green/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-mongodb-green"></div>
          </label>
        </div>

        <div>
          {enabled ? (
            <>
              <span className="badge badge-green">Enabled</span>
              <p className="text-sm text-gray-600 mt-3">
                Backup is enabled for this deployment via Ops Manager integration.
              </p>
            </>
          ) : (
            <>
              <span className="badge badge-gray">Disabled</span>
              <p className="text-sm text-gray-600 mt-3">
                Enable backup to configure automated backups via Ops Manager.
              </p>
            </>
          )}
        </div>
      </div>

      <ConfirmModal
        open={showConfirm}
        onClose={() => setShowConfirm(false)}
        onConfirm={handleConfirm}
        title={`${pendingEnabled ? 'Enable' : 'Disable'} Backup`}
        message={`Are you sure you want to ${pendingEnabled ? 'enable' : 'disable'} backup for this deployment?`}
        confirmText={pendingEnabled ? 'Enable' : 'Disable'}
        loading={updating}
      />
    </>
  );
}
