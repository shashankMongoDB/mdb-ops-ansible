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

  if (loading) {
    return <div className="text-gray-500">Loading connection info...</div>;
  }

  if (!connectionInfo) {
    return null;
  }

  return (
    <div className="card">
      <h3 className="text-xl font-semibold text-mongodb-forest mb-4">Connection Information</h3>

      <div className="space-y-4">
        {/* Error Message */}
        {connectionInfo.error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-3">
            <p className="text-sm text-red-800">
              <span className="font-medium">Error:</span> {connectionInfo.error}
            </p>
          </div>
        )}

        {/* Info Banner */}
        <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
          <p className="text-sm text-blue-800">
            <span className="font-medium">External access is automatically configured</span> via NodePort service. 
            Use the External URI from VMs/clients that can reach the worker node IP.
          </p>
        </div>

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

        {/* External URI */}
        {connectionInfo.externalUri && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-700">
                External URI 
                <span className="text-xs text-gray-500 ml-2">(from VPC clients)</span>
              </label>
              <button
                onClick={() => handleCopy(connectionInfo.externalUri!, 'uri')}
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
              {connectionInfo.externalUri}
            </div>
            {connectionInfo.externalHostPort && (
              <p className="text-xs text-gray-500 mt-1">
                Host: {connectionInfo.externalHostPort}
              </p>
            )}
          </div>
        )}

        {/* Internal URI */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-gray-700">
              Internal URI 
              <span className="text-xs text-gray-500 ml-2">(from inside K8s cluster)</span>
            </label>
            <button
              onClick={() => handleCopy(connectionInfo.internalUri, 'mongosh')}
              className="flex items-center gap-1 text-sm text-mongodb-green hover:text-mongodb-green-dark"
            >
              {copiedMongosh ? (
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
          <div className="bg-gray-50 p-3 rounded-md border border-gray-200 font-mono text-sm break-all">
            {connectionInfo.internalUri}
          </div>
        </div>

        {/* mongosh Examples */}
        <div className="pt-4 border-t">
          <label className="text-sm font-medium text-gray-700 block mb-3">mongosh Examples</label>
          
          {connectionInfo.externalUri && (
            <div className="mb-3">
              <p className="text-xs text-gray-500 mb-1">From VPC (outside K8s):</p>
              <div className="bg-gray-50 p-2 rounded border border-gray-200 font-mono text-xs break-all">
                mongosh "{connectionInfo.externalUri}"
              </div>
            </div>
          )}
          
          <div>
            <p className="text-xs text-gray-500 mb-1">From inside K8s cluster:</p>
            <div className="bg-gray-50 p-2 rounded border border-gray-200 font-mono text-xs break-all">
              mongosh "{connectionInfo.internalUri}"
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
