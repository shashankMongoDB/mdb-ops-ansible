import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowPathIcon } from '@heroicons/react/24/outline';
import { tenantsApi, deploymentsApi } from '@/lib/api';
import { CreateTenantModal } from '@/components/CreateTenantModal';
import { useToast } from '@/components/Toast';
import type { TenantWithStats } from '@/lib/types';

export function TenantsPage() {
  const navigate = useNavigate();
  const [tenants, setTenants] = useState<TenantWithStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const { showError } = useToast();

  const loadTenants = async () => {
    try {
      setLoading(true);
      const tenantsData = await tenantsApi.getAll();

      const tenantsWithStats = await Promise.all(
        tenantsData.map(async (tenant) => {
          try {
            const deployments = await deploymentsApi.getAllForTenant(tenant.tenantId);
            const runningCount = deployments.filter((d) => d.status?.phase === 'Running').length;
            const stoppedCount = deployments.filter((d) => d.status?.phase === 'Stopped').length;
            const errorCount = deployments.filter((d) => d.status?.phase === 'Error').length;

            return {
              ...tenant,
              deploymentCount: deployments.length,
              runningCount,
              stoppedCount,
              errorCount,
            };
          } catch {
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
  }, []); // Only load once, no auto-refresh

  if (loading) {
    return (
      <div>
        <h1 className="text-3xl font-bold text-mongodb-forest mb-2">Tenants</h1>
        <p className="text-mongodb-slate">Loading tenants...</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-mongodb-forest mb-2">Tenants</h1>
          <p className="text-mongodb-slate">Manage your MongoDB tenants and deployments</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={loadTenants}
            className="btn-secondary flex items-center gap-2"
            title="Refresh"
          >
            <ArrowPathIcon className="h-5 w-5" />
            Refresh
          </button>
          <button onClick={() => setShowCreateModal(true)} className="btn-primary">
            Onboard Tenant
          </button>
        </div>
      </div>

      {tenants.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-600 mb-4">No tenants found. Create your first tenant to get started.</p>
          <button onClick={() => setShowCreateModal(true)} className="btn-primary">
            Onboard Tenant
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {tenants.map((tenant) => (
            <div
              key={tenant.tenantId}
              onClick={() => navigate(`/tenants/${tenant.tenantId}`)}
              className="card cursor-pointer hover:shadow-md transition-shadow"
            >
              <h3 className="text-xl font-semibold text-mongodb-forest mb-1">
                {tenant.displayName || tenant.tenantId}
              </h3>
              <p className="text-sm text-mongodb-slate mb-3">{tenant.tenantId}</p>

              {tenant.environment && (
                <span className="badge badge-gray mb-4">{tenant.environment}</span>
              )}

              <div className="flex gap-6 pt-4 border-t border-gray-200">
                <div>
                  <p className="text-xs text-mongodb-slate">Deployments</p>
                  <p className="text-2xl font-semibold text-mongodb-forest">{tenant.deploymentCount}</p>
                </div>

                {tenant.runningCount > 0 && (
                  <div>
                    <p className="text-xs text-mongodb-slate">Running</p>
                    <p className="text-2xl font-semibold text-green-600">{tenant.runningCount}</p>
                  </div>
                )}

                {tenant.errorCount > 0 && (
                  <div>
                    <p className="text-xs text-mongodb-slate">Errors</p>
                    <p className="text-2xl font-semibold text-red-600">{tenant.errorCount}</p>
                  </div>
                )}
              </div>
            </div>
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
