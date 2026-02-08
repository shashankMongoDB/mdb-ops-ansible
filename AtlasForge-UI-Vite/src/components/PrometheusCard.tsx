import { useEffect, useState } from 'react';
import { deploymentsApi } from '@/lib/api';
import { useToast } from './Toast';
import { ConfirmModal } from './ConfirmModal';
import type { PrometheusConfig } from '@/lib/types';

interface PrometheusCardProps {
  tenantId: string;
  deploymentId: string;
}

export function PrometheusCard({ tenantId, deploymentId }: PrometheusCardProps) {
  const [config, setConfig] = useState<PrometheusConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [showConfirm, setShowConfirm] = useState(false);
  const [pendingEnabled, setPendingEnabled] = useState(false);
  const [updating, setUpdating] = useState(false);
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

  const handleToggle = () => {
    if (config) {
      setPendingEnabled(!config.enabled);
      setShowConfirm(true);
    }
  };

  const handleConfirm = async () => {
    setUpdating(true);
    try {
      await deploymentsApi.updatePrometheus(tenantId, deploymentId, pendingEnabled);
      showSuccess(
        `Prometheus ${pendingEnabled ? 'enabled' : 'disabled'}`,
        `Monitoring has been ${pendingEnabled ? 'enabled' : 'disabled'} for this deployment`
      );
      await loadConfig();
    } catch (error: any) {
      showError('Failed to update Prometheus', error.detail);
    } finally {
      setUpdating(false);
      setShowConfirm(false);
    }
  };

  if (loading) {
    return <div className="text-gray-500">Loading Prometheus config...</div>;
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
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-semibold text-mongodb-forest">Prometheus Monitoring</h3>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={config.enabled}
              onChange={handleToggle}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-mongodb-green/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-mongodb-green"></div>
          </label>
        </div>

        {config.enabled ? (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <span className="badge badge-green">Enabled</span>
            </div>

            {config.externalHost && (
              <>
                <div>
                  <label className="text-sm font-medium text-gray-700 block mb-1">Metrics Endpoint</label>
                  <p className="text-sm text-gray-600">
                    {config.externalHost}:{config.externalPort}
                    {config.metricsPath || '/metrics'}
                  </p>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-700 block mb-2">
                    Prometheus Configuration
                  </label>
                  <pre className="bg-gray-50 p-4 rounded-md border border-gray-200 text-xs font-mono overflow-x-auto">
                    {prometheusYaml}
                  </pre>
                </div>
              </>
            )}
          </div>
        ) : (
          <div>
            <span className="badge badge-gray">Disabled</span>
            <p className="text-sm text-gray-600 mt-3">Enable Prometheus to expose metrics for monitoring</p>
          </div>
        )}
      </div>

      <ConfirmModal
        open={showConfirm}
        onClose={() => setShowConfirm(false)}
        onConfirm={handleConfirm}
        title={`${pendingEnabled ? 'Enable' : 'Disable'} Prometheus Monitoring`}
        message={`Are you sure you want to ${pendingEnabled ? 'enable' : 'disable'} Prometheus monitoring for this deployment?`}
        confirmText={pendingEnabled ? 'Enable' : 'Disable'}
        loading={updating}
      />
    </>
  );
}
