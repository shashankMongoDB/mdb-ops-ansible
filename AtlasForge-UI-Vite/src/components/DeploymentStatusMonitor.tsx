import { useEffect, useState } from 'react';
import { deploymentsApi } from '@/lib/api';

interface Replica {
  name: string;
  version: string;
  status: string;
  ready: boolean;
}

interface StatusData {
  operation: 'running' | 'upgrading' | 'scaling' | 'stabilizing' | 'restarting' | 'starting' | 'pending' | 'failed';
  progress: number;
  operationMessage: string;
  targetVersion: string;
  targetReplicas: number;
  currentVersion: string;
  currentReplicas: number;
  readyReplicas: number;
  totalReplicas: number;
  replicas: Replica[];
  crPhase?: string;
  crMessage?: string;
  crActualVersion?: string;
}

interface Props {
  tenantId: string;
  deploymentId: string;
  onStatusChange?: (status: StatusData) => void;
  compact?: boolean;
}

export function DeploymentStatusMonitor({ tenantId, deploymentId, onStatusChange, compact = false }: Props) {
  const [status, setStatus] = useState<StatusData | null>(null);

  useEffect(() => {
    let timeoutId: NodeJS.Timeout;
    let isMounted = true;

    const pollStatus = async () => {
      try {
        const info = await deploymentsApi.getConnectionInfo(tenantId, deploymentId);
        if (isMounted) {
          const statusData: StatusData = {
            operation: info.operation || 'running',
            progress: info.progress || 0,
            operationMessage: info.operationMessage || '',
            targetVersion: info.targetVersion || '',
            targetReplicas: info.targetReplicas || 0,
            currentVersion: info.currentVersion || '',
            currentReplicas: info.currentReplicas || 0,
            readyReplicas: info.readyReplicas || 0,
            totalReplicas: info.totalReplicas || 0,
            replicas: info.replicas || [],
            crPhase: info.crPhase,
            crMessage: info.crMessage,
            crActualVersion: info.crActualVersion
          };
          
          setStatus(statusData);
          
          if (onStatusChange) {
            onStatusChange(statusData);
          }
          
          // Adjust polling frequency based on operation
          const pollInterval = statusData.operation === 'running' ? 30000 : 5000;
          timeoutId = setTimeout(pollStatus, pollInterval);
        }
      } catch (error) {
        console.error('Failed to poll deployment status:', error);
        // Retry after 10 seconds on error
        timeoutId = setTimeout(pollStatus, 10000);
      }
    };

    pollStatus();

    return () => {
      isMounted = false;
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [tenantId, deploymentId, onStatusChange]);

  if (!status) {
    return null;
  }

  const getOperationColor = () => {
    switch (status.operation) {
      case 'running':
        return 'text-green-600';
      case 'upgrading':
        return 'text-blue-600';
      case 'scaling':
        return 'text-yellow-600';
      case 'stabilizing':
        return 'text-orange-600';
      case 'restarting':
        return 'text-blue-600';
      case 'starting':
        return 'text-blue-600';
      case 'pending':
        return 'text-yellow-600';
      case 'failed':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getOperationIcon = () => {
    switch (status.operation) {
      case 'running':
        return '✅';
      case 'upgrading':
        return '⏳';
      case 'scaling':
        return '📊';
      case 'stabilizing':
        return '🔄';
      case 'restarting':
        return '🔄';
      case 'starting':
        return '⏳';
      case 'pending':
        return '⏸️';
      case 'failed':
        return '❌';
      default:
        return '⚪';
    }
  };

  const getReplicaIcon = (replica: Replica) => {
    if (!replica.ready) {
      if (replica.status === 'Pending') return '⏸️';
      if (replica.status === 'ContainerCreating') return '⏳';
      if (replica.status === 'Terminating') return '🗑️';
      return '⚠️';
    }
    return '✅';
  };

  const showProgress = status.operation !== 'running';
  
  // Don't render anything if everything is running normally
  if (status.operation === 'running') {
    return null;
  }
  
  // Status message based on operation
  const statusMessage = 
    status.operation === 'upgrading' ? 'Upgrading...' :
    status.operation === 'scaling' ? 'Scaling...' :
    status.operation === 'restarting' ? 'Restarting...' :
    status.operation === 'starting' ? 'Starting...' :
    status.operation === 'pending' ? 'Pending...' :
    status.operation === 'stabilizing' ? (
      status.readyReplicas === 0 ? 'Starting Up...' :
      status.readyReplicas === 1 ? 'Initializing...' :
      'Stabilizing...'
    ) :
    status.operation === 'failed' ? 'Failed' :
    'Running';

  // Show blue banner style when operation in progress
  const bannerStyle = showProgress 
    ? 'bg-blue-50 border border-blue-200 rounded-lg p-4 space-y-3'
    : 'bg-white rounded-lg shadow-md p-6 space-y-4';

  if (compact) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="animate-spin">
              <svg className="h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>
            <div className="min-w-0">
              <p className="font-semibold text-blue-900 truncate">{statusMessage}</p>
              <p className="text-sm text-blue-700 truncate">
                Replicas: {status.readyReplicas}/{status.totalReplicas} • {status.operationMessage}
              </p>
            </div>
          </div>
          <div className="text-sm font-semibold text-blue-900 whitespace-nowrap">{status.progress}%</div>
        </div>
      </div>
    );
  }

  return (
    <div className={bannerStyle}>
      {/* Operation Status Header */}
      <div className="flex items-center gap-3">
        {showProgress && (
          <div className="animate-spin">
            <svg className="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
        )}
        {!showProgress && <span className="text-2xl">{getOperationIcon()}</span>}
        <div className="flex-1">
          <h3 className={`font-semibold ${showProgress ? 'text-blue-900' : getOperationColor()}`}>
            {statusMessage}
          </h3>
          <p className={`text-sm ${showProgress ? 'text-blue-700' : 'text-mongodb-slate'}`}>
            Replicas: {status.readyReplicas}/{status.totalReplicas} ready
          </p>
        </div>
      </div>

      {/* CR Phase and Message */}
      {status.crPhase && status.crPhase !== 'Running' && (
        <div className={`p-3 rounded-lg ${
          status.crPhase === 'Failed' ? 'bg-red-50 border border-red-200' :
          status.crPhase === 'Pending' ? 'bg-yellow-50 border border-yellow-200' :
          'bg-blue-50 border border-blue-200'
        }`}>
          <p className={`text-sm font-medium ${
            status.crPhase === 'Failed' ? 'text-red-800' :
            status.crPhase === 'Pending' ? 'text-yellow-800' :
            'text-blue-800'
          }`}>
            CR Phase: {status.crPhase}
          </p>
          {status.crMessage && (
            <p className={`text-xs mt-1 ${
              status.crPhase === 'Failed' ? 'text-red-700' :
              status.crPhase === 'Pending' ? 'text-yellow-700' :
              'text-blue-700'
            }`}>
              {status.crMessage}
            </p>
          )}
          {status.crActualVersion && status.crActualVersion !== status.currentVersion && (
            <p className="text-xs mt-1 text-gray-600">
              Operator working: {status.crActualVersion} → {status.currentVersion}
            </p>
          )}
        </div>
      )}

      {/* Progress Bar */}
      {showProgress && (
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-gray-600 mb-1">
            <span>Progress</span>
            <span>{status.progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                status.operation === 'upgrading'
                  ? 'bg-blue-500'
                  : status.operation === 'scaling'
                  ? 'bg-blue-500'
                  : status.operation === 'pending'
                  ? 'bg-yellow-500'
                  : status.operation === 'failed'
                  ? 'bg-red-500'
                  : 'bg-blue-500'
              }`}
              style={{ width: `${status.progress}%` }}
            ></div>
          </div>
          <p className="text-sm text-gray-600">{status.operationMessage}</p>
        </div>
      )}

      {/* Replica Status Table */}
      <div className="border-t pt-4">
        <h4 className="text-sm font-semibold text-mongodb-forest mb-3">Replica Status:</h4>
        <div className="space-y-2">
          {status.replicas.map((replica) => (
            <div
              key={replica.name}
              className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="text-xl">{getReplicaIcon(replica)}</span>
                <div>
                  <div className="font-medium text-sm text-mongodb-forest">
                    {replica.name}
                  </div>
                  <div className="text-xs text-mongodb-slate">{replica.status}</div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm font-mono text-mongodb-slate">
                  {replica.version}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Warning during operations */}
      {showProgress && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
          <p className="text-sm text-yellow-800">
            ⚠️ <strong>Operation in progress:</strong> Avoid scaling, upgrading, or restarting
            until this operation completes.
          </p>
        </div>
      )}
    </div>
  );
}
