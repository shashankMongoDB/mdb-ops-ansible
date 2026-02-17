import { useState, useEffect, useCallback, useRef } from 'react';
import { deploymentsApi } from '@/lib/api';

interface ReplicaStatus {
  name: string;
  version: string;
  status: string;
  ready: boolean;
}

interface UpgradeProgress {
  fromVersion: string;
  toVersion: string;
  currentReplica: number;
  totalReplicas: number;
  percentage: number;
  replicas: ReplicaStatus[];
  estimatedTimeRemaining: string | null;
  startTime: Date;
  isComplete: boolean;
  error: string | null;
}

interface UseUpgradePollingOptions {
  tenantId: string;
  deploymentId: string;
  targetVersion: string;
  enabled: boolean;
  onComplete?: () => void;
  onError?: (error: string) => void;
}

export function useUpgradePolling({
  tenantId,
  deploymentId,
  targetVersion,
  enabled,
  onComplete,
  onError,
}: UseUpgradePollingOptions) {
  const [progress, setProgress] = useState<UpgradeProgress | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const startTimeRef = useRef<Date | null>(null);

  const calculateETA = useCallback((startTime: Date, current: number, total: number): string | null => {
    if (current === 0) return null;
    
    const elapsedMs = new Date().getTime() - startTime.getTime();
    const avgTimePerReplica = elapsedMs / current;
    const remainingReplicas = total - current;
    const estimatedRemainingMs = avgTimePerReplica * remainingReplicas;
    
    const minutes = Math.ceil(estimatedRemainingMs / 60000);
    if (minutes < 1) return '< 1 minute';
    if (minutes === 1) return '1 minute';
    return `${minutes} minutes`;
  }, []);

  const checkUpgradeStatus = useCallback(async () => {
    try {
      const connectionInfo = await deploymentsApi.getConnectionInfo(tenantId, deploymentId);
      
      if (!connectionInfo.replicas || connectionInfo.replicas.length === 0) {
        return;
      }

      // Count upgraded replicas
      const upgradedReplicas = connectionInfo.replicas.filter(
        (r: any) => r.version === targetVersion && r.ready
      );
      
      const currentReplica = upgradedReplicas.length;
      const totalReplicas = connectionInfo.replicas.length;
      const percentage = Math.round((currentReplica / totalReplicas) * 100);
      
      // Check if all replicas are upgraded
      const isComplete = currentReplica === totalReplicas;
      
      // Get first non-upgraded replica version as "from" version
      const fromReplica = connectionInfo.replicas.find(
        (r: any) => r.version !== targetVersion
      );
      const fromVersion = fromReplica?.version || connectionInfo.replicas[0].version;

      const startTime = startTimeRef.current || new Date();
      if (!startTimeRef.current) {
        startTimeRef.current = startTime;
      }

      const progressData: UpgradeProgress = {
        fromVersion,
        toVersion: targetVersion,
        currentReplica,
        totalReplicas,
        percentage,
        replicas: connectionInfo.replicas.map((r: any) => ({
          name: r.name || 'unknown',
          version: r.version || 'unknown',
          status: r.ready ? 'Running' : 'Pending',
          ready: r.ready || false,
        })),
        estimatedTimeRemaining: calculateETA(startTime, currentReplica, totalReplicas),
        startTime,
        isComplete,
        error: null,
      };

      setProgress(progressData);

      if (isComplete) {
        stopPolling();
        onComplete?.();
      }
    } catch (error: any) {
      console.error('Failed to check upgrade status:', error);
      const errorMsg = error.detail || 'Failed to check upgrade status';
      setProgress(prev => prev ? { ...prev, error: errorMsg } : null);
      onError?.(errorMsg);
    }
  }, [tenantId, deploymentId, targetVersion, calculateETA, onComplete, onError]);

  const startPolling = useCallback(() => {
    if (isPolling) return;
    
    setIsPolling(true);
    startTimeRef.current = new Date();
    
    // Check immediately
    checkUpgradeStatus();
    
    // Then poll every 5 seconds
    intervalRef.current = setInterval(checkUpgradeStatus, 5000);
    
    // Safety timeout after 30 minutes
    setTimeout(() => {
      if (intervalRef.current) {
        stopPolling();
        onError?.('Upgrade monitoring timeout after 30 minutes');
      }
    }, 1800000);
  }, [isPolling, checkUpgradeStatus, onError]);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsPolling(false);
  }, []);

  // Auto-start polling when enabled
  useEffect(() => {
    if (enabled && !isPolling) {
      startPolling();
    } else if (!enabled && isPolling) {
      stopPolling();
    }

    return () => {
      stopPolling();
    };
  }, [enabled, isPolling, startPolling, stopPolling]);

  return {
    progress,
    isPolling,
    startPolling,
    stopPolling,
  };
}
