import { Fragment, useState } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { tenantsApi } from '@/lib/api';
import { useToast } from './Toast';
import type { CreateTenantRequest } from '@/lib/types';

interface CreateTenantModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function CreateTenantModal({ open, onClose, onSuccess }: CreateTenantModalProps) {
  const [formData, setFormData] = useState({
    tenantId: '',
    displayName: '',
    plan: 'enterprise' as 'enterprise' | 'community',
    environment: '',
    notes: '',
  });
  const [loading, setLoading] = useState(false);
  const { showSuccess, showError } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.tenantId.trim()) {
      showError('Tenant ID is required');
      return;
    }

    if (!/^[a-z0-9-]+$/.test(formData.tenantId)) {
      showError('Invalid Tenant ID', 'Use only lowercase letters, numbers, and hyphens');
      return;
    }

    setLoading(true);
    try {
      const request: CreateTenantRequest = {
        tenantId: formData.tenantId.trim(),
        displayName: formData.displayName.trim() || undefined,
        plan: formData.plan,
        environment: formData.environment.trim() || undefined,
        notes: formData.notes.trim() || undefined,
      };

      await tenantsApi.create(request);
      showSuccess('Tenant created successfully', `Tenant ${formData.tenantId} has been created`);
      handleClose();
      onSuccess();
    } catch (error: any) {
      showError('Failed to create tenant', error.detail || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setFormData({ tenantId: '', displayName: '', plan: 'enterprise', environment: '', notes: '' });
    onClose();
  };

  return (
    <Transition show={open} as={Fragment}>
      <Dialog onClose={handleClose} className="relative z-50">
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
        </Transition.Child>

        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Transition.Child
            as={Fragment}
            enter="ease-out duration-300"
            enterFrom="opacity-0 scale-95"
            enterTo="opacity-100 scale-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100 scale-100"
            leaveTo="opacity-0 scale-95"
          >
            <Dialog.Panel className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
              <div className="flex items-center justify-between mb-6">
                <Dialog.Title className="text-2xl font-semibold text-gray-900">
                  Onboard New Tenant
                </Dialog.Title>
                <button
                  onClick={handleClose}
                  className="text-gray-400 hover:text-gray-600"
                  disabled={loading}
                >
                  <XMarkIcon className="h-6 w-6" />
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Tenant ID <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.tenantId}
                    onChange={(e) => setFormData({ ...formData, tenantId: e.target.value })}
                    className="input"
                    placeholder="t-acme"
                    required
                  />
                  <p className="mt-1 text-sm text-gray-500">
                    Lowercase letters, numbers, and hyphens only
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Display Name
                  </label>
                  <input
                    type="text"
                    value={formData.displayName}
                    onChange={(e) => setFormData({ ...formData, displayName: e.target.value })}
                    className="input"
                    placeholder="Acme Corporation"
                  />
                  <p className="mt-1 text-sm text-gray-500">
                    Human-readable name for the tenant
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Deployment Plan <span className="text-red-500">*</span>
                  </label>
                  <div className="space-y-3">
                    <label className="flex items-start p-3 border-2 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
                      <input
                        type="radio"
                        name="plan"
                        value="enterprise"
                        checked={formData.plan === 'enterprise'}
                        onChange={(e) => setFormData({ ...formData, plan: e.target.value as 'enterprise' })}
                        className="mt-0.5 h-4 w-4 text-mongodb-green focus:ring-mongodb-green"
                      />
                      <div className="ml-3 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-900">Enterprise (Ops Manager)</span>
                          <span className="badge badge-green text-xs">Recommended</span>
                        </div>
                        <p className="text-sm text-gray-600 mt-1">
                          Full features including Ops Manager integration, backup, and advanced monitoring
                        </p>
                      </div>
                    </label>

                    <label className="flex items-start p-3 border-2 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
                      <input
                        type="radio"
                        name="plan"
                        value="community"
                        checked={formData.plan === 'community'}
                        onChange={(e) => setFormData({ ...formData, plan: e.target.value as 'community' })}
                        className="mt-0.5 h-4 w-4 text-mongodb-green focus:ring-mongodb-green"
                      />
                      <div className="ml-3 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-900">Community (No Ops Manager)</span>
                          <span className="badge badge-blue text-xs">Open Source</span>
                        </div>
                        <p className="text-sm text-gray-600 mt-1">
                          MongoDB Community binaries. Backup and Ops Manager features not available.
                        </p>
                      </div>
                    </label>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Environment
                  </label>
                  <input
                    type="text"
                    value={formData.environment}
                    onChange={(e) => setFormData({ ...formData, environment: e.target.value })}
                    className="input"
                    placeholder="dev, staging, prod"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Notes
                  </label>
                  <textarea
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    className="input"
                    rows={3}
                    placeholder="Optional notes about this tenant"
                  />
                </div>

                <div className="flex gap-3 justify-end pt-4">
                  <button
                    type="button"
                    onClick={handleClose}
                    disabled={loading}
                    className="btn-secondary"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={loading}
                    className="btn-primary"
                  >
                    {loading ? 'Creating...' : 'Create Tenant'}
                  </button>
                </div>
              </form>
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition>
  );
}
