import React, { useState } from 'react';
import Modal from '@leafygreen-ui/modal';
import TextInput from '@leafygreen-ui/text-input';
import Button from '@leafygreen-ui/button';
import Banner from '@leafygreen-ui/banner';
import { FormFooter } from '@leafygreen-ui/form-footer';
import { deploymentsApi } from '@/lib/api/deployments';
import { useToast } from './Toast';
import { isDowngrade } from '@/lib/utils';

interface UpgradeVersionModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  tenantId: string;
  deploymentId: string;
  currentVersion: string;
}

export function UpgradeVersionModal({
  open,
  onClose,
  onSuccess,
  tenantId,
  deploymentId,
  currentVersion,
}: UpgradeVersionModalProps) {
  const [mongoVersion, setMongoVersion] = useState('');
  const [loading, setLoading] = useState(false);
  const { showSuccess, showError } = useToast();

  const isDowngradeAttempt = mongoVersion.trim() && isDowngrade(currentVersion, mongoVersion.trim());

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const newVersion = mongoVersion.trim();
    
    if (!newVersion) {
      showError('MongoDB version is required');
      return;
    }

    if (newVersion === currentVersion) {
      showError('Version unchanged', 'The new version is the same as current');
      return;
    }

    if (isDowngradeAttempt) {
      showError(
        'Downgrade not allowed',
        'You cannot downgrade to an older MongoDB version'
      );
      return;
    }

    setLoading(true);
    try {
      await deploymentsApi.upgradeVersion(tenantId, deploymentId, { mongoVersion: newVersion });
      showSuccess(
        'Version upgrade initiated',
        `Deployment is upgrading to ${newVersion}`
      );
      onClose();
      onSuccess();
    } catch (error: any) {
      showError('Failed to upgrade version', error.detail || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal open={open} setOpen={onClose}>
      <form onSubmit={handleSubmit}>
        <div style={{ padding: '24px' }}>
          <h2 style={{ marginBottom: '24px', fontSize: '24px', fontWeight: 600 }}>
            Upgrade MongoDB Version
          </h2>

          <Banner variant="info" style={{ marginBottom: '16px' }}>
            Current version: {currentVersion}
          </Banner>

          {isDowngradeAttempt && (
            <Banner variant="warning" style={{ marginBottom: '16px' }}>
              Downgrade detected! Downgrades are not allowed.
            </Banner>
          )}

          <div style={{ marginBottom: '24px' }}>
            <TextInput
              label="New MongoDB Version"
              description="e.g., 8.0.17-ent, 7.0.14 (must be higher than current)"
              value={mongoVersion}
              onChange={(e) => setMongoVersion(e.target.value)}
              state={isDowngradeAttempt ? 'error' : undefined}
              errorMessage={isDowngradeAttempt ? 'Downgrade not allowed' : undefined}
            />
          </div>

          <FormFooter
            primaryButton={
              <Button type="submit" disabled={loading || isDowngradeAttempt}>
                {loading ? 'Upgrading...' : 'Upgrade Version'}
              </Button>
            }
            secondaryButton={
              <Button variant="default" onClick={onClose} disabled={loading}>
                Cancel
              </Button>
            }
          />
        </div>
      </form>
    </Modal>
  );
}
