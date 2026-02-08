import { Fragment, useState } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon, ExclamationTriangleIcon, InformationCircleIcon } from '@heroicons/react/24/outline';
import { deploymentsApi } from '@/lib/api';
import { useToast } from './Toast';
import { validateMembers } from '@/lib/utils';

interface ScaleModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  tenantId: string;
  deploymentId: string;
  currentMembers: number;
}

export function ScaleModal({ open, onClose, onSuccess, tenantId, deploymentId, currentMembers }: ScaleModalProps) {
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
      await deploymentsApi.scale(tenantId, deploymentId, newMembers);
      showSuccess('Scaling initiated', `Deployment is scaling to ${newMembers} members`);

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
    <Transition show={open} as={Fragment}>
      <Dialog onClose={onClose} className="relative z-50">
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
            <Dialog.Panel className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
              <div className="flex items-center justify-between mb-6">
                <Dialog.Title className="text-2xl font-semibold text-gray-900">
                  Scale Deployment
                </Dialog.Title>
                <button onClick={onClose} className="text-gray-400 hover:text-gray-600" disabled={loading}>
                  <XMarkIcon className="h-6 w-6" />
                </button>
              </div>

              <div className="mb-4 flex items-start gap-2 p-3 bg-blue-50 border border-blue-200 rounded-md">
                <InformationCircleIcon className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-blue-800">Current members: {currentMembers}</p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    New Member Count
                  </label>
                  <input
                    type="number"
                    value={members}
                    onChange={(e) => setMembers(e.target.value)}
                    className={`input ${!membersValidation.valid ? 'border-red-500' : ''}`}
                    min="3"
                  />
                  <p className="mt-1 text-sm text-gray-500">Recommended: odd number ≥ 3</p>
                  {membersValidation.error && (
                    <p className="mt-1 text-sm text-red-600">{membersValidation.error}</p>
                  )}
                </div>

                {membersValidation.warning && (
                  <div className="flex items-start gap-2 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                    <ExclamationTriangleIcon className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-yellow-800">{membersValidation.warning}</p>
                  </div>
                )}

                <div className="flex gap-3 justify-end pt-4">
                  <button type="button" onClick={onClose} disabled={loading} className="btn-secondary">
                    Cancel
                  </button>
                  <button type="submit" disabled={loading || !membersValidation.valid} className="btn-primary">
                    {loading ? 'Scaling...' : 'Scale Deployment'}
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
