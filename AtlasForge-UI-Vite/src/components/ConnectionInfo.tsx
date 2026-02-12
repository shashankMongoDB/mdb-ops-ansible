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
        {/* Access Method Info */}
        <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
          <p className="text-sm text-blue-800">
            <span className="font-medium">Access Method:</span> {connectionInfo.accessMethod}
          </p>
          {connectionInfo.message && (
            <p className="text-sm text-blue-700 mt-1">{connectionInfo.message}</p>
          )}
        </div>

        {/* External URI (if available) */}
        {connectionInfo.externalUri && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-700">External MongoDB URI</label>
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
            <div className="bg-gray-50 p-3 rounded-md border border-gray-200 font-mono text-sm break-all">
              {connectionInfo.externalUri}
            </div>
          </div>
        )}

        {/* Port Forward Command */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-gray-700">Port Forward Command</label>
            <button
              onClick={() => handleCopy(connectionInfo.portForwardCommand, 'uri')}
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
          <div className="bg-gray-50 p-3 rounded-md border border-gray-200 font-mono text-sm break-all">
            {connectionInfo.portForwardCommand}
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Run this command in a terminal, then connect to localhost:27017
          </p>
        </div>

        {/* mongosh Command */}
        {connectionInfo.mongoshExample && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-700">mongosh Command</label>
              <button
                onClick={() => handleCopy(connectionInfo.mongoshExample, 'mongosh')}
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
              {connectionInfo.mongoshExample}
            </div>
          </div>
        )}

        {/* Internal URI (for reference) */}
        <div className="pt-4 border-t">
          <label className="text-sm font-medium text-gray-500">Internal URI (K8s cluster only)</label>
          <div className="bg-gray-50 p-3 rounded-md border border-gray-200 font-mono text-xs break-all mt-2">
            {connectionInfo.internalUri}
          </div>
        </div>
      </div>
    </div>
  );
}
