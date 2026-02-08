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
  const [error, setError] = useState<string | null>(null);
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
      setError(null);
      console.log('Loading Prometheus config for:', tenantId, deploymentId);
      const data = await deploymentsApi.getPrometheusConfig(tenantId, deploymentId);
      console.log('Prometheus config received:', data);
      setConfig(data);
    } catch (error: any) {
      console.error('Failed to load Prometheus config:', error);
      const errorMsg = error.detail || error.message || 'Unknown error';
      setError(errorMsg);
      showError('Failed to load Prometheus config', errorMsg);
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
      const updatedConfig = await deploymentsApi.updatePrometheus(tenantId, deploymentId, pendingEnabled);
      setConfig(updatedConfig);
      showSuccess(
        `Prometheus ${pendingEnabled ? 'enabled' : 'disabled'}`,
        `Monitoring has been ${pendingEnabled ? 'enabled' : 'disabled'} for this deployment`
      );
    } catch (error: any) {
      showError('Failed to update Prometheus', error.detail);
    } finally {
      setUpdating(false);
      setShowConfirm(false);
    }
  };

  if (loading) {
    return (
      <div className="card">
        <div className="text-gray-500">Loading Prometheus config...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <h3 className="text-xl font-semibold text-mongodb-forest mb-4">Prometheus Monitoring</h3>
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-sm text-red-800">Error: {error}</p>
          <button onClick={loadConfig} className="btn-secondary mt-3">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="card">
        <h3 className="text-xl font-semibold text-mongodb-forest mb-4">Prometheus Monitoring</h3>
        <p className="text-gray-500">No configuration available</p>
      </div>
    );
  }

  const prometheusYaml = config.enabled && config.externalHost
    ? `# Add this to your prometheus.yml:

scrape_configs:
  - job_name: '${deploymentId}'
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

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">External Host</label>
                <p className="text-sm text-gray-600 font-mono">{config.externalHost || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">Port</label>
                <p className="text-sm text-gray-600 font-mono">{config.externalPort || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">Metrics Path</label>
                <p className="text-sm text-gray-600 font-mono">{config.metricsPath || '/metrics'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">Full URL</label>
                <p className="text-sm text-gray-600 font-mono">
                  {config.externalHost && config.externalPort 
                    ? `http://${config.externalHost}:${config.externalPort}${config.metricsPath || '/metrics'}`
                    : 'Not configured'}
                </p>
              </div>
            </div>

            {config.externalHost && prometheusYaml && (
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-2">
                  Prometheus Configuration (prometheus.yml)
                </label>
                <pre className="bg-gray-50 p-4 rounded-md border border-gray-200 text-xs font-mono overflow-x-auto whitespace-pre">
{prometheusYaml}
                </pre>
              </div>
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
