import React, { useState } from 'react';
import Modal from '@leafygreen-ui/modal';
import TextInput from '@leafygreen-ui/text-input';
import Button from '@leafygreen-ui/button';
import { RadioBoxGroup, RadioBox } from '@leafygreen-ui/radio-box-group';
import Banner from '@leafygreen-ui/banner';
import { deploymentsApi } from '@/lib/api/deployments';
import { useToast } from './Toast';
import { CreateDeploymentRequest } from '@/lib/types';
import { validateMembers } from '@/lib/utils';

interface CreateDeploymentModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  tenantId: string;
}

export function CreateDeploymentModal({ open, onClose, onSuccess, tenantId }: CreateDeploymentModalProps) {
  const [deploymentId, setDeploymentId] = useState('');
  const [type, setType] = useState<'Standalone' | 'ReplicaSet' | 'ShardedCluster'>('ReplicaSet');
  const [mongoVersion, setMongoVersion] = useState('8.0.3');
  const [members, setMembers] = useState('3');
  const [displayName, setDisplayName] = useState('');
  const [environment, setEnvironment] = useState('');
  const [loading, setLoading] = useState(false);
  const { showSuccess, showError, showWarning } = useToast();

  const membersValidation = validateMembers(parseInt(members) || 0);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!deploymentId.trim()) {
      showError('Deployment ID is required');
      return;
    }

    if (!mongoVersion.trim()) {
      showError('MongoDB version is required');
      return;
    }

    if (type === 'ReplicaSet' && !membersValidation.valid) {
      showError('Invalid member count', membersValidation.error);
      return;
    }

    setLoading(true);
    try {
      const request: CreateDeploymentRequest = {
        deploymentId: deploymentId.trim(),
        type,
        mongoVersion: mongoVersion.trim(),
        displayName: displayName.trim() || undefined,
        environment: environment.trim() || undefined,
      };

      if (type === 'ReplicaSet') {
        request.members = parseInt(members);
      }

      await deploymentsApi.create(tenantId, request);
      showSuccess('Deployment created successfully', `Deployment ${deploymentId} is being provisioned`);
      
      if (membersValidation.warning) {
        showWarning('Configuration warning', membersValidation.warning);
      }
      
      handleClose();
      onSuccess();
    } catch (error: any) {
      showError('Failed to create deployment', error.detail || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setDeploymentId('');
    setType('ReplicaSet');
    setMongoVersion('8.0.3');
    setMembers('3');
    setDisplayName('');
    setEnvironment('');
    onClose();
  };

  return (
    <Modal open={open} setOpen={handleClose}>
      <form onSubmit={handleSubmit}>
        <div style={{ padding: '24px' }}>
          <h2 style={{ marginBottom: '24px', fontSize: '24px', fontWeight: 600 }}>
            Create MongoDB Deployment
          </h2>

          <div style={{ marginBottom: '16px' }}>
            <TextInput
              label="Deployment ID"
              description="Unique identifier (e.g., rs-orders, sc-analytics)"
              value={deploymentId}
              onChange={(e) => setDeploymentId(e.target.value)}
              required
            />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <RadioBoxGroup
              label="Deployment Type"
              value={type}
              onChange={(e) => setType(e.target.value as any)}
            >
              <RadioBox value="Standalone">Standalone</RadioBox>
              <RadioBox value="ReplicaSet">Replica Set</RadioBox>
              <RadioBox value="ShardedCluster" disabled>
                Sharded Cluster (Coming Soon)
              </RadioBox>
            </RadioBoxGroup>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <TextInput
              label="MongoDB Version"
              description="e.g., 8.0.3, 7.0.14, 8.0.17-ent"
              value={mongoVersion}
              onChange={(e) => setMongoVersion(e.target.value)}
              required
            />
          </div>

          {type === 'ReplicaSet' && (
            <div style={{ marginBottom: '16px' }}>
              <TextInput
                label="Number of Members"
                description="Recommended: odd number >= 3"
                type="number"
                value={members}
                onChange={(e) => setMembers(e.target.value)}
                state={membersValidation.valid ? undefined : 'error'}
                errorMessage={membersValidation.error}
              />
              {membersValidation.warning && (
                <Banner variant="warning" style={{ marginTop: '8px' }}>
                  {membersValidation.warning}
                </Banner>
              )}
            </div>
          )}

          <div style={{ marginBottom: '16px' }}>
            <TextInput
              label="Display Name"
              description="Human-readable name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          </div>

          <div style={{ marginBottom: '24px' }}>
            <TextInput
              label="Environment"
              description="e.g., dev, staging, prod"
              value={environment}
              onChange={(e) => setEnvironment(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
            <Button variant="default" onClick={handleClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading || !membersValidation.valid}>
              {loading ? 'Creating...' : 'Create Deployment'}
            </Button>
          </div>
        </div>
      </form>
    </Modal>
  );
}
