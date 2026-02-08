import React, { useState, useEffect } from 'react';
import Card from '@leafygreen-ui/card';
import Button from '@leafygreen-ui/button';
import Toggle from '@leafygreen-ui/toggle';
import Badge from '@leafygreen-ui/badge';
import { H3, Body } from '@leafygreen-ui/typography';
import Code from '@leafygreen-ui/code';
import { deploymentsApi } from '@/lib/api/deployments';
import { PrometheusConfig } from '@/lib/types';
import { useToast } from './Toast';
import { ConfirmActionModal } from './ConfirmActionModal';

interface PrometheusCardProps {
  tenantId: string;
  deploymentId: string;
}

export function PrometheusCard({ tenantId, deploymentId }: PrometheusCardProps) {
  const [config, setConfig] = useState<PrometheusConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [showConfirm, setShowConfirm] = useState(false);
  const [pendingEnabled, setPendingEnabled] = useState(false);
  const { showSuccess, showError } = useToast();

  useEffect(() => {
    loadConfig();
  }, [tenantId, deploymentId]);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const data = await deploymentsApi.getPrometheusConfig(tenantId, deploymentId);
      setConfig(data);
    } catch (error: any) {
      showError('Failed to load Prometheus config', error.detail);
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = (enabled: boolean) => {
    setPendingEnabled(enabled);
    setShowConfirm(true);
  };

  const handleConfirm = async () => {
    try {
      await deploymentsApi.updatePrometheus(tenantId, deploymentId, { enabled: pendingEnabled });
      showSuccess(
        `Prometheus ${pendingEnabled ? 'enabled' : 'disabled'}`,
        `Monitoring has been ${pendingEnabled ? 'enabled' : 'disabled'} for this deployment`
      );
      await loadConfig();
    } catch (error: any) {
      showError('Failed to update Prometheus', error.detail);
    } finally {
      setShowConfirm(false);
    }
  };

  if (loading) {
    return <Body>Loading Prometheus config...</Body>;
  }

  if (!config) {
    return null;
  }

  const prometheusYaml = config.enabled && config.externalHost
    ? `- job_name: '${deploymentId}'
  static_configs:
    - targets: ['${config.externalHost}:${config.externalPort}']
  metrics_path: '${config.metricsPath || '/metrics'}'`
    : '';

  return (
    <>
      <Card style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <H3>Prometheus Monitoring</H3>
          <Toggle
            aria-label="Enable Prometheus"
            checked={config.enabled}
            onChange={(e) => handleToggle(e.target.checked)}
          />
        </div>

        <div style={{ marginTop: '16px' }}>
          {config.enabled ? (
            <>
              <Badge variant="green">Enabled</Badge>
              
              {config.externalHost && (
                <div style={{ marginTop: '16px' }}>
                  <Body style={{ fontWeight: 600, marginBottom: '8px' }}>
                    Metrics Endpoint
                  </Body>
                  <Body style={{ color: '#5C6C75', marginBottom: '16px' }}>
                    {config.externalHost}:{config.externalPort}{config.metricsPath || '/metrics'}
                  </Body>

                  <Body style={{ fontWeight: 600, marginBottom: '8px' }}>
                    Prometheus Configuration
                  </Body>
                  <Code language="yaml" copyable={true}>
                    {prometheusYaml}
                  </Code>
                </div>
              )}
            </>
          ) : (
            <>
              <Badge variant="lightgray">Disabled</Badge>
              <Body style={{ marginTop: '16px', color: '#5C6C75' }}>
                Enable Prometheus to expose metrics for monitoring
              </Body>
            </>
          )}
        </div>
      </Card>

      <ConfirmActionModal
        open={showConfirm}
        onConfirm={handleConfirm}
        onCancel={() => setShowConfirm(false)}
        title={`${pendingEnabled ? 'Enable' : 'Disable'} Prometheus Monitoring`}
        confirmText={pendingEnabled ? 'Enable' : 'Disable'}
      >
        Are you sure you want to {pendingEnabled ? 'enable' : 'disable'} Prometheus monitoring for this deployment?
      </ConfirmActionModal>
    </>
  );
}
