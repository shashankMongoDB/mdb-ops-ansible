import { useEffect, useState } from 'react';
import { ClipboardDocumentIcon, CheckIcon } from '@heroicons/react/24/outline';
import { deploymentsApi } from '@/lib/api';
import { useToast } from './Toast';
import type { PrometheusScrapeConfig } from '@/lib/types';

interface PrometheusCardProps {
  tenantId: string;
  deploymentId: string;
}

export function PrometheusCard({ tenantId, deploymentId }: PrometheusCardProps) {
  const [config, setConfig] = useState<PrometheusScrapeConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const { showSuccess, showError } = useToast();

  useEffect(() => {
    loadConfig();
  }, [tenantId, deploymentId]);

  const loadConfig = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await deploymentsApi.getPrometheusScrapeConfig(tenantId, deploymentId);
      setConfig(data);
    } catch (error: any) {
      const errorMsg = error.detail || error.message || 'Unknown error';
      setError(errorMsg);
      showError('Failed to load Prometheus config', errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const buildYamlConfig = () => {
    if (!config) return '';

    const labelsYaml = Object.entries(config.labels)
      .map(([key, value]) => `        ${key}: "${value}"`)
      .join('\n');

    return `job_name: "${config.jobName}"
metrics_path: ${config.metricsPath}
basic_auth:
  username: ${config.username}
  password: ${config.password}
static_configs:
  - targets:
${config.targets.map(t => `    - "${t}"`).join('\n')}
    labels:
${labelsYaml}`;
  };

  const handleCopy = async () => {
    const yamlConfig = buildYamlConfig();
    try {
      await navigator.clipboard.writeText(yamlConfig);
      setCopied(true);
      showSuccess('Copied!', 'Configuration copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      showError('Failed to copy', 'Could not copy to clipboard');
    }
  };

  if (loading) {
    return (
      <div className="card">
        <div className="text-gray-500">Loading Prometheus configuration...</div>
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

  return (
    <div className="card">
      <h3 className="text-xl font-semibold text-mongodb-forest mb-4">Prometheus Scrape Configuration</h3>

      {/* Password warning for first view */}
      {config.isFirstView && (
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
          <p className="text-sm text-yellow-800 font-medium">
            ⚠️ Password is shown only once in full. Please copy and store it securely. 
            It will be masked on subsequent views.
          </p>
        </div>
      )}

      {/* Instructions */}
      <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
        <h4 className="font-medium text-blue-900 mb-2">Instructions:</h4>
        <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
          <li>Copy the configuration below and add it to your <code className="bg-blue-100 px-1 rounded">prometheus.yml</code> file</li>
          <li>You can use any of the worker node IPs listed below with NodePort <code className="bg-blue-100 px-1 rounded">{config.nodePort}</code></li>
          <li>After updating prometheus.yml, restart your Prometheus server</li>
          <li>Access your Prometheus UI to verify the target health</li>
        </ol>
      </div>

      {/* Worker Node IPs */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Available Worker Node IPs:
        </label>
        <div className="flex flex-wrap gap-2">
          {config.workerNodeIps.map((ip) => (
            <span key={ip} className="badge badge-gray font-mono text-xs">
              {ip}
            </span>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-1">
          NodePort: <span className="font-mono">{config.nodePort}</span>
        </p>
      </div>

      {/* YAML Configuration */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <label className="block text-sm font-medium text-gray-700">
            Prometheus Configuration:
          </label>
          <button
            onClick={handleCopy}
            className="btn-secondary text-xs flex items-center gap-1"
          >
            {copied ? (
              <>
                <CheckIcon className="h-4 w-4" />
                Copied!
              </>
            ) : (
              <>
                <ClipboardDocumentIcon className="h-4 w-4" />
                Copy Config
              </>
            )}
          </button>
        </div>
        <pre className="bg-gray-50 p-4 rounded-md border border-gray-200 text-xs font-mono overflow-x-auto whitespace-pre">
{buildYamlConfig()}
        </pre>
      </div>

      {/* Additional Details */}
      <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-200">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Job Name</label>
          <p className="text-sm font-mono text-gray-900">{config.jobName}</p>
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Username</label>
          <p className="text-sm font-mono text-gray-900">{config.username}</p>
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Metrics Path</label>
          <p className="text-sm font-mono text-gray-900">{config.metricsPath}</p>
        </div>
      </div>
    </div>
  );
}
