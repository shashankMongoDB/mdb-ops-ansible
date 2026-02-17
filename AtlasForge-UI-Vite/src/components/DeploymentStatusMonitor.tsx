import { useEffect, useState } from 'react';
import { deploymentsApi } from '@/lib/api';

interface Replica {
  name: string;
  version: string;
  status: string;
  ready: boolean;
}

interface StatusData {
  operation: 'running' | 'upgrading' | 'scaling' | 'stabilizing';
  progress: number;
  operationMessage: string;
  targetVersion: string;
  targetReplicas: number;
  currentVersion: string;
  currentReplicas: number;
  readyReplicas: number;
  totalReplicas: number;
  replicas: Replica[];
}

interface Props {
  tenantId: string;
  deploymentId: string;
  onStatusChange?: (status: StatusData) => void;
}

export function DeploymentStatusMonitor({ tenantId, deploymentId, onStatusChange }: Props) {
  const [status, setStatus] = useState<StatusData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let timeoutId: NodeJS.Timeout;
    let isMounted = true;

    const pollStatus = async () => {
      try {
        const info = await deploymentsApi.getConnectionInfo(tenantId, deploymentId);
        
        if (isMounted && info.operation) {
          const statusData: StatusData = {
            operation: info.operation,
            progress: info.progress || 0,
            operationMessage: info.operationMessage || '',
            targetVersion: info.targetVersion || '',
            targetReplicas: info.targetReplicas || 0,
            currentVersion: info.currentVersion || '',
            currentReplicas: info.currentReplicas || 0,
            readyReplicas: info.readyReplicas || 0,
            totalReplicas: info.totalReplicas || 0,
            replicas: info.replicas || []
          };
          
          setStatus(statusData);
          setLoading(false);
          
          if (onStatusChange) {
            onStatusChange(statusData);
          }
          
          // Adjust polling frequency based on operation
          const pollInterval = statusData.operation === 'running' ? 30000 : 5000;
          timeoutId = setTimeout(pollStatus, pollInterval);
        }
      } catch (error) {
        console.error('Failed to poll deployment status:', error);
        setLoading(false);
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

  if (loading || !status) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center gap-3">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-mongodb-green"></div>
          <span className="text-mongodb-slate">Loading status...</span>
        </div>
      </div>
    );
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

  return (
    <div className="bg-white rounded-lg shadow-md p-6 space-y-4">
      {/* Operation Status */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{getOperationIcon()}</span>
          <div>
            <h3 className={`text-lg font-semibold ${getOperationColor()}`}>
              {status.operation.charAt(0).toUpperCase() + status.operation.slice(1)}
            </h3>
            <p className="text-sm text-mongodb-slate">
              Replicas: {status.readyReplicas}/{status.totalReplicas} ready
            </p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-mongodb-forest">
            {status.progress}%
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      {showProgress && (
        <div className="space-y-2">
          <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                status.operation === 'upgrading'
                  ? 'bg-blue-500'
                  : status.operation === 'scaling'
                  ? 'bg-yellow-500'
                  : 'bg-orange-500'
              }`}
              style={{ width: `${status.progress}%` }}
            ></div>
          </div>
          <p className="text-sm text-mongodb-slate">{status.operationMessage}</p>
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
