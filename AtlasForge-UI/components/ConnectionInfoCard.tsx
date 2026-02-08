import React, { useState, useEffect } from 'react';
import Card from '@leafygreen-ui/card';
import Button from '@leafygreen-ui/button';
import Icon from '@leafygreen-ui/icon';
import { H3, Body } from '@leafygreen-ui/typography';
import Code from '@leafygreen-ui/code';
import { deploymentsApi } from '@/lib/api/deployments';
import { ConnectionInfo } from '@/lib/types';
import { useToast } from './Toast';
import { copyToClipboard } from '@/lib/utils';

interface ConnectionInfoCardProps {
  tenantId: string;
  deploymentId: string;
}

export function ConnectionInfoCard({ tenantId, deploymentId }: ConnectionInfoCardProps) {
  const [connectionInfo, setConnectionInfo] = useState<ConnectionInfo | null>(null);
  const [loading, setLoading] = useState(true);
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

  const handleCopy = async (text: string, label: string) => {
    try {
      await copyToClipboard(text);
      showSuccess(`${label} copied to clipboard`);
    } catch (error) {
      showError('Failed to copy to clipboard');
    }
  };

  if (loading) {
    return <Body>Loading connection info...</Body>;
  }

  if (!connectionInfo) {
    return null;
  }

  return (
    <Card style={{ padding: '24px' }}>
      <H3>Connection Information</H3>
      
      <div style={{ marginTop: '16px' }}>
        <Body style={{ fontWeight: 600, marginBottom: '8px' }}>
          MongoDB URI
        </Body>
        <div style={{ 
          display: 'flex', 
          alignItems: 'start', 
          gap: '8px',
          marginBottom: '16px'
        }}>
          <Code
            language="none"
            copyable={false}
            style={{ flex: 1 }}
          >
            {connectionInfo.mongoUri}
          </Code>
          <Button
            size="small"
            leftGlyph={<Icon glyph="Copy" />}
            onClick={() => handleCopy(connectionInfo.mongoUri, 'MongoDB URI')}
          >
            Copy
          </Button>
        </div>
      </div>

      <div style={{ marginTop: '16px' }}>
        <Body style={{ fontWeight: 600, marginBottom: '8px' }}>
          mongosh Example
        </Body>
        <div style={{ 
          display: 'flex', 
          alignItems: 'start', 
          gap: '8px'
        }}>
          <Code
            language="bash"
            copyable={false}
            style={{ flex: 1 }}
          >
            {connectionInfo.mongoshExample}
          </Code>
          <Button
            size="small"
            leftGlyph={<Icon glyph="Copy" />}
            onClick={() => handleCopy(connectionInfo.mongoshExample, 'mongosh command')}
          >
            Copy
          </Button>
        </div>
      </div>
    </Card>
  );
}
