import { Fragment, useState, useEffect } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon, ExclamationTriangleIcon, InformationCircleIcon, CheckCircleIcon } from '@heroicons/react/24/outline';
import { deploymentsApi } from '@/lib/api';
import { useToast } from './Toast';
import { isDowngrade } from '@/lib/utils';
import { useUpgradePolling } from '@/hooks/useUpgradePolling';
import { UpgradeProgressView } from './UpgradeProgressView';

interface UpgradeVersionModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  tenantId: string;
  deploymentId: string;
  currentVersion: string;
  tenantPlan?: string;
}

export function UpgradeVersionModal({
  open,
  onClose,
  onSuccess,
  tenantId,
  deploymentId,
  currentVersion,
  tenantPlan = 'enterprise',
}: UpgradeVersionModalProps) {
  const [mongoVersion, setMongoVersion] = useState('');
  const [versions, setVersions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingVersions, setLoadingVersions] = useState(false);
  const [upgradeState, setUpgradeState] = useState<'idle' | 'upgrading' | 'complete'>('idle');
  const { showSuccess, showError } = useToast();

  const isDowngradeAttempt = mongoVersion.trim() && isDowngrade(currentVersion, mongoVersion.trim());

  // Upgrade polling hook
  const { progress, isPolling, startPolling, stopPolling } = useUpgradePolling({
    tenantId,
    deploymentId,
    targetVersion: mongoVersion,
    enabled: upgradeState === 'upgrading',
    onComplete: () => {
      setUpgradeState('complete');
      showSuccess('Upgrade complete!', `All replicas upgraded to ${mongoVersion}`);
    },
    onError: (error) => {
      showError('Upgrade monitoring delayed', error);
    },
  });

  // Load available versions
  useEffect(() => {
    const loadVersions = async () => {
      console.log('[UpgradeVersionModal] Loading versions...');
      setLoadingVersions(true);
      try {
        const data = await deploymentsApi.getMongoDBVersions();
        console.log('[UpgradeVersionModal] Versions loaded:', data);
        setVersions(data);
      } catch (error) {
        console.error('[UpgradeVersionModal] Failed to load MongoDB versions:', error);
      } finally {
        setLoadingVersions(false);
      }
    };

    if (open) {
      loadVersions();
    }
  }, [open]);

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
      // Initiate upgrade
      await deploymentsApi.upgradeVersion(tenantId, deploymentId, newVersion);
      
      // Switch to upgrading state
      setUpgradeState('upgrading');
      showSuccess('Version upgrade initiated', `Upgrading to ${newVersion}...`);
      
      // Start polling for progress
      startPolling();
    } catch (error: any) {
      const message = error.detail || 'An error occurred';
      showError('Failed to start upgrade', message);
      setUpgradeState('idle');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (upgradeState === 'upgrading') {
      // Allow closing modal but keep monitoring in background
      showSuccess('Upgrade continues', 'Check deployment page for progress');
    }
    
    // Reset state
    setUpgradeState('idle');
    setMongoVersion('');
    stopPolling();
    
    onClose();
    onSuccess(); // Refresh deployment page
  };

  const handleDone = () => {
    setUpgradeState('idle');
    setMongoVersion('');
    stopPolling();
    onClose();
    onSuccess();
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
            <Dialog.Panel className={`w-full rounded-lg bg-white p-6 shadow-xl ${upgradeState === 'idle' ? 'max-w-md' : 'max-w-2xl'}`}>
              <div className="flex items-center justify-between mb-6">
                <Dialog.Title className="text-2xl font-semibold text-gray-900">
                  {upgradeState === 'idle' && 'Upgrade MongoDB Version'}
                  {upgradeState === 'upgrading' && 'Upgrading MongoDB Version'}
                  {upgradeState === 'complete' && 'Upgrade Complete'}
                </Dialog.Title>
                <button 
                  onClick={handleClose} 
                  className="text-gray-400 hover:text-gray-600" 
                  disabled={loading && upgradeState === 'idle'}
                >
                  <XMarkIcon className="h-6 w-6" />
                </button>
              </div>

              {/* Idle State - Show Form */}
              {upgradeState === 'idle' && (
                <>
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
                  <select
                    value={mongoVersion}
                    onChange={(e) => setMongoVersion(e.target.value)}
                    className={`input ${isDowngradeAttempt ? 'border-red-500' : ''}`}
                    disabled={loadingVersions}
                  >
                    <option value="">Select a version to upgrade to...</option>
                    {versions.length > 0 ? (
                      versions.map((versionGroup) => (
                        <optgroup key={versionGroup.major} label={versionGroup.label}>
                          {versionGroup.versions
                            .filter((v: any) => {
                              // Filter based on tenant plan
                              if (tenantPlan === 'community') {
                                return !v.version.includes('-ent');
                              } else {
                                return v.version.includes('-ent');
                              }
                            })
                            .map((v: any) => (
                              <option key={v.version} value={v.version}>
                                {v.version} {v.label ? `(${v.label})` : ''}
                              </option>
                            ))}
                        </optgroup>
                      ))
                    ) : !loadingVersions ? (
                      <option disabled>No versions available</option>
                    ) : null}
                  </select>
                  <p className="mt-1 text-sm text-gray-500">
                    {loadingVersions ? 'Loading versions...' : 'Select a version higher than current'}
                  </p>
                  {isDowngradeAttempt && <p className="mt-1 text-sm text-red-600">⚠️ Downgrade not allowed</p>}
                </div>

                    <div className="flex gap-3 justify-end pt-4">
                      <button type="button" onClick={handleClose} disabled={loading} className="btn-secondary">
                        Cancel
                      </button>
                      <button type="submit" disabled={loading || isDowngradeAttempt} className="btn-primary">
                        {loading ? 'Starting Upgrade...' : 'Upgrade Version'}
                      </button>
                    </div>
                  </form>
                </>
              )}

              {/* Upgrading State - Show Progress */}
              {upgradeState === 'upgrading' && progress && (
                <>
                  <UpgradeProgressView
                    fromVersion={progress.fromVersion}
                    toVersion={progress.toVersion}
                    currentReplica={progress.currentReplica}
                    totalReplicas={progress.totalReplicas}
                    percentage={progress.percentage}
                    replicas={progress.replicas}
                    estimatedTimeRemaining={progress.estimatedTimeRemaining || undefined}
                    startTime={progress.startTime}
                  />
                  
                  <div className="flex gap-3 justify-end pt-6 mt-6 border-t">
                    <button 
                      type="button" 
                      onClick={handleClose} 
                      className="btn-secondary"
                    >
                      Close (continues in background)
                    </button>
                  </div>
                </>
              )}

              {/* Complete State - Show Success */}
              {upgradeState === 'complete' && progress && (
                <>
                  <div className="mb-6 p-4 bg-green-50 border-l-4 border-green-500 rounded">
                    <div className="flex items-center gap-3">
                      <CheckCircleIcon className="h-8 w-8 text-green-600" />
                      <div>
                        <h3 className="font-medium text-green-900">Successfully upgraded to {progress.toVersion}</h3>
                        <p className="mt-1 text-sm text-green-700">
                          All {progress.totalReplicas} replicas are now running the new version.
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Show final replica status */}
                  <div className="border border-gray-200 rounded-lg overflow-hidden mb-6">
                    <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
                      <h4 className="text-sm font-medium text-gray-900">Final Replica Status</h4>
                    </div>
                    <div className="divide-y divide-gray-200">
                      {progress.replicas.map((replica, index) => (
                        <div
                          key={replica.name || index}
                          className="px-4 py-3 flex items-center justify-between bg-green-50"
                        >
                          <div className="flex items-center gap-3">
                            <CheckCircleIcon className="h-5 w-5 text-green-600" />
                            <div>
                              <div className="font-medium text-sm">{replica.name}</div>
                              <div className="text-xs text-gray-600">Running</div>
                            </div>
                          </div>
                          <div className="text-sm font-mono text-green-700">{replica.version}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="flex justify-end">
                    <button 
                      type="button" 
                      onClick={handleDone} 
                      className="btn-primary"
                    >
                      Done
                    </button>
                  </div>
                </>
              )}
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition>
  );
}
