import { Fragment, useState } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon, ExclamationTriangleIcon, InformationCircleIcon } from '@heroicons/react/24/outline';
import { deploymentsApi } from '@/lib/api';
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
      showError('Downgrade not allowed', 'You cannot downgrade to an older MongoDB version');
      return;
    }

    setLoading(true);
    try {
      await deploymentsApi.upgradeVersion(tenantId, deploymentId, newVersion);
      showSuccess('Version upgrade initiated', `Deployment is upgrading to ${newVersion}`);
      onClose();
      onSuccess();
    } catch (error: any) {
      showError('Failed to upgrade version', error.detail || 'An error occurred');
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
                  Upgrade MongoDB Version
                </Dialog.Title>
                <button onClick={onClose} className="text-gray-400 hover:text-gray-600" disabled={loading}>
                  <XMarkIcon className="h-6 w-6" />
                </button>
              </div>

              <div className="mb-4 flex items-start gap-2 p-3 bg-blue-50 border border-blue-200 rounded-md">
                <InformationCircleIcon className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-blue-800">Current version: {currentVersion}</p>
              </div>

              {isDowngradeAttempt && (
                <div className="mb-4 flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-md">
                  <ExclamationTriangleIcon className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-800">Downgrade detected! Downgrades are not allowed.</p>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    New MongoDB Version
                  </label>
                  <input
                    type="text"
                    value={mongoVersion}
                    onChange={(e) => setMongoVersion(e.target.value)}
                    className={`input ${isDowngradeAttempt ? 'border-red-500' : ''}`}
                    placeholder="8.0.17-ent, 7.0.14"
                  />
                  <p className="mt-1 text-sm text-gray-500">Must be higher than current version</p>
                  {isDowngradeAttempt && <p className="mt-1 text-sm text-red-600">Downgrade not allowed</p>}
                </div>

                <div className="flex gap-3 justify-end pt-4">
                  <button type="button" onClick={onClose} disabled={loading} className="btn-secondary">
                    Cancel
                  </button>
                  <button type="submit" disabled={loading || isDowngradeAttempt} className="btn-primary">
                    {loading ? 'Upgrading...' : 'Upgrade Version'}
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
