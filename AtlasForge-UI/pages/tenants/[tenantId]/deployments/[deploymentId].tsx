import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Button from '@leafygreen-ui/button';
import Card from '@leafygreen-ui/card';
import Badge from '@leafygreen-ui/badge';
import Icon from '@leafygreen-ui/icon';
import IconButton from '@leafygreen-ui/icon-button';
import { H1, H2, H3, Body } from '@leafygreen-ui/typography';
import { Tabs, Tab } from '@leafygreen-ui/tabs';
import { deploymentsApi } from '@/lib/api/deployments';
import { Deployment } from '@/lib/types';
import { StatusBadge } from '@/components/StatusBadge';
import { ScaleDeploymentModal } from '@/components/ScaleDeploymentModal';
import { UpgradeVersionModal } from '@/components/UpgradeVersionModal';
import { ConfirmActionModal } from '@/components/ConfirmActionModal';
import { ConnectionInfoCard } from '@/components/ConnectionInfoCard';
import { PrometheusCard } from '@/components/PrometheusCard';
import { useToast } from '@/components/Toast';
import { formatTimestamp } from '@/lib/utils';

type ActionType = 'shutdown' | 'start' | 'restart' | null;

export default function DeploymentDetailsPage() {
  const router = useRouter();
  const { tenantId, deploymentId } = router.query;
  const [deployment, setDeployment] = useState<Deployment | null>(null);
  const [loading, setLoading] = useState(true);
  const [showScaleModal, setShowScaleModal] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [confirmAction, setConfirmAction] = useState<ActionType>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const { showSuccess, showError } = useToast();

  const loadData = async () => {
    if (!tenantId || typeof tenantId !== 'string') return;
    if (!deploymentId || typeof deploymentId !== 'string') return;

    try {
      setLoading(true);
      const data = await deploymentsApi.getById(tenantId, deploymentId);
      setDeployment(data);
    } catch (error: any) {
      showError('Failed to load deployment details', error.detail || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, [tenantId, deploymentId]);


  const handleAction = async (action: ActionType) => {
    if (!tenantId || typeof tenantId !== 'string') return;
    if (!deploymentId || typeof deploymentId !== 'string') return;
    if (!action) return;

    setActionLoading(true);
    try {
      switch (action) {
        case 'shutdown':
          await deploymentsApi.shutdown(tenantId, deploymentId);
          showSuccess('Shutdown initiated', 'Deployment is shutting down');
          break;
        case 'start':
          await deploymentsApi.start(tenantId, deploymentId);
          showSuccess('Start initiated', 'Deployment is starting');
          break;
        case 'restart':
          await deploymentsApi.restart(tenantId, deploymentId);
          showSuccess('Restart initiated', 'Deployment is restarting');
          break;
      }
      setConfirmAction(null);
      await loadData();
    } catch (error: any) {
      showError(`Failed to ${action} deployment`, error.detail || 'An error occurred');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div>
        <Body>Loading deployment details...</Body>
      </div>
    );
  }

  if (!deployment) {
    return (
      <div>
        <H1>Deployment Not Found</H1>
        <Body>The requested deployment could not be found.</Body>
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <Button
          variant="default"
          leftGlyph={<Icon glyph="ChevronLeft" />}
          onClick={() => router.push(`/tenants/${tenantId}`)}
          style={{ marginBottom: '16px' }}
        >
          Back to Tenant
        </Button>
      </div>

      <Card style={{ padding: '24px', marginBottom: '32px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
          <div style={{ flex: 1 }}>
            <H1>{deployment.displayName || deployment.deploymentId}</H1>
            <Body style={{ color: '#5C6C75', marginTop: '8px' }}>
              Deployment ID: {deployment.deploymentId}
            </Body>
            <Body style={{ color: '#5C6C75', marginTop: '4px' }}>
              Tenant: {deployment.tenantId}
            </Body>
            
            <div style={{ display: 'flex', gap: '12px', marginTop: '16px', flexWrap: 'wrap' }}>
              <div>
                <Body style={{ fontSize: '12px', color: '#5C6C75' }}>Type</Body>
                <Body style={{ fontWeight: 600 }}>{deployment.type}</Body>
              </div>
              <div>
                <Body style={{ fontSize: '12px', color: '#5C6C75' }}>Version</Body>
                <Body style={{ fontWeight: 600 }}>{deployment.mongoVersion}</Body>
              </div>
              {deployment.members && (
                <div>
                  <Body style={{ fontSize: '12px', color: '#5C6C75' }}>Members</Body>
                  <Body style={{ fontWeight: 600 }}>{deployment.members}</Body>
                </div>
              )}
              {deployment.environment && (
                <div>
                  <Body style={{ fontSize: '12px', color: '#5C6C75' }}>Environment</Body>
                  <Badge variant="lightgray">{deployment.environment}</Badge>
                </div>
              )}
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', alignItems: 'flex-end' }}>
            {deployment.status && <StatusBadge status={deployment.status} />}
            {deployment.status?.timestamp && (
              <Body style={{ fontSize: '12px', color: '#5C6C75' }}>
                Updated: {formatTimestamp(deployment.status.timestamp)}
              </Body>
            )}
            <IconButton
              aria-label="Refresh"
              onClick={loadData}
            >
              <Icon glyph="Refresh" />
            </IconButton>
          </div>
        </div>
      </Card>

      <Tabs aria-label="Deployment Management">
        <Tab name="Overview" default>
          <div style={{ padding: '24px 0' }}>
            <H2 style={{ marginBottom: '24px' }}>Lifecycle Controls</H2>
            
            <div style={{ display: 'flex', gap: '12px', marginBottom: '32px', flexWrap: 'wrap' }}>
              {deployment.type === 'ReplicaSet' && (
                <Button onClick={() => setShowScaleModal(true)}>
                  Scale Members
                </Button>
              )}
              <Button onClick={() => setShowUpgradeModal(true)}>
                Upgrade Version
              </Button>
              <Button
                variant="default"
                onClick={() => setConfirmAction('restart')}
              >
                Restart
              </Button>
              {deployment.status?.phase === 'Running' ? (
                <Button
                  variant="danger"
                  onClick={() => setConfirmAction('shutdown')}
                >
                  Shutdown
                </Button>
              ) : (
                <Button onClick={() => setConfirmAction('start')}>
                  Start
                </Button>
              )}
            </div>

            <div style={{ marginBottom: '24px' }}>
              <ConnectionInfoCard
                tenantId={deployment.tenantId}
                deploymentId={deployment.deploymentId}
              />
            </div>
          </div>
        </Tab>

        <Tab name="Monitoring">
          <div style={{ padding: '24px 0' }}>
            <PrometheusCard
              tenantId={deployment.tenantId}
              deploymentId={deployment.deploymentId}
            />
          </div>
        </Tab>

        <Tab name="Backup">
          <div style={{ padding: '24px 0' }}>
            <Card style={{ padding: '24px' }}>
              <H3>Backup Configuration</H3>
              <Body style={{ marginTop: '16px', color: '#5C6C75' }}>
                Backup enrollment is managed via CR spec. Check your deployment's CR for backup configuration.
              </Body>
              <Badge variant="lightgray" style={{ marginTop: '16px' }}>
                Backup Status: Check CR
              </Badge>
            </Card>
          </div>
        </Tab>
      </Tabs>

      {deployment.type === 'ReplicaSet' && deployment.members && (
        <ScaleDeploymentModal
          open={showScaleModal}
          onClose={() => setShowScaleModal(false)}
          onSuccess={loadData}
          tenantId={deployment.tenantId}
          deploymentId={deployment.deploymentId}
          currentMembers={deployment.members}
        />
      )}

      <UpgradeVersionModal
        open={showUpgradeModal}
        onClose={() => setShowUpgradeModal(false)}
        onSuccess={loadData}
        tenantId={deployment.tenantId}
        deploymentId={deployment.deploymentId}
        currentVersion={deployment.mongoVersion}
      />

      <ConfirmActionModal
        open={confirmAction === 'shutdown'}
        onConfirm={() => handleAction('shutdown')}
        onCancel={() => setConfirmAction(null)}
        title="Shutdown Deployment"
        confirmText="Shutdown"
        variant="danger"
      >
        Are you sure you want to shutdown this deployment? All MongoDB processes will be stopped.
      </ConfirmActionModal>

      <ConfirmActionModal
        open={confirmAction === 'start'}
        onConfirm={() => handleAction('start')}
        onCancel={() => setConfirmAction(null)}
        title="Start Deployment"
        confirmText="Start"
      >
        Are you sure you want to start this deployment?
      </ConfirmActionModal>

      <ConfirmActionModal
        open={confirmAction === 'restart'}
        onConfirm={() => handleAction('restart')}
        onCancel={() => setConfirmAction(null)}
        title="Restart Deployment"
        confirmText="Restart"
      >
        Are you sure you want to restart this deployment? This will perform a rolling restart of all MongoDB processes.
      </ConfirmActionModal>
    </div>
  );
}
