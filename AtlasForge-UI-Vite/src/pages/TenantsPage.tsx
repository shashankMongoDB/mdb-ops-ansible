import { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowPathIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline';
import { tenantsApi, deploymentsApi } from '@/lib/api';
import { CreateTenantModal } from '@/components/CreateTenantModal';
import { useToast } from '@/components/Toast';
import type { TenantWithStats } from '@/lib/types';

type PlanFilter = 'all' | 'enterprise' | 'community';

export function TenantsPage() {
  const navigate = useNavigate();
  const [tenants, setTenants] = useState<TenantWithStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [planFilter, setPlanFilter] = useState<PlanFilter>('all');
  const { showError } = useToast();

  // Filtered tenants based on search and plan filter
  const filteredTenants = useMemo(() => {
    let filtered = tenants;

    // Apply plan filter
    if (planFilter !== 'all') {
      filtered = filtered.filter((t) => t.plan === planFilter);
    }

    // Apply search filter
    if (searchTerm.trim()) {
      const search = searchTerm.toLowerCase();
      filtered = filtered.filter((t) =>
        t.tenantId.toLowerCase().includes(search) ||
        (t.displayName && t.displayName.toLowerCase().includes(search)) ||
        (t.namespace && t.namespace.toLowerCase().includes(search))
      );
    }

    return filtered;
  }, [tenants, searchTerm, planFilter]);

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
      <div className="flex justify-between items-center mb-6">
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

      {/* Search and Filter */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        <div className="flex-1 relative">
          <MagnifyingGlassIcon className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search tenants by ID, name, or namespace..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-mongodb-green focus:border-mongodb-green"
          />
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setPlanFilter('all')}
            className={`px-4 py-2 text-sm font-medium rounded-md ${
              planFilter === 'all'
                ? 'bg-mongodb-green text-white'
                : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setPlanFilter('enterprise')}
            className={`px-4 py-2 text-sm font-medium rounded-md ${
              planFilter === 'enterprise'
                ? 'bg-green-600 text-white'
                : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
            }`}
          >
            Enterprise
          </button>
          <button
            onClick={() => setPlanFilter('community')}
            className={`px-4 py-2 text-sm font-medium rounded-md ${
              planFilter === 'community'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
            }`}
          >
            Community
          </button>
        </div>
      </div>

      {/* Results Count */}
      {tenants.length > 0 && (
        <div className="mb-4">
          <p className="text-sm text-gray-600">
            Showing {filteredTenants.length} of {tenants.length} tenant{tenants.length !== 1 ? 's' : ''}
          </p>
        </div>
      )}

      {tenants.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-600 mb-4">No tenants found. Create your first tenant to get started.</p>
          <button onClick={() => setShowCreateModal(true)} className="btn-primary">
            Onboard Tenant
          </button>
        </div>
      ) : filteredTenants.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-600 mb-4">No tenants match your search criteria.</p>
          <button onClick={() => { setSearchTerm(''); setPlanFilter('all'); }} className="btn-secondary">
            Clear Filters
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredTenants.map((tenant) => (
            <div
              key={tenant.tenantId}
              onClick={() => navigate(`/tenants/${tenant.tenantId}`)}
              className="card cursor-pointer hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between mb-2">
                <h3 className="text-xl font-semibold text-mongodb-forest">
                  {tenant.displayName || tenant.tenantId}
                </h3>
                {tenant.plan === 'community' ? (
                  <span className="badge badge-blue text-xs">Community</span>
                ) : (
                  <span className="badge badge-green text-xs">Enterprise</span>
                )}
              </div>
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
