import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronDownIcon, ChevronRightIcon } from '@heroicons/react/24/outline';
import { deploymentStatusApi, deploymentsApi } from '@/lib/api';
import { useToast } from './Toast';
import type { Deployment } from '@/lib/types';

interface DeploymentStatus {
  deploymentId: string;
  type: string;
  status: 'running' | 'pending' | 'partial' | 'shutdown' | 'error';
  phase: string;
  operation?: 'running' | 'upgrading' | 'scaling' | 'stabilizing' | 'pending' | 'failed';
  progress?: number;
  operationMessage?: string;
  readyReplicas: number;
  totalReplicas: number;
  topology?: any;
  pods?: any[];
  lastUpdated: string;
}

interface Props {
  tenantId: string;
  deployments: Deployment[];
  tenantPlan: 'enterprise' | 'community';
}

export function ExpandableDeploymentList({ tenantId, deployments, tenantPlan }: Props) {
  const [expandedDeployments, setExpandedDeployments] = useState<Set<string>>(new Set());
  const [deploymentStatuses, setDeploymentStatuses] = useState<Map<string, DeploymentStatus>>(new Map());
  const [loading, setLoading] = useState(false);
  const [startingDeployment, setStartingDeployment] = useState<string | null>(null);
  const navigate = useNavigate();
  const { showSuccess, showError } = useToast();

  // Poll for status updates every 10 seconds
  useEffect(() => {
    loadAllStatuses();
    
    const interval = setInterval(() => {
      loadAllStatuses();
    }, 10000); // Poll every 10 seconds

    return () => clearInterval(interval);
  }, [tenantId, deployments]);

  const loadAllStatuses = async () => {
    try {
      setLoading(true);
      const response = await deploymentStatusApi.getAllStatus(tenantId);
      
      const statusMap = new Map<string, DeploymentStatus>();
      response.deployments.forEach((status: DeploymentStatus) => {
        statusMap.set(status.deploymentId, status);
      });
      
      setDeploymentStatuses(statusMap);
    } catch (error) {
      console.error('Failed to load deployment statuses:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = (deploymentId: string) => {
    const newExpanded = new Set(expandedDeployments);
    if (newExpanded.has(deploymentId)) {
      newExpanded.delete(deploymentId);
    } else {
      newExpanded.add(deploymentId);
    }
    setExpandedDeployments(newExpanded);
  };

  const handleStartDeployment = async (deploymentId: string) => {
    setStartingDeployment(deploymentId);
    try {
      await deploymentsApi.start(tenantId, deploymentId);
      showSuccess('Deployment starting', `Deployment ${deploymentId} is starting up`);
      // Immediately refresh statuses
      await loadAllStatuses();
    } catch (error: any) {
      showError('Failed to start deployment', error.detail || 'An error occurred');
    } finally {
      setStartingDeployment(null);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'text-green-600';
      case 'pending':
      case 'partial':
        return 'text-yellow-600';
      case 'shutdown':
        return 'text-gray-600';
      case 'error':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return '●';
      case 'pending':
      case 'partial':
        return '◐';
      case 'shutdown':
        return '○';
      case 'error':
        return '✗';
      default:
        return '○';
    }
  };

  return (
    <div className="space-y-2">
      {deployments.map((deployment) => {
        const isExpanded = expandedDeployments.has(deployment.deploymentId);
        const status = deploymentStatuses.get(deployment.deploymentId);
        const isInitialCreate = !!(status && deployment.status === 'pending' && status.readyReplicas === 0);
        const statusColor = status ? getStatusColor(status.status) : 'text-gray-600';
        const statusIcon = status ? getStatusIcon(status.status) : '○';

        return (
          <div key={deployment.deploymentId} className="border border-gray-200 rounded-lg overflow-hidden">
            {/* Main row - always visible */}
            <div className="bg-white hover:bg-gray-50 transition-colors">
              <div className="flex items-center gap-4 p-4">
                {/* Expand/Collapse button */}
                <button
                  onClick={() => toggleExpand(deployment.deploymentId)}
                  className="flex-shrink-0 p-1 hover:bg-gray-200 rounded"
                >
                  {isExpanded ? (
                    <ChevronDownIcon className="h-5 w-5 text-gray-600" />
                  ) : (
                    <ChevronRightIcon className="h-5 w-5 text-gray-600" />
                  )}
                </button>

                {/* Status indicator */}
                <div className={`text-2xl ${statusColor}`} title={status?.phase || 'Unknown'}>
                  {statusIcon}
                </div>

                {/* Deployment name and info */}
                <div className="flex-1 min-w-0">
                  <button
                    onClick={() => {
                      // Block only for initial creation state, not scale/upgrade operations
                      if (!isInitialCreate) {
                        navigate(`/tenants/${tenantId}/deployments/${deployment.deploymentId}`);
                      } else {
                        // Just toggle expand to show status
                        toggleExpand(deployment.deploymentId);
                      }
                    }}
                    className={`font-medium transition-colors text-left ${
                      !isInitialCreate
                        ? 'text-mongodb-forest hover:text-mongodb-green cursor-pointer'
                        : 'text-gray-600 cursor-default'
                    }`}
                    title={isInitialCreate ? 'Details available when first replica is ready' : ''}
                  >
                    {deployment.displayName || deployment.deploymentId}
                  </button>
                  <div className="text-sm text-gray-500 flex items-center gap-3 mt-1">
                    <span className="font-mono text-xs">{deployment.deploymentId}</span>
                    <span>•</span>
                    <span>{deployment.type}</span>
                    {deployment.type === 'ShardedCluster' && (
                      <>
                        <span>•</span>
                        <span>{deployment.shardCount || 2} Shards</span>
                        <span>•</span>
                        <span>{deployment.mongosCount || 2} Mongos</span>
                      </>
                    )}
                    {deployment.type === 'ReplicaSet' && (
                      <>
                        <span>•</span>
                        <span>{deployment.members || 3} Members</span>
                      </>
                    )}
                  </div>
                </div>

                {/* Status summary */}
                <div className="flex items-center gap-6 text-sm">
                  <div className="text-center">
                    <div className="text-gray-500 text-xs">Status</div>
                    <div className={`font-medium ${statusColor}`}>
                      {status?.phase || 'Unknown'}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-gray-500 text-xs">Replicas</div>
                    <div className="font-medium">
                      {status ? `${status.readyReplicas}/${status.totalReplicas}` : '-'}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-gray-500 text-xs">Version</div>
                    <div className="font-medium text-gray-700">
                      {deployment.mongoVersion}
                    </div>
                  </div>
                  <div className="text-center min-w-[80px]">
                    <div className="text-gray-500 text-xs mb-1">Monitoring</div>
                    <div>
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                        Enabled
                      </span>
                    </div>
                  </div>
                </div>

                {/* Actions - Conditional based on status */}
                <div className="flex gap-2">
                  {status?.status === 'shutdown' ? (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleStartDeployment(deployment.deploymentId);
                      }}
                      disabled={startingDeployment === deployment.deploymentId}
                      className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {startingDeployment === deployment.deploymentId ? 'Starting...' : 'Start'}
                    </button>
                  ) : isInitialCreate ? (
                    // Brand new deployment with 0 replicas and pending status - block access
                    <button
                      disabled
                      className="px-3 py-1 text-sm border border-gray-300 text-gray-400 rounded cursor-not-allowed"
                      title="Details available when first replica is ready"
                    >
                      Details
                    </button>
                  ) : (
                    // All other cases - allow access (including during scale operations)
                    <button
                      onClick={() => navigate(`/tenants/${tenantId}/deployments/${deployment.deploymentId}`)}
                      className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-100"
                    >
                      Details
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Expanded section - topology details */}
            {isExpanded && status && (
              <div className="bg-gray-50 border-t border-gray-200 p-4">
                <DeploymentTopology deployment={deployment} status={status} tenantPlan={tenantPlan} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// Topology component for expanded view
function DeploymentTopology({ deployment, status, tenantPlan }: { deployment: Deployment; status: DeploymentStatus; tenantPlan: string }) {
  // Calculate progress percentage
  const progressPercent = typeof status.progress === 'number'
    ? status.progress
    : status.totalReplicas > 0
    ? Math.round((status.readyReplicas / status.totalReplicas) * 100)
    : 0;

  if (status.status === 'shutdown') {
    return (
      <div className="text-gray-500 text-sm">
        Deployment is currently shutdown. No topology information available.
      </div>
    );
  }

  const activeOperation = status.operation && status.operation !== 'running';

  // Show progress view for create/scale/upgrade operations
  if (status.status === 'pending' || status.status === 'partial' || activeOperation) {
    const isInitialCreate = deployment.status === 'pending';
    // Determine status message
    const statusMessage = isInitialCreate && status.operation === 'scaling'
      ? 'Creating Members...'
      : status.operation === 'upgrading'
      ? 'Upgrading Version...'
      : status.operation === 'scaling'
      ? 'Scaling Members...'
      : status.readyReplicas === 0 
      ? 'Starting Up...'
      : status.readyReplicas === 1
      ? 'Initializing...'
      : 'Stabilizing...';
    
    const detailMessage = (isInitialCreate && status.operation === 'scaling')
      ? `Creating members (${status.readyReplicas}/${status.totalReplicas} ready)`
      : status.operationMessage || (status.readyReplicas === 0
      ? 'Waiting for first replica to start'
      : status.readyReplicas === 1
      ? 'First replica running. Detail page accessible with limited features.'
      : 'Multiple replicas running. Waiting for full cluster.');
    
    return (
      <div className="space-y-4">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center gap-3 mb-3">
            <div className="animate-spin">
              <svg className="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>
            <div>
              <h3 className="font-semibold text-blue-900">{statusMessage}</h3>
              <p className="text-sm text-blue-700">Replicas: {status.readyReplicas}/{status.totalReplicas} ready</p>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="mb-3">
            <div className="flex justify-between text-xs text-blue-700 mb-1">
              <span>Progress</span>
              <span>{progressPercent}%</span>
            </div>
            <div className="w-full bg-blue-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                style={{ width: `${progressPercent}%` }}
              ></div>
            </div>
          </div>

          <p className="text-xs text-blue-600">
            {detailMessage}
          </p>
        </div>

        {/* Replica Status List */}
        <div>
          <h4 className="font-medium text-gray-700 mb-2">Replica Status</h4>
          <div className="space-y-2">
            {status.pods && status.pods.length > 0 ? (
              status.pods.map((pod: any, index: number) => (
                <div key={pod.name} className="flex items-center justify-between bg-white border border-gray-200 rounded p-2">
                  <div className="flex items-center gap-3">
                    <span className={`text-lg ${pod.ready ? 'text-green-600' : 'text-yellow-600'}`}>
                      {pod.ready ? '●' : '◐'}
                    </span>
                    <span className="font-mono text-sm">{pod.name} <span className="text-xs text-gray-500">(Replica {index})</span></span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-2 py-1 rounded ${
                      pod.status === 'Running' ? 'bg-green-100 text-green-800' :
                      pod.status === 'Pending' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {pod.status}
                    </span>
                    {!pod.ready && (
                      <span className="text-xs text-gray-500">⏳</span>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-gray-500">Loading replica information...</p>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (deployment.type === 'ShardedCluster' && status.topology?.shards) {
    return (
      <div className="space-y-4">
        {/* Shards */}
        <div>
          <h4 className="font-medium text-gray-700 mb-2">Shards</h4>
          <div className="space-y-2">
            {status.topology.shards.map((shard: any, idx: number) => (
              <div key={idx} className="bg-white border border-gray-200 rounded p-3">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-medium text-sm">Shard {idx}</span>
                  <span className="text-xs text-gray-500">
                    {shard.readyMembers}/{shard.totalMembers} ready
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {shard.members.map((pod: any) => (
                    <div key={pod.name} className="text-xs">
                      <div className="flex items-center gap-2">
                        <span className={pod.ready ? 'text-green-600' : 'text-gray-400'}>
                          {pod.ready ? '●' : '○'}
                        </span>
                        <span className="font-mono truncate">{pod.name}</span>
                      </div>
                      <div className="ml-5 text-gray-500">{pod.status}</div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Config Servers */}
        {status.topology.configServers && (
          <div>
            <h4 className="font-medium text-gray-700 mb-2">Config Servers</h4>
            <div className="bg-white border border-gray-200 rounded p-3">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm">Config Server Replica Set</span>
                <span className="text-xs text-gray-500">
                  {status.topology.configServers.readyMembers}/{status.topology.configServers.totalMembers} ready
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                {status.topology.configServers.members.map((pod: any) => (
                  <div key={pod.name} className="text-xs">
                    <div className="flex items-center gap-2">
                      <span className={pod.ready ? 'text-green-600' : 'text-gray-400'}>
                        {pod.ready ? '●' : '○'}
                      </span>
                      <span className="font-mono truncate">{pod.name}</span>
                    </div>
                    <div className="ml-5 text-gray-500">{pod.status}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Mongos */}
        {status.topology.mongos && (
          <div>
            <h4 className="font-medium text-gray-700 mb-2">Mongos Routers</h4>
            <div className="bg-white border border-gray-200 rounded p-3">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm">Query Routers</span>
                <span className="text-xs text-gray-500">
                  {status.topology.mongos.readyInstances}/{status.topology.mongos.totalInstances} ready
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                {status.topology.mongos.instances.map((pod: any) => (
                  <div key={pod.name} className="text-xs">
                    <div className="flex items-center gap-2">
                      <span className={pod.ready ? 'text-green-600' : 'text-gray-400'}>
                        {pod.ready ? '●' : '○'}
                      </span>
                      <span className="font-mono truncate">{pod.name}</span>
                    </div>
                    <div className="ml-5 text-gray-500">{pod.status}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  if (deployment.type === 'ReplicaSet' && status.topology?.replicaSet) {
    return (
      <div>
        <h4 className="font-medium text-gray-700 mb-2">Replica Set Members</h4>
        <div className="bg-white border border-gray-200 rounded p-3">
          <div className="grid grid-cols-3 gap-2">
            {status.topology.replicaSet.members.map((pod: any) => (
              <div key={pod.name} className="text-xs">
                <div className="flex items-center gap-2">
                  <span className={pod.ready ? 'text-green-600' : 'text-gray-400'}>
                    {pod.ready ? '●' : '○'}
                  </span>
                  <span className="font-mono truncate">{pod.name}</span>
                </div>
                <div className="ml-5 text-gray-500">{pod.status}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (deployment.type === 'Standalone' && status.pods) {
    return (
      <div>
        <h4 className="font-medium text-gray-700 mb-2">Standalone Instance</h4>
        <div className="bg-white border border-gray-200 rounded p-3">
          {status.pods.map((pod: any) => (
            <div key={pod.name} className="text-sm">
              <div className="flex items-center gap-2">
                <span className={pod.ready ? 'text-green-600' : 'text-gray-400'}>
                  {pod.ready ? '●' : '○'}
                </span>
                <span className="font-mono">{pod.name}</span>
                <span className="text-gray-500">- {pod.status}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return null;
}
