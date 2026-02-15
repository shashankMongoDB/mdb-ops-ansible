import { Fragment, useState } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { ExclamationTriangleIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { atlasForgeApi } from '../lib/api';
import { useToast } from '../lib/hooks';

interface RestoreBackupModalProps {
  isOpen: boolean;
  onClose: () => void;
  tenantId: string;
  deploymentId: string;
  snapshot: {
    filename: string;
    timestamp: string;
    sizeFormatted: string;
  };
  onRestoreStarted: () => void;
}

export function RestoreBackupModal({
  isOpen,
  onClose,
  tenantId,
  deploymentId,
  snapshot,
  onRestoreStarted
}: RestoreBackupModalProps) {
  const [loading, setLoading] = useState(false);
  const [dropExisting, setDropExisting] = useState(true);
  const { showSuccess, showError } = useToast();

  const handleRestore = async () => {
    if (!snapshot) return;

    setLoading(true);
    try {
      const result = await atlasForgeApi.restoreCommunityBackup(tenantId, deploymentId, {
        snapshotFilename: snapshot.filename,
        dropExisting: dropExisting
      });

      showSuccess('Restore job started successfully!');
      onRestoreStarted();
      onClose();
    } catch (error: any) {
      showError(error.message || 'Failed to start restore');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Transition.Root show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </Transition.Child>

        <div className="fixed inset-0 z-10 overflow-y-auto">
          <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <Dialog.Panel className="relative transform overflow-hidden rounded-lg bg-white px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6">
                <div className="absolute right-0 top-0 hidden pr-4 pt-4 sm:block">
                  <button
                    type="button"
                    className="rounded-md bg-white text-gray-400 hover:text-gray-500"
                    onClick={onClose}
                  >
                    <XMarkIcon className="h-6 w-6" />
                  </button>
                </div>

                <div className="sm:flex sm:items-start">
                  <div className="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-red-100 sm:mx-0 sm:h-10 sm:w-10">
                    <ExclamationTriangleIcon className="h-6 w-6 text-red-600" />
                  </div>
                  <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left">
                    <Dialog.Title as="h3" className="text-lg font-semibold leading-6 text-gray-900">
                      Restore Backup
                    </Dialog.Title>
                    <div className="mt-4 space-y-3">
                      {/* Warning */}
                      <div className="bg-red-50 border border-red-200 rounded-md p-3">
                        <p className="text-sm text-red-800 font-semibold">
                          ⚠️ Warning: This is a destructive operation
                        </p>
                        <p className="text-xs text-red-700 mt-1">
                          This will restore your MongoDB database from the selected snapshot. 
                          {dropExisting && ' All existing data will be replaced.'}
                        </p>
                      </div>

                      {/* Snapshot Info */}
                      <div className="bg-gray-50 rounded-md p-3">
                        <h4 className="text-sm font-semibold text-gray-900 mb-2">Snapshot Details</h4>
                        <div className="text-xs text-gray-600 space-y-1">
                          <div><span className="font-medium">File:</span> {snapshot?.filename}</div>
                          <div><span className="font-medium">Timestamp:</span> {snapshot?.timestamp}</div>
                          <div><span className="font-medium">Size:</span> {snapshot?.sizeFormatted}</div>
                        </div>
                      </div>

                      {/* Options */}
                      <div className="flex items-start">
                        <input
                          id="dropExisting"
                          type="checkbox"
                          checked={dropExisting}
                          onChange={(e) => setDropExisting(e.target.checked)}
                          className="h-4 w-4 rounded border-gray-300 text-mongodb-green focus:ring-mongodb-green mt-0.5"
                        />
                        <label htmlFor="dropExisting" className="ml-2 text-sm text-gray-700">
                          <span className="font-medium">Drop existing collections before restore</span>
                          <p className="text-xs text-gray-500 mt-1">
                            Recommended: Ensures a clean restore without conflicts
                          </p>
                        </label>
                      </div>

                      {/* What Happens */}
                      <div className="text-xs text-gray-600 space-y-1">
                        <p className="font-semibold">What will happen:</p>
                        <ol className="list-decimal list-inside space-y-1 ml-2">
                          <li>A Kubernetes restore job will be created</li>
                          <li>The snapshot will be downloaded from storage</li>
                          <li>{dropExisting ? 'Existing collections will be dropped' : 'Data will be merged with existing collections'}</li>
                          <li>mongorestore will import all data</li>
                          <li>Your application may experience brief downtime</li>
                        </ol>
                      </div>

                      {/* Recommendation */}
                      <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
                        <p className="text-xs text-blue-700">
                          <strong>💡 Recommendation:</strong> Create a fresh backup before restoring to have a rollback option.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse gap-2">
                  <button
                    type="button"
                    disabled={loading}
                    onClick={handleRestore}
                    className="inline-flex w-full justify-center rounded-md bg-red-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-red-500 disabled:opacity-50 disabled:cursor-not-allowed sm:w-auto"
                  >
                    {loading ? 'Starting Restore...' : 'Restore Backup'}
                  </button>
                  <button
                    type="button"
                    disabled={loading}
                    onClick={onClose}
                    className="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed sm:mt-0 sm:w-auto"
                  >
                    Cancel
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  );
}
