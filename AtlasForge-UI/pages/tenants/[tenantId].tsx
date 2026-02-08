import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Button from '@leafygreen-ui/button';
import Card from '@leafygreen-ui/card';
import Badge from '@leafygreen-ui/badge';
import Icon from '@leafygreen-ui/icon';
import IconButton from '@leafygreen-ui/icon-button';
import { H1, H2, Body } from '@leafygreen-ui/typography';
import {
  Table,
  TableHeader,
  Row,
  Cell,
} from '@leafygreen-ui/table';
import { tenantsApi } from '@/lib/api/tenants';
import { deploymentsApi } from '@/lib/api/deployments';
import { Tenant, Deployment } from '@/lib/types';
import { CreateDeploymentModal } from '@/components/CreateDeploymentModal';
import { StatusBadge } from '@/components/StatusBadge';
import { useToast } from '@/components/Toast';
import { formatTimestamp } from '@/lib/utils';

export default function TenantDetailsPage() {
  const router = useRouter();
  const { tenantId } = router.query;
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const { showError } = useToast();

  const loadData = async () => {
    if (!tenantId || typeof tenantId !== 'string') return;

    try {
      setLoading(true);
      const [tenantData, deploymentsData] = await Promise.all([
        tenantsApi.getById(tenantId),
        deploymentsApi.getAllForTenant(tenantId),
      ]);
      setTenant(tenantData);
      setDeployments(deploymentsData);
    } catch (error: any) {
      showError('Failed to load tenant details', error.detail || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, [tenantId]);

  if (loading) {
    return (
      <div>
        <Body>Loading tenant details...</Body>
      </div>
    );
  }

  if (!tenant) {
    return (
      <div>
        <H1>Tenant Not Found</H1>
        <Body>The requested tenant could not be found.</Body>
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <Button
          variant="default"
          leftGlyph={<Icon glyph="ChevronLeft" />}
          onClick={() => router.push('/')}
          style={{ marginBottom: '16px' }}
        >
          Back to Tenants
        </Button>
      </div>

      <Card style={{ padding: '24px', marginBottom: '32px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
          <div>
            <H1>{tenant.displayName || tenant.tenantId}</H1>
            <Body style={{ color: '#5C6C75', marginTop: '8px' }}>
              Tenant ID: {tenant.tenantId}
            </Body>
            {tenant.namespace && (
              <Body style={{ color: '#5C6C75', marginTop: '4px' }}>
                Namespace: {tenant.namespace}
              </Body>
            )}
            {tenant.environment && (
              <div style={{ marginTop: '12px' }}>
                <Badge variant="lightgray">{tenant.environment}</Badge>
              </div>
            )}
          </div>
        </div>
      </Card>

      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '24px'
      }}>
        <H2>Deployments</H2>
        <div style={{ display: 'flex', gap: '12px' }}>
          <IconButton
            aria-label="Refresh"
            onClick={loadData}
          >
            <Icon glyph="Refresh" />
          </IconButton>
          <Button onClick={() => setShowCreateModal(true)}>
            Create Deployment
          </Button>
        </div>
      </div>

      {deployments.length === 0 ? (
        <Card style={{ padding: '48px', textAlign: 'center' }}>
          <Body>No deployments found. Create your first MongoDB deployment.</Body>
          <div style={{ marginTop: '24px' }}>
            <Button onClick={() => setShowCreateModal(true)}>
              Create Deployment
            </Button>
          </div>
        </Card>
      ) : (
        <Table
          data={deployments}
          columns={[
            <TableHeader key="id" label="Deployment ID" />,
            <TableHeader key="name" label="Display Name" />,
            <TableHeader key="type" label="Type" />,
            <TableHeader key="version" label="Version" />,
            <TableHeader key="members" label="Members" />,
            <TableHeader key="status" label="Status" />,
            <TableHeader key="actions" label="" />,
          ]}
        >
          {({ datum }) => (
            <Row key={datum.deploymentId}>
              <Cell>{datum.deploymentId}</Cell>
              <Cell>{datum.displayName || '-'}</Cell>
              <Cell>{datum.type}</Cell>
              <Cell>{datum.mongoVersion}</Cell>
              <Cell>{datum.members || '-'}</Cell>
              <Cell>
                {datum.status ? (
                  <StatusBadge status={datum.status} />
                ) : (
                  <Badge variant="lightgray">Unknown</Badge>
                )}
              </Cell>
              <Cell>
                <Button
                  size="small"
                  onClick={() => router.push(`/tenants/${tenant.tenantId}/deployments/${datum.deploymentId}`)}
                >
                  View Details
                </Button>
              </Cell>
            </Row>
          )}
        </Table>
      )}

      <CreateDeploymentModal
        open={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={loadData}
        tenantId={tenant.tenantId}
      />
    </div>
  );
}
