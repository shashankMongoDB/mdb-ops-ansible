import React from 'react';
import Badge, { Variant } from '@leafygreen-ui/badge';
import { DeploymentStatus } from '@/lib/types';
import { getStatusColor } from '@/lib/utils';

interface StatusBadgeProps {
  status: DeploymentStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const variantMap: Record<string, Variant> = {
    green: 'green',
    blue: 'blue',
    gray: 'lightgray',
    red: 'red',
    yellow: 'yellow',
  };

  const color = getStatusColor(status.phase);
  const variant = variantMap[color];

  return (
    <Badge variant={variant}>
      {status.phase}
      {status.ready !== undefined && status.desired !== undefined && 
        ` (${status.ready}/${status.desired})`
      }
    </Badge>
  );
}
