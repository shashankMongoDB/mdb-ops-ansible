import { CheckCircleIcon, ClockIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

interface ReplicaStatus {
  name: string;
  version: string;
  status: string;
  ready: boolean;
}

interface UpgradeProgressViewProps {
  fromVersion: string;
  toVersion: string;
  currentReplica: number;
  totalReplicas: number;
  percentage: number;
  replicas: ReplicaStatus[];
  estimatedTimeRemaining?: string;
  startTime?: Date;
}

export function UpgradeProgressView({
  fromVersion,
  toVersion,
  currentReplica,
  totalReplicas,
  percentage,
  replicas,
  estimatedTimeRemaining,
  startTime,
}: UpgradeProgressViewProps) {
  const getReplicaStatusIcon = (replica: ReplicaStatus) => {
    if (replica.version === toVersion && replica.ready) {
      return <CheckCircleIcon className="h-5 w-5 text-green-600" />;
    } else if (replica.status === 'Upgrading' || replica.status === 'Pending') {
      return (
        <div className="animate-spin h-5 w-5 border-2 border-blue-600 border-t-transparent rounded-full" />
      );
    } else {
      return <ClockIcon className="h-5 w-5 text-gray-400" />;
    }
  };

  const getReplicaStatusText = (replica: ReplicaStatus) => {
    if (replica.version === toVersion && replica.ready) {
      return 'Upgraded';
    } else if (replica.status === 'Upgrading') {
      return 'Upgrading...';
    } else if (replica.status === 'Pending') {
      return 'Pending';
    } else {
      return 'Waiting';
    }
  };

  const getReplicaStatusColor = (replica: ReplicaStatus) => {
    if (replica.version === toVersion && replica.ready) {
      return 'text-green-700 bg-green-50';
    } else if (replica.status === 'Upgrading' || replica.status === 'Pending') {
      return 'text-blue-700 bg-blue-50';
    } else {
      return 'text-gray-600 bg-gray-50';
    }
  };

  const elapsedTime = startTime 
    ? Math.floor((new Date().getTime() - startTime.getTime()) / 1000) 
    : 0;
  
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-medium text-gray-900">
            Upgrading to {toVersion}
          </h3>
          <p className="text-sm text-gray-500">
            From {fromVersion} to {toVersion}
          </p>
        </div>
        {startTime && (
          <div className="text-right text-sm text-gray-500">
            <div>Elapsed: {formatTime(elapsedTime)}</div>
            {estimatedTimeRemaining && (
              <div>Remaining: ~{estimatedTimeRemaining}</div>
            )}
          </div>
        )}
      </div>

      {/* Progress Bar */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">
            {currentReplica} of {totalReplicas} replicas upgraded
          </span>
          <span className="text-sm font-medium text-gray-900">{percentage}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
          <div
            className="bg-gradient-to-r from-blue-500 to-blue-600 h-3 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${percentage}%` }}
          >
            <div className="h-full w-full animate-pulse opacity-75" />
          </div>
        </div>
      </div>

      {/* Status Message */}
      <div className="p-3 bg-blue-50 border border-blue-200 rounded-md">
        <div className="flex items-start gap-2">
          <div className="animate-spin h-5 w-5 border-2 border-blue-600 border-t-transparent rounded-full flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-800">
            {percentage === 100 ? (
              <p className="font-medium">Finalizing upgrade...</p>
            ) : (
              <>
                <p className="font-medium">
                  Upgrading replica {currentReplica} of {totalReplicas}
                </p>
                <p className="mt-1 text-blue-700">
                  The deployment remains available during this rolling upgrade.
                </p>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Replica Status Table */}
      {replicas && replicas.length > 0 && (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
            <h4 className="text-sm font-medium text-gray-900">Replica Status</h4>
          </div>
          <div className="divide-y divide-gray-200">
            {replicas.map((replica, index) => (
              <div
                key={replica.name || index}
                className={`px-4 py-3 flex items-center justify-between transition-colors ${getReplicaStatusColor(replica)}`}
              >
                <div className="flex items-center gap-3 flex-1">
                  {getReplicaStatusIcon(replica)}
                  <div>
                    <div className="font-medium text-sm">{replica.name}</div>
                    <div className="text-xs text-gray-600">
                      {getReplicaStatusText(replica)}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-mono">{replica.version}</div>
                  <div className="text-xs text-gray-600">{replica.status}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Warning Note */}
      {percentage < 100 && (
        <div className="flex items-start gap-2 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
          <ExclamationTriangleIcon className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-yellow-800">
            <p className="font-medium">Do not perform other operations during upgrade</p>
            <p className="mt-1 text-yellow-700">
              Avoid scaling, restarting, or shutting down the deployment until the upgrade completes.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
