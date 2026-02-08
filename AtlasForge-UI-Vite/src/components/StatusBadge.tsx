import type { DeploymentStatus } from '@/lib/types';
import { getStatusColor } from '@/lib/utils';

interface StatusBadgeProps {
  status: DeploymentStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const color = getStatusColor(status.phase);
  
  const colorClasses = {
    green: 'badge-green',
    blue: 'badge-blue',
    gray: 'badge-gray',
    red: 'badge-red',
    yellow: 'badge-yellow',
  };

  return (
    <span className={`badge ${colorClasses[color]}`}>
      {status.phase}
      {status.ready !== undefined && status.desired !== undefined && 
        ` (${status.ready}/${status.desired})`
      }
    </span>
  );
}
