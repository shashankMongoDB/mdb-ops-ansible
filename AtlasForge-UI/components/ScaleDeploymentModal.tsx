import React, { useState } from 'react';
import Modal from '@leafygreen-ui/modal';
import TextInput from '@leafygreen-ui/text-input';
import Button from '@leafygreen-ui/button';
import Banner from '@leafygreen-ui/banner';
import { FormFooter } from '@leafygreen-ui/form-footer';
import { deploymentsApi } from '@/lib/api/deployments';
import { useToast } from './Toast';
import { validateMembers } from '@/lib/utils';

interface ScaleDeploymentModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  tenantId: string;
  deploymentId: string;
  currentMembers: number;
}

export function ScaleDeploymentModal({
  open,
  onClose,
  onSuccess,
  tenantId,
  deploymentId,
  currentMembers,
}: ScaleDeploymentModalProps) {
  const [members, setMembers] = useState(currentMembers.toString());
  const [loading, setLoading] = useState(false);
  const { showSuccess, showError, showWarning } = useToast();

  const membersValidation = validateMembers(parseInt(members) || 0);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const newMembers = parseInt(members);
    
    if (!membersValidation.valid) {
      showError('Invalid member count', membersValidation.error);
      return;
    }

    if (newMembers === currentMembers) {
      showError('No change', 'The member count is the same as current');
      return;
    }

    setLoading(true);
    try {
      await deploymentsApi.scale(tenantId, deploymentId, { members: newMembers });
      showSuccess(
        'Scaling initiated',
        `Deployment is scaling to ${newMembers} members`
      );
      
      if (membersValidation.warning) {
        showWarning('Configuration warning', membersValidation.warning);
      }
      
      onClose();
      onSuccess();
    } catch (error: any) {
      showError('Failed to scale deployment', error.detail || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal open={open} setOpen={onClose}>
      <form onSubmit={handleSubmit}>
        <div style={{ padding: '24px' }}>
          <h2 style={{ marginBottom: '24px', fontSize: '24px', fontWeight: 600 }}>
            Scale Deployment
          </h2>

          <Banner variant="info" style={{ marginBottom: '16px' }}>
            Current members: {currentMembers}
          </Banner>

          <div style={{ marginBottom: '16px' }}>
            <TextInput
              label="New Member Count"
              description="Recommended: odd number >= 3"
              type="number"
              value={members}
              onChange={(e) => setMembers(e.target.value)}
              state={membersValidation.valid ? undefined : 'error'}
              errorMessage={membersValidation.error}
            />
          </div>

          {membersValidation.warning && (
            <Banner variant="warning" style={{ marginBottom: '16px' }}>
              {membersValidation.warning}
            </Banner>
          )}

          <FormFooter
            primaryButton={
              <Button type="submit" disabled={loading || !membersValidation.valid}>
                {loading ? 'Scaling...' : 'Scale Deployment'}
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
