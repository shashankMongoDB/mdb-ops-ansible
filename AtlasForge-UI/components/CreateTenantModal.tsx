import React, { useState } from 'react';
import Modal from '@leafygreen-ui/modal';
import TextInput from '@leafygreen-ui/text-input';
import Button from '@leafygreen-ui/button';
import { tenantsApi } from '@/lib/api/tenants';
import { useToast } from './Toast';
import { CreateTenantRequest } from '@/lib/types';

interface CreateTenantModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function CreateTenantModal({ open, onClose, onSuccess }: CreateTenantModalProps) {
  const [tenantId, setTenantId] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [environment, setEnvironment] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const { showSuccess, showError } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!tenantId.trim()) {
      showError('Tenant ID is required');
      return;
    }

    if (!/^[a-z0-9-]+$/.test(tenantId)) {
      showError('Tenant ID must contain only lowercase letters, numbers, and hyphens');
      return;
    }

    setLoading(true);
    try {
      const request: CreateTenantRequest = {
        tenantId: tenantId.trim(),
        displayName: displayName.trim() || undefined,
        environment: environment.trim() || undefined,
        notes: notes.trim() || undefined,
      };

      await tenantsApi.create(request);
      showSuccess('Tenant created successfully', `Tenant ${tenantId} has been created`);
      handleClose();
      onSuccess();
    } catch (error: any) {
      showError('Failed to create tenant', error.detail || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setTenantId('');
    setDisplayName('');
    setEnvironment('');
    setNotes('');
    onClose();
  };

  return (
    <Modal open={open} setOpen={handleClose}>
      <form onSubmit={handleSubmit}>
        <div style={{ padding: '24px' }}>
          <h2 style={{ marginBottom: '24px', fontSize: '24px', fontWeight: 600 }}>
            Onboard New Tenant
          </h2>

          <div style={{ marginBottom: '16px' }}>
            <TextInput
              label="Tenant ID"
              description="Lowercase letters, numbers, and hyphens only (e.g., t-acme)"
              value={tenantId}
              onChange={(e) => setTenantId(e.target.value)}
              required
            />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <TextInput
              label="Display Name"
              description="Human-readable name for the tenant"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <TextInput
              label="Environment"
              description="e.g., dev, staging, prod"
              value={environment}
              onChange={(e) => setEnvironment(e.target.value)}
            />
          </div>

          <div style={{ marginBottom: '24px' }}>
            <TextInput
              label="Notes"
              description="Optional notes about this tenant"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
            <Button variant="default" onClick={handleClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'Creating...' : 'Create Tenant'}
            </Button>
          </div>
        </div>
      </form>
    </Modal>
  );
}
