import { useEffect, useState } from 'react';
import { ClipboardDocumentIcon, CheckIcon } from '@heroicons/react/24/outline';
import { deploymentsApi } from '@/lib/api';
import { useToast } from './Toast';
import { copyToClipboard } from '@/lib/utils';
import type { ConnectionInfo as ConnectionInfoType } from '@/lib/types';

interface ConnectionInfoProps {
  tenantId: string;
  deploymentId: string;
}

export function ConnectionInfo({ tenantId, deploymentId }: ConnectionInfoProps) {
  const [connectionInfo, setConnectionInfo] = useState<ConnectionInfoType | null>(null);
  const [connectionMode, setConnectionMode] = useState<'primary' | 'secondary'>('primary');
  const [loading, setLoading] = useState(true);
  const [copiedUri, setCopiedUri] = useState(false);
  const [copiedMongosh, setCopiedMongosh] = useState(false);
  const { showSuccess, showError } = useToast();

  useEffect(() => {
    loadConnectionInfo();
  }, [tenantId, deploymentId]);

  const loadConnectionInfo = async () => {
    try {
      setLoading(true);
      const data = await deploymentsApi.getConnectionInfo(tenantId, deploymentId);
      setConnectionInfo(data);
    } catch (error: any) {
      showError('Failed to load connection info', error.detail);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async (text: string, type: 'uri' | 'mongosh') => {
    try {
      await copyToClipboard(text);
      if (type === 'uri') {
        setCopiedUri(true);
        setTimeout(() => setCopiedUri(false), 2000);
      } else {
        setCopiedMongosh(true);
        setTimeout(() => setCopiedMongosh(false), 2000);
      }
      showSuccess('Copied to clipboard');
    } catch (error) {
      showError('Failed to copy to clipboard');
    }
  };

  const withReadPreference = (uri: string, mode: 'primary' | 'secondary') => {
    const pref = mode === 'primary' ? 'primary' : 'secondaryPreferred';
    if (uri.includes('readPreference=')) {
      return uri.replace(/readPreference=[^&]*/g, `readPreference=${pref}`);
    }
    return uri.includes('?') ? `${uri}&readPreference=${pref}` : `${uri}?readPreference=${pref}`;
  };

  if (loading) {
    return <div className="text-gray-500">Loading connection info...</div>;
  }

  if (!connectionInfo) {
    return null;
  }

  const selectedExternalUri = connectionMode === 'primary'
    ? (connectionInfo.externalPrimaryUri || (connectionInfo.externalUri ? withReadPreference(connectionInfo.externalUri, 'primary') : null))
    : (connectionInfo.externalSecondaryUri || (connectionInfo.externalUri ? withReadPreference(connectionInfo.externalUri, 'secondary') : null));

  const selectedInternalUri = connectionInfo.internalUri
    ? withReadPreference(connectionInfo.internalUri, connectionMode)
    : null;

  return (
    <div className="card">
      <h3 className="text-xl font-semibold text-mongodb-forest mb-4">Connection Information</h3>

      <div className="mb-4 bg-yellow-50 border border-yellow-200 rounded-md p-3">
        <p className="text-xs text-yellow-800">
          <span className="font-semibold">Note:</span> Use these connection strings mainly to test connectivity.
          For application operations, create a dedicated DB user with appropriate roles from the <span className="font-semibold">DB Users</span> tab.
        </p>
      </div>

      <div className="mb-4">
        <label className="text-sm font-medium text-gray-700 block mb-2">Connection Target</label>
        <div className="flex gap-3">
          <label className="inline-flex items-center gap-2 text-sm">
            <input
              type="radio"
              name="connection-mode-main"
              checked={connectionMode === 'primary'}
              onChange={() => setConnectionMode('primary')}
            />
            Primary (read/write)
          </label>
          <label className="inline-flex items-center gap-2 text-sm">
            <input
              type="radio"
              name="connection-mode-main"
              checked={connectionMode === 'secondary'}
              onChange={() => setConnectionMode('secondary')}
            />
            Secondary preferred (reads)
          </label>
        </div>
      </div>

      <div className="space-y-4">
        {/* Error Message */}
        {connectionInfo.error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-3">
            <p className="text-sm text-red-800">
              <span className="font-medium">Error:</span> {connectionInfo.error}
            </p>
          </div>
        )}

        {/* Deployment Info */}
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Namespace</label>
            <p className="font-mono">{connectionInfo.namespace}</p>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Deployment</label>
            <p className="font-mono">{connectionInfo.deploymentId}</p>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Replica Set</label>
            <p className="font-mono">{connectionInfo.replicaSet}</p>
          </div>
        </div>

        {/* External MongoDB URI */}
        {selectedExternalUri && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-700">External MongoDB URI</label>
              <button
                onClick={() => handleCopy(selectedExternalUri, 'uri')}
                className="flex items-center gap-1 text-sm text-mongodb-green hover:text-mongodb-green-dark"
              >
                {copiedUri ? (
                  <>
                    <CheckIcon className="h-4 w-4" />
                    Copied
                  </>
                ) : (
                  <>
                    <ClipboardDocumentIcon className="h-4 w-4" />
                    Copy
                  </>
                )}
              </button>
            </div>
            <div className="bg-mongodb-green bg-opacity-5 p-3 rounded-md border border-mongodb-green font-mono text-sm break-all">
              {selectedExternalUri}
            </div>
            
            {/* Access Method Explanation */}
            <div className="mt-2 bg-blue-50 border border-blue-200 rounded-md p-3">
              <p className="text-xs text-blue-800">
                <span className="font-medium">Access Method:</span> This URI is accessible from clients within the same VPC 
                via private networking to the Kubernetes NodePort endpoint. 
                It is <strong>not reachable from the public internet</strong> unless explicitly exposed 
                through a load balancer or firewall rule.
              </p>
            </div>

            {/* mongosh Example */}
            <div className="mt-3">
              <label className="text-xs text-gray-500 block mb-1">mongosh Connection Example:</label>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-gray-50 p-2 rounded border border-gray-200 font-mono text-xs break-all">
                  mongosh "{selectedExternalUri}"
                </div>
                <button
                  onClick={() => handleCopy(`mongosh "${selectedExternalUri}"`, 'mongosh')}
                  className="flex-shrink-0 text-mongodb-green hover:text-mongodb-green-dark"
                  title="Copy mongosh command"
                >
                  {copiedMongosh ? (
                    <CheckIcon className="h-4 w-4" />
                  ) : (
                    <ClipboardDocumentIcon className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Internal URI (K8s cluster only) */}
        <div className="pt-4 border-t">
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-gray-500">
              Internal URI 
              <span className="text-xs text-gray-400 ml-2">(K8s cluster only)</span>
            </label>
            <button
              onClick={() => handleCopy(selectedInternalUri || connectionInfo.internalUri, 'uri')}
              className="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-800"
            >
              {copiedUri ? (
                <>
                  <CheckIcon className="h-4 w-4" />
                  Copied
                </>
              ) : (
                <>
                  <ClipboardDocumentIcon className="h-4 w-4" />
                  Copy
                </>
              )}
            </button>
          </div>
          <div className="bg-gray-50 p-3 rounded-md border border-gray-200 font-mono text-xs break-all">
            {selectedInternalUri || connectionInfo.internalUri}
          </div>
        </div>
      </div>
    </div>
  );
}
