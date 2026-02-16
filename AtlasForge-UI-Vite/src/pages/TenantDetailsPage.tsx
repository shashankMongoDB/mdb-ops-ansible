import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowPathIcon, ChevronLeftIcon, TrashIcon } from '@heroicons/react/24/outline';
import { tenantsApi, deploymentsApi } from '@/lib/api';
import { CreateDeploymentModal } from '@/components/CreateDeploymentModal';
import { ConfirmModal } from '@/components/ConfirmModal';
import { StatusBadge } from '@/components/StatusBadge';
import { ExpandableDeploymentList } from '@/components/ExpandableDeploymentList';
import { useToast } from '@/components/Toast';
import type { Tenant, Deployment } from '@/lib/types';

export function TenantDetailsPage() {
  const { tenantId } = useParams<{ tenantId: string }>();
  const navigate = useNavigate();
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const { showSuccess, showError } = useToast();

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
  }, [tenantId]); // Removed auto-refresh to prevent flickering

  const handleDeleteTenant = async () => {
    if (!tenantId) return;

    setDeleteLoading(true);
    try {
      await tenantsApi.delete(tenantId);
      showSuccess('Tenant deleted', 'Tenant has been successfully deleted');
      navigate('/');
    } catch (error: any) {
      showError('Failed to delete tenant', error.detail || 'An error occurred');
    } finally {
      setDeleteLoading(false);
      setShowDeleteConfirm(false);
    }
  };

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
        <div className="flex justify-between items-start">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-mongodb-forest">
                {tenant.displayName || tenant.tenantId}
              </h1>
              {tenant.plan === 'community' ? (
                <span className="badge badge-blue">Community</span>
              ) : (
                <span className="badge badge-green">Enterprise</span>
              )}
            </div>
            <p className="text-mongodb-slate mb-1">Tenant ID: {tenant.tenantId}</p>
            {tenant.namespace && <p className="text-mongodb-slate mb-1">Namespace: {tenant.namespace}</p>}
            <p className="text-mongodb-slate mb-3">
              Plan: <span className="font-medium">{tenant.plan === 'community' ? 'Community' : 'Enterprise'}</span>
            </p>
            {tenant.environment && <span className="badge badge-gray">{tenant.environment}</span>}
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (deployments.length === 0) {
                setShowDeleteConfirm(true);
              }
            }}
            disabled={deployments.length > 0}
            className={`p-2 ${
              deployments.length > 0
                ? 'text-gray-400 cursor-not-allowed'
                : 'text-red-600 hover:text-red-700'
            }`}
            title={
              deployments.length > 0
                ? 'Delete all deployments first before deleting tenant'
                : 'Delete Tenant'
            }
          >
            <TrashIcon className="h-5 w-5" />
          </button>
        </div>
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
        <ExpandableDeploymentList
          tenantId={tenantId!}
          deployments={deployments}
          tenantPlan={tenant.plan || 'enterprise'}
        />
      )}

      <CreateDeploymentModal
        open={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={loadData}
        tenantId={tenant.tenantId}
        tenantPlan={tenant.plan}
      />

      <ConfirmModal
        open={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        onConfirm={handleDeleteTenant}
        title="Delete Tenant"
        message={`Are you sure you want to delete tenant "${tenant.displayName || tenant.tenantId}"? This will delete all deployments and cannot be undone.`}
        confirmText="Delete"
        confirmVariant="danger"
        loading={deleteLoading}
      />
    </div>
  );
}
