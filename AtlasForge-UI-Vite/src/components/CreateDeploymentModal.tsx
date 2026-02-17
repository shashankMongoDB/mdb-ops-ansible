import { Fragment, useState, useEffect } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import { deploymentsApi, versionsApi } from '@/lib/api';
import { useToast } from './Toast';
import { validateMembers } from '@/lib/utils';
import type { CreateDeploymentRequest } from '@/lib/types';

interface CreateDeploymentModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  tenantId: string;
  tenantPlan?: 'enterprise' | 'community';
}

export function CreateDeploymentModal({ open, onClose, onSuccess, tenantId, tenantPlan = 'enterprise' }: CreateDeploymentModalProps) {
  const [formData, setFormData] = useState({
    deploymentId: '',
    type: 'ReplicaSet' as 'Standalone' | 'ReplicaSet' | 'ShardedCluster',
    mongoVersion: '8.0.19',
    members: '3',
    displayName: '',
    environment: '',
    // ShardedCluster fields
    shardCount: '2',
    mongodsPerShardCount: '3',
    mongosCount: '2',
    configServerCount: '3',
  });
  const [loading, setLoading] = useState(false);
  const [versions, setVersions] = useState<any>(null);
  const [loadingVersions, setLoadingVersions] = useState(false);
  const { showSuccess, showError, showWarning } = useToast();

  // Load MongoDB versions on mount
  useEffect(() => {
    const loadVersions = async () => {
      setLoadingVersions(true);
      try {
        const data = await versionsApi.getAll();
        setVersions(data);
        
        // Set default version to first "Latest" labeled version for the plan
        if (data && data.length > 0) {
          let defaultVersion = '';
          for (const majorGroup of data) {
            const latestVersion = majorGroup.versions.find((v: any) => 
              v.label === 'Latest' && 
              (tenantPlan === 'enterprise' ? v.version.endsWith('-ent') : !v.version.endsWith('-ent'))
            );
            if (latestVersion) {
              defaultVersion = latestVersion.version;
              break;
            }
          }
          
          // Fallback to first version if no "Latest" found
          if (!defaultVersion && data[0].versions.length > 0) {
            const firstMatchingVersion = data[0].versions.find((v: any) => 
              tenantPlan === 'enterprise' ? v.version.endsWith('-ent') : !v.version.endsWith('-ent')
            );
            if (firstMatchingVersion) {
              defaultVersion = firstMatchingVersion.version;
            }
          }
          
          if (defaultVersion) {
            setFormData(prev => ({ ...prev, mongoVersion: defaultVersion }));
          }
        }
      } catch (error: any) {
        console.error('Failed to load MongoDB versions:', error);
        showError('Failed to load MongoDB versions', error.detail);
      } finally {
        setLoadingVersions(false);
      }
    };
    if (open) {
      loadVersions();
    }
  }, [open, tenantPlan]);

  const membersValidation = formData.type === 'ReplicaSet' ? validateMembers(parseInt(formData.members) || 0) : { valid: true };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate Deployment ID
    if (!formData.deploymentId.trim()) {
      showError('Deployment ID is required');
      return;
    }

    // Validate Deployment ID format (lowercase alphanumeric with hyphens)
    const deploymentIdRegex = /^[a-z0-9-]+$/;
    if (!deploymentIdRegex.test(formData.deploymentId)) {
      showError('Invalid Deployment ID', 'Use lowercase letters, numbers, and hyphens only');
      return;
    }

    // Validate MongoDB Version
    if (!formData.mongoVersion.trim()) {
      showError('MongoDB version is required');
      return;
    }

    // Validate version format (e.g., 8.0.3, 7.0.14-ent)
    const versionRegex = /^\d+\.\d+\.\d+(-ent)?$/;
    if (!versionRegex.test(formData.mongoVersion)) {
      showError('Invalid MongoDB version', 'Use format like 8.0.3 or 7.0.14-ent');
      return;
    }

    // Validate Environment
    if (!formData.environment.trim()) {
      showError('Environment is required');
      return;
    }

    // Validate environment value
    const validEnvironments = ['dev', 'test', 'staging', 'prod'];
    if (!validEnvironments.includes(formData.environment.toLowerCase())) {
      showError('Invalid environment', 'Must be one of: dev, test, staging, prod');
      return;
    }

    // Validate ReplicaSet members
    if (formData.type === 'ReplicaSet' && !membersValidation.valid) {
      showError('Invalid member count', membersValidation.error);
      return;
    }

    // Validate ShardedCluster configuration
    if (formData.type === 'ShardedCluster') {
      const shardCount = parseInt(formData.shardCount);
      const mongodsPerShard = parseInt(formData.mongodsPerShardCount);
      const mongosCount = parseInt(formData.mongosCount);
      const configServerCount = parseInt(formData.configServerCount);

      if (shardCount < 1 || shardCount > 50) {
        showError('Invalid shard count', 'Must be between 1 and 50');
        return;
      }

      if (mongodsPerShard < 3 || mongodsPerShard > 50) {
        showError('Invalid members per shard', 'Must be at least 3');
        return;
      }

      if (mongodsPerShard % 2 === 0) {
        showWarning('Even member count', 'Odd numbers (3, 5, 7) are recommended for proper election');
      }

      if (mongosCount < 1) {
        showError('Invalid mongos count', 'Must be at least 1');
        return;
      }

      if (configServerCount !== 3) {
        showError('Invalid config server count', 'Must be exactly 3 (replica set requirement)');
        return;
      }
    }

    setLoading(true);
    try {
      const request: CreateDeploymentRequest = {
        deploymentId: formData.deploymentId.trim(),
        type: formData.type,
        mongoVersion: formData.mongoVersion.trim(),
        displayName: formData.displayName.trim() || undefined,
        environment: formData.environment.trim() || undefined,
      };

      if (formData.type === 'ReplicaSet') {
        request.members = parseInt(formData.members);
      }

      if (formData.type === 'ShardedCluster') {
        request.shardCount = parseInt(formData.shardCount);
        request.mongodsPerShardCount = parseInt(formData.mongodsPerShardCount);
        request.mongosCount = parseInt(formData.mongosCount);
        request.configServerCount = parseInt(formData.configServerCount);
      }

      await deploymentsApi.create(tenantId, request);
      showSuccess('Deployment created successfully', `Deployment ${formData.deploymentId} is being provisioned`);

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
    setFormData({
      deploymentId: '',
      type: 'ReplicaSet',
      mongoVersion: '8.0.3',
      members: '3',
      displayName: '',
      environment: '',
    });
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
                  Create MongoDB Deployment
                </Dialog.Title>
                <button onClick={handleClose} className="text-gray-400 hover:text-gray-600" disabled={loading}>
                  <XMarkIcon className="h-6 w-6" />
                </button>
              </div>

              {tenantPlan === 'community' ? (
                <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
                  <p className="text-sm text-blue-800">
                    <span className="font-medium">Community Plan:</span> This deployment will use MongoDB Community binaries. 
                    Ops Manager backup and advanced features are not available.
                  </p>
                </div>
              ) : (
                <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-md">
                  <p className="text-sm text-green-800">
                    <span className="font-medium">Enterprise Plan:</span> This deployment will use Enterprise Advanced 
                    with Ops Manager integration, including backup and advanced monitoring.
                  </p>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Deployment ID <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.deploymentId}
                    onChange={(e) => setFormData({ ...formData, deploymentId: e.target.value.toLowerCase() })}
                    className="input"
                    placeholder="rs-orders, sc-analytics"
                    pattern="[a-z0-9-]+"
                    required
                  />
                  <p className="mt-1 text-xs text-gray-500">Lowercase letters, numbers, and hyphens only</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Deployment Type
                  </label>
                  <div className="space-y-2">
                    {/* Enterprise: All types available */}
                    {tenantPlan === 'enterprise' && (
                      <>
                        {(['Standalone', 'ReplicaSet', 'ShardedCluster'] as const).map((type) => (
                          <label key={type} className="flex items-center">
                            <input
                              type="radio"
                              name="type"
                              value={type}
                              checked={formData.type === type}
                              onChange={(e) => setFormData({ ...formData, type: e.target.value as any })}
                              className="mr-2"
                            />
                            <span>{type}</span>
                          </label>
                        ))}
                      </>
                    )}
                    
                    {/* Community: Only ReplicaSet */}
                    {tenantPlan === 'community' && (
                      <>
                        <label className="flex items-center">
                          <input
                            type="radio"
                            name="type"
                            value="ReplicaSet"
                            checked={formData.type === 'ReplicaSet'}
                            onChange={(e) => setFormData({ ...formData, type: 'ReplicaSet' })}
                            className="mr-2"
                          />
                          <span>ReplicaSet</span>
                        </label>
                        <label className="flex items-center opacity-50">
                          <input type="radio" disabled className="mr-2" />
                          <span>Standalone (Not supported for Community)</span>
                        </label>
                        <label className="flex items-center opacity-50">
                          <input type="radio" disabled className="mr-2" />
                          <span>Sharded Cluster (Not supported for Community)</span>
                        </label>
                      </>
                    )}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    MongoDB Version <span className="text-red-500">*</span>
                  </label>
                  {loadingVersions ? (
                    <div className="input bg-gray-50 text-gray-500">Loading versions...</div>
                  ) : (
                    <select
                      value={formData.mongoVersion}
                      onChange={(e) => setFormData({ ...formData, mongoVersion: e.target.value })}
                      className="input"
                      required
                    >
                      <option value="">Select MongoDB version</option>
                      {versions && Array.isArray(versions) && versions.map((majorGroup: any) => {
                        const filteredVersions = majorGroup.versions.filter((versionObj: any) => {
                          // Filter based on plan
                          const isEnterprise = versionObj.version.endsWith('-ent');
                          if (tenantPlan === 'enterprise') return isEnterprise;
                          if (tenantPlan === 'community') return !isEnterprise;
                          return true;
                        });
                        
                        return (
                          <optgroup key={majorGroup.major} label={majorGroup.label || `MongoDB ${majorGroup.major}`}>
                            {filteredVersions.map((versionObj: any) => (
                              <option key={versionObj.version} value={versionObj.version}>
                                {versionObj.version}
                                {versionObj.label && ` (${versionObj.label})`}
                              </option>
                            ))}
                          </optgroup>
                        );
                      })}
                    </select>
                  )}
                  <p className="mt-1 text-xs text-gray-500">
                    {tenantPlan === 'enterprise' 
                      ? 'Enterprise versions only (-ent suffix)' 
                      : 'Community versions available'}
                  </p>
                </div>

                {formData.type === 'ReplicaSet' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Number of Members
                    </label>
                    <input
                      type="number"
                      value={formData.members}
                      onChange={(e) => setFormData({ ...formData, members: e.target.value })}
                      className={`input ${!membersValidation.valid ? 'border-red-500' : ''}`}
                      min="3"
                    />
                    {membersValidation.error && (
                      <p className="mt-1 text-sm text-red-600">{membersValidation.error}</p>
                    )}
                    {membersValidation.warning && (
                      <div className="mt-2 flex items-start gap-2 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                        <ExclamationTriangleIcon className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                        <p className="text-sm text-yellow-800">{membersValidation.warning}</p>
                      </div>
                    )}
                  </div>
                )}

                {formData.type === 'ShardedCluster' && (
                  <div className="space-y-4 p-4 bg-gray-50 rounded-md">
                    <h4 className="text-sm font-medium text-gray-900">Sharded Cluster Configuration</h4>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Number of Shards <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="number"
                          value={formData.shardCount}
                          onChange={(e) => setFormData({ ...formData, shardCount: e.target.value })}
                          className="input"
                          min="1"
                          required
                        />
                        <p className="mt-1 text-xs text-gray-500">Typically 2-10</p>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Members per Shard <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="number"
                          value={formData.mongodsPerShardCount}
                          onChange={(e) => setFormData({ ...formData, mongodsPerShardCount: e.target.value })}
                          className="input"
                          min="3"
                          required
                        />
                        <p className="mt-1 text-xs text-gray-500">Odd numbers: 3, 5, 7</p>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Number of Mongos <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="number"
                          value={formData.mongosCount}
                          onChange={(e) => setFormData({ ...formData, mongosCount: e.target.value })}
                          className="input"
                          min="2"
                          required
                        />
                        <p className="mt-1 text-xs text-gray-500">Query routers: 2+</p>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Config Server Count <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="number"
                          value={formData.configServerCount}
                          onChange={(e) => setFormData({ ...formData, configServerCount: e.target.value })}
                          className="input bg-gray-50"
                          min="3"
                          max="3"
                          required
                          disabled
                        />
                        <p className="mt-1 text-xs text-gray-500">Fixed at 3 (MongoDB replica set requirement)</p>
                      </div>
                    </div>

                    <div className="p-3 bg-blue-50 border border-blue-200 rounded-md">
                      <p className="text-xs text-blue-800">
                        <strong>Total pods:</strong> {parseInt(formData.shardCount || '0') * parseInt(formData.mongodsPerShardCount || '0') + parseInt(formData.mongosCount || '0') + parseInt(formData.configServerCount || '0')}
                        ({formData.shardCount} shards × {formData.mongodsPerShardCount} members + {formData.mongosCount} mongos + {formData.configServerCount} config servers)
                      </p>
                    </div>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Display Name</label>
                  <input
                    type="text"
                    value={formData.displayName}
                    onChange={(e) => setFormData({ ...formData, displayName: e.target.value })}
                    className="input"
                    placeholder="Orders Database"
                  />
                  <p className="mt-1 text-xs text-gray-500">Optional: Friendly name for this deployment</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Environment <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={formData.environment}
                    onChange={(e) => setFormData({ ...formData, environment: e.target.value })}
                    className="input"
                    required
                  >
                    <option value="">Select environment</option>
                    <option value="dev">Development</option>
                    <option value="test">Test</option>
                    <option value="staging">Staging</option>
                    <option value="prod">Production</option>
                  </select>
                  <p className="mt-1 text-xs text-gray-500">Choose the environment for this deployment</p>
                </div>

                <div className="flex gap-3 justify-end pt-4">
                  <button type="button" onClick={handleClose} disabled={loading} className="btn-secondary">
                    Cancel
                  </button>
                  <button type="submit" disabled={loading || !membersValidation.valid} className="btn-primary">
                    {loading ? 'Creating...' : 'Create Deployment'}
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
