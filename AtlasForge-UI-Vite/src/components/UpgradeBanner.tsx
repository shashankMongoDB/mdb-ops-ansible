import { useState } from 'react';
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';

interface ReplicaStatus {
  name: string;
  version: string;
  status: string;
  ready: boolean;
}

interface UpgradeBannerProps {
  fromVersion: string;
  toVersion: string;
  currentReplica: number;
  totalReplicas: number;
  percentage: number;
  replicas: ReplicaStatus[];
  estimatedTimeRemaining?: string;
}

export function UpgradeBanner({
  fromVersion,
  toVersion,
  currentReplica,
  totalReplicas,
  percentage,
  replicas,
  estimatedTimeRemaining,
}: UpgradeBannerProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="mb-6 border border-blue-200 rounded-lg overflow-hidden bg-blue-50">
      {/* Collapsed View */}
      <div className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3 flex-1">
            <div className="animate-spin h-5 w-5 border-2 border-blue-600 border-t-transparent rounded-full flex-shrink-0 mt-1" />
            <div className="flex-1">
              <h3 className="font-medium text-blue-900">
                Upgrade in Progress: {fromVersion} → {toVersion}
              </h3>
              <div className="mt-2">
                <div className="w-full bg-blue-200 rounded-full h-2.5 overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-blue-500 to-blue-600 h-2.5 rounded-full transition-all duration-500"
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
              <p className="mt-2 text-sm text-blue-800">
                Upgrading replica {currentReplica} of {totalReplicas}
                {estimatedTimeRemaining && ` • ${estimatedTimeRemaining} remaining`}
              </p>
            </div>
          </div>
          <button
            onClick={() => setExpanded(!expanded)}
            className="ml-4 p-1 hover:bg-blue-100 rounded transition-colors"
            aria-label={expanded ? 'Hide details' : 'Show details'}
          >
            {expanded ? (
              <ChevronUpIcon className="h-5 w-5 text-blue-700" />
            ) : (
              <ChevronDownIcon className="h-5 w-5 text-blue-700" />
            )}
          </button>
        </div>
      </div>

      {/* Expanded View */}
      {expanded && (
        <div className="border-t border-blue-200 bg-white">
          <div className="p-4">
            <h4 className="text-sm font-medium text-gray-900 mb-3">Replica Status</h4>
            <div className="space-y-2">
              {replicas.map((replica, index) => {
                const isUpgraded = replica.version === toVersion && replica.ready;
                const isUpgrading = !isUpgraded && replica.status !== 'Waiting';
                
                return (
                  <div
                    key={replica.name || index}
                    className={`flex items-center justify-between p-3 rounded-md ${
                      isUpgraded
                        ? 'bg-green-50 border border-green-200'
                        : isUpgrading
                        ? 'bg-blue-50 border border-blue-200'
                        : 'bg-gray-50 border border-gray-200'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      {isUpgraded ? (
                        <div className="h-2 w-2 bg-green-500 rounded-full" />
                      ) : isUpgrading ? (
                        <div className="h-2 w-2 bg-blue-500 rounded-full animate-pulse" />
                      ) : (
                        <div className="h-2 w-2 bg-gray-400 rounded-full" />
                      )}
                      <div>
                        <div className="text-sm font-medium text-gray-900">{replica.name}</div>
                        <div className="text-xs text-gray-600">
                          {isUpgraded
                            ? 'Upgraded'
                            : isUpgrading
                            ? 'Upgrading...'
                            : 'Waiting'}
                        </div>
                      </div>
                    </div>
                    <div className="text-sm font-mono text-gray-700">{replica.version}</div>
                  </div>
                );
              })}
            </div>

            <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
              <p className="text-xs text-yellow-800">
                <span className="font-medium">Note:</span> Avoid scaling, restarting, or shutting down during upgrade.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
