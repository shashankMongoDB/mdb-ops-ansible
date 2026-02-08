import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowPathIcon, ChevronLeftIcon } from '@heroicons/react/24/outline';
import { tenantsApi, deploymentsApi } from '@/lib/api';
import { CreateDeploymentModal } from '@/components/CreateDeploymentModal';
import { StatusBadge } from '@/components/StatusBadge';
import { useToast } from '@/components/Toast';
import type { Tenant, Deployment } from '@/lib/types';

export function TenantDetailsPage() {
  const { tenantId } = useParams<{ tenantId: string }>();
  const navigate = useNavigate();
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const { showError } = useToast();

  const loadData = async () => {
    if (!tenantId) return;

    try {
      setLoading(true);
      const [tenantData, deploymentsData] = await Promise.all([
        tenantsApi.getById(tenantId),
        deploymentsApi.getAllForTenant(tenantId),
      ]);
      setTenant(tenantData);
      setDeployments(deploymentsData);
    } catch (error: any) {
      showError('Failed to load tenant details', error.detail || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();

    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, [tenantId]);

  if (loading) {
    return <div className="text-gray-500">Loading tenant details...</div>;
  }

  if (!tenant) {
    return (
      <div>
        <h1 className="text-3xl font-bold text-mongodb-forest mb-2">Tenant Not Found</h1>
        <p className="text-mongodb-slate">The requested tenant could not be found.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <Link to="/" className="inline-flex items-center gap-2 text-mongodb-green hover:text-mongodb-green-dark">
          <ChevronLeftIcon className="h-5 w-5" />
          Back to Tenants
        </Link>
      </div>

      <div className="card mb-8">
        <h1 className="text-3xl font-bold text-mongodb-forest mb-2">
          {tenant.displayName || tenant.tenantId}
        </h1>
        <p className="text-mongodb-slate mb-1">Tenant ID: {tenant.tenantId}</p>
        {tenant.namespace && <p className="text-mongodb-slate mb-3">Namespace: {tenant.namespace}</p>}
        {tenant.environment && <span className="badge badge-gray">{tenant.environment}</span>}
      </div>

      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-semibold text-mongodb-forest">Deployments</h2>
        <div className="flex gap-3">
          <button onClick={loadData} className="btn-secondary flex items-center gap-2">
            <ArrowPathIcon className="h-5 w-5" />
            Refresh
          </button>
          <button onClick={() => setShowCreateModal(true)} className="btn-primary">
            Create Deployment
          </button>
        </div>
      </div>

      {deployments.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-600 mb-4">No deployments found. Create your first MongoDB deployment.</p>
          <button onClick={() => setShowCreateModal(true)} className="btn-primary">
            Create Deployment
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {deployments.map((deployment) => (
            <div
              key={deployment.deploymentId}
              className="card cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => navigate(`/tenants/${tenantId}/deployments/${deployment.deploymentId}`)}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-mongodb-forest mb-1">
                    {deployment.displayName || deployment.deploymentId}
                  </h3>
                  <p className="text-sm text-mongodb-slate mb-3">{deployment.deploymentId}</p>

                  <div className="flex gap-6 flex-wrap">
                    <div>
                      <span className="text-xs text-mongodb-slate">Type</span>
                      <p className="font-medium">{deployment.type}</p>
                    </div>
                    <div>
                      <span className="text-xs text-mongodb-slate">Version</span>
                      <p className="font-medium">{deployment.mongoVersion}</p>
                    </div>
                    {deployment.members && (
                      <div>
                        <span className="text-xs text-mongodb-slate">Members</span>
                        <p className="font-medium">{deployment.members}</p>
                      </div>
                    )}
                    {deployment.environment && (
                      <div>
                        <span className="text-xs text-mongodb-slate">Environment</span>
                        <span className="badge badge-gray">{deployment.environment}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex flex-col items-end gap-3">
                  {deployment.status ? (
                    <StatusBadge status={deployment.status} />
                  ) : (
                    <span className="badge badge-gray">Unknown</span>
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/tenants/${tenantId}/deployments/${deployment.deploymentId}`);
                    }}
                    className="btn-secondary text-sm"
                  >
                    View Details
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <CreateDeploymentModal
        open={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={loadData}
        tenantId={tenant.tenantId}
      />
    </div>
  );
}
