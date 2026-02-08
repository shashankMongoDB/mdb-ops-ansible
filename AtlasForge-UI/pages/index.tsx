import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Button from '@leafygreen-ui/button';
import Card from '@leafygreen-ui/card';
import Badge from '@leafygreen-ui/badge';
import Icon from '@leafygreen-ui/icon';
import IconButton from '@leafygreen-ui/icon-button';
import { H1, Body } from '@leafygreen-ui/typography';
import { tenantsApi } from '@/lib/api/tenants';
import { deploymentsApi } from '@/lib/api/deployments';
import { Tenant, TenantWithStats } from '@/lib/types';
import { CreateTenantModal } from '@/components/CreateTenantModal';
import { useToast } from '@/components/Toast';

export default function TenantsPage() {
  const router = useRouter();
  const [tenants, setTenants] = useState<TenantWithStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const { showError } = useToast();

  const loadTenants = async () => {
    try {
      setLoading(true);
      const tenantsData = await tenantsApi.getAll();
      
      const tenantsWithStats = await Promise.all(
        tenantsData.map(async (tenant: Tenant) => {
          try {
            const deployments = await deploymentsApi.getAllForTenant(tenant.tenantId);
            const runningCount = deployments.filter(d => d.status?.phase === 'Running').length;
            const stoppedCount = deployments.filter(d => d.status?.phase === 'Stopped').length;
            const errorCount = deployments.filter(d => d.status?.phase === 'Error').length;
            
            return {
              ...tenant,
              deploymentCount: deployments.length,
              runningCount,
              stoppedCount,
              errorCount,
            };
          } catch (error) {
            return {
              ...tenant,
              deploymentCount: 0,
              runningCount: 0,
              stoppedCount: 0,
              errorCount: 0,
            };
          }
        })
      );
      
      setTenants(tenantsWithStats);
    } catch (error: any) {
      showError('Failed to load tenants', error.detail || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTenants();
  }, []);

  if (loading) {
    return (
      <div>
        <H1>Tenants</H1>
        <Body>Loading tenants...</Body>
      </div>
    );
  }

  return (
    <div>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '32px'
      }}>
        <div>
          <H1>Tenants</H1>
          <Body style={{ color: '#5C6C75', marginTop: '8px' }}>
            Manage your MongoDB tenants and deployments
          </Body>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <IconButton
            aria-label="Refresh"
            onClick={loadTenants}
          >
            <Icon glyph="Refresh" />
          </IconButton>
          <Button onClick={() => setShowCreateModal(true)}>
            Onboard Tenant
          </Button>
        </div>
      </div>

      {tenants.length === 0 ? (
        <Card style={{ padding: '48px', textAlign: 'center' }}>
          <Body>No tenants found. Create your first tenant to get started.</Body>
          <div style={{ marginTop: '24px' }}>
            <Button onClick={() => setShowCreateModal(true)}>
              Onboard Tenant
            </Button>
          </div>
        </Card>
      ) : (
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))',
          gap: '24px'
        }}>
          {tenants.map((tenant) => (
            <Card
              key={tenant.tenantId}
              style={{ 
                padding: '24px',
                cursor: 'pointer',
                transition: 'box-shadow 0.2s',
              }}
              onClick={() => router.push(`/tenants/${tenant.tenantId}`)}
            >
              <div style={{ marginBottom: '16px' }}>
                <h3 style={{ 
                  fontSize: '18px', 
                  fontWeight: 600,
                  marginBottom: '4px',
                  color: '#001E2B'
                }}>
                  {tenant.displayName || tenant.tenantId}
                </h3>
                <Body style={{ fontSize: '14px', color: '#5C6C75' }}>
                  {tenant.tenantId}
                </Body>
              </div>

              {tenant.environment && (
                <div style={{ marginBottom: '12px' }}>
                  <Badge variant="lightgray">{tenant.environment}</Badge>
                </div>
              )}

              <div style={{ 
                display: 'flex', 
                gap: '16px',
                paddingTop: '16px',
                borderTop: '1px solid #E8EDEB'
              }}>
                <div>
                  <Body style={{ fontSize: '12px', color: '#5C6C75' }}>
                    Deployments
                  </Body>
                  <Body style={{ fontSize: '20px', fontWeight: 600 }}>
                    {tenant.deploymentCount}
                  </Body>
                </div>
                
                {tenant.runningCount > 0 && (
                  <div>
                    <Body style={{ fontSize: '12px', color: '#5C6C75' }}>
                      Running
                    </Body>
                    <Body style={{ fontSize: '20px', fontWeight: 600, color: '#00684A' }}>
                      {tenant.runningCount}
                    </Body>
                  </div>
                )}
                
                {tenant.errorCount > 0 && (
                  <div>
                    <Body style={{ fontSize: '12px', color: '#5C6C75' }}>
                      Errors
                    </Body>
                    <Body style={{ fontSize: '20px', fontWeight: 600, color: '#CE1126' }}>
                      {tenant.errorCount}
                    </Body>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      <CreateTenantModal
        open={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={loadTenants}
      />
    </div>
  );
}
