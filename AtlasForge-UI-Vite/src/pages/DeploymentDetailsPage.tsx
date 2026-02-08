import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { ArrowPathIcon, ChevronLeftIcon, TrashIcon } from '@heroicons/react/24/outline';
import { deploymentsApi } from '@/lib/api';
import { StatusBadge } from '@/components/StatusBadge';
import { ScaleModal } from '@/components/ScaleModal';
import { UpgradeVersionModal } from '@/components/UpgradeVersionModal';
import { ConfirmModal } from '@/components/ConfirmModal';
import { ConnectionInfo } from '@/components/ConnectionInfo';
import { PrometheusCard } from '@/components/PrometheusCard';
import { BackupCard } from '@/components/BackupCard';
import { useToast } from '@/components/Toast';
import { formatTimestamp } from '@/lib/utils';
import type { Deployment } from '@/lib/types';

type ActionType = 'shutdown' | 'restart' | 'delete' | null;
type TabType = 'overview' | 'monitoring' | 'backup';

export function DeploymentDetailsPage() {
  const { tenantId, deploymentId } = useParams<{ tenantId: string; deploymentId: string }>();
  const navigate = useNavigate();
  const [deployment, setDeployment] = useState<Deployment | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [showScaleModal, setShowScaleModal] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [confirmAction, setConfirmAction] = useState<ActionType>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const { showSuccess, showError } = useToast();

  const loadData = async () => {
    if (!tenantId || !deploymentId) return;

    try {
      setLoading(true);
      const data = await deploymentsApi.getById(tenantId, deploymentId);
      setDeployment(data);
    } catch (error: any) {
      showError('Failed to load deployment details', error.detail || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [tenantId, deploymentId]); // Removed auto-refresh to prevent flickering

  const handleAction = async (action: ActionType) => {
    if (!tenantId || !deploymentId || !action) return;

    setActionLoading(true);
    try {
      switch (action) {
        case 'shutdown':
          await deploymentsApi.shutdown(tenantId, deploymentId);
          showSuccess('Shutdown initiated', 'Deployment is shutting down');
          break;
        case 'restart':
          await deploymentsApi.restart(tenantId, deploymentId);
          showSuccess('Restart initiated', 'Deployment is restarting');
          break;
        case 'delete':
          await deploymentsApi.delete(tenantId, deploymentId);
          showSuccess('Deployment deleted', 'Deployment has been deleted');
          navigate(`/tenants/${tenantId}`);
          return;
      }
      setConfirmAction(null);
      await loadData();
    } catch (error: any) {
      showError(`Failed to ${action} deployment`, error.detail || 'An error occurred');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return <div className="text-gray-500">Loading deployment details...</div>;
  }

  if (!deployment) {
    return (
      <div>
        <h1 className="text-3xl font-bold text-mongodb-forest mb-2">Deployment Not Found</h1>
        <p className="text-mongodb-slate">The requested deployment could not be found.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <Link
          to={`/tenants/${tenantId}`}
          className="inline-flex items-center gap-2 text-mongodb-green hover:text-mongodb-green-dark"
        >
          <ChevronLeftIcon className="h-5 w-5" />
          Back to Tenant
        </Link>
      </div>

      <div className="card mb-8">
        <div className="flex justify-between items-start">
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-mongodb-forest mb-2">
              {deployment.displayName || deployment.deploymentId}
            </h1>
            <p className="text-mongodb-slate mb-1">Deployment ID: {deployment.deploymentId}</p>
            <p className="text-mongodb-slate mb-4">Tenant: {deployment.tenantId}</p>

            <div className="flex gap-6 flex-wrap">
              <div>
                <span className="text-xs text-mongodb-slate">Type</span>
                <p className="font-semibold">{deployment.type}</p>
              </div>
              <div>
                <span className="text-xs text-mongodb-slate">Version</span>
                <p className="font-semibold">{deployment.mongoVersion}</p>
              </div>
              {deployment.members && (
                <div>
                  <span className="text-xs text-mongodb-slate">Members</span>
                  <p className="font-semibold">{deployment.members}</p>
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

          <div className="flex flex-col items-end gap-2">
            {deployment.status && <StatusBadge status={deployment.status} />}
            {deployment.status?.timestamp && (
              <p className="text-xs text-mongodb-slate">Updated: {formatTimestamp(deployment.status.timestamp)}</p>
            )}
            <div className="flex gap-2 items-center">
              <button onClick={loadData} className="text-mongodb-green hover:text-mongodb-green-dark p-1" title="Refresh">
                <ArrowPathIcon className="h-5 w-5" />
              </button>
              <button 
                onClick={() => setConfirmAction('delete')} 
                className="text-red-600 hover:text-red-700 p-1"
                title="Delete Deployment"
              >
                <TrashIcon className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex space-x-8">
          {(['overview', 'monitoring', 'backup'] as TabType[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-2 px-1 border-b-2 font-medium text-sm capitalize ${
                activeTab === tab
                  ? 'border-mongodb-green text-mongodb-green'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-semibold text-mongodb-forest mb-4">Lifecycle Controls</h2>
            <div className="flex gap-3 flex-wrap">
              {deployment.type === 'ReplicaSet' && (
                <button onClick={() => setShowScaleModal(true)} className="btn-primary">
                  Scale Members
                </button>
              )}
              <button onClick={() => setShowUpgradeModal(true)} className="btn-primary">
                Upgrade Version
              </button>
              <button onClick={() => setConfirmAction('restart')} className="btn-secondary">
                Restart
              </button>
              <button onClick={() => setConfirmAction('shutdown')} className="btn-danger">
                Shutdown
              </button>
            </div>
          </div>

          <ConnectionInfo tenantId={deployment.tenantId} deploymentId={deployment.deploymentId} />
        </div>
      )}

      {activeTab === 'monitoring' && (
        <div>
          <PrometheusCard tenantId={deployment.tenantId} deploymentId={deployment.deploymentId} />
        </div>
      )}

      {activeTab === 'backup' && (
        <div>
          <BackupCard 
            tenantId={deployment.tenantId} 
            deploymentId={deployment.deploymentId}
            initialEnabled={false}
          />
        </div>
      )}

      {/* Modals */}
      {deployment.type === 'ReplicaSet' && deployment.members && (
        <ScaleModal
          open={showScaleModal}
          onClose={() => setShowScaleModal(false)}
          onSuccess={loadData}
          tenantId={deployment.tenantId}
          deploymentId={deployment.deploymentId}
          currentMembers={deployment.members}
        />
      )}

      <UpgradeVersionModal
        open={showUpgradeModal}
        onClose={() => setShowUpgradeModal(false)}
        onSuccess={loadData}
        tenantId={deployment.tenantId}
        deploymentId={deployment.deploymentId}
        currentVersion={deployment.mongoVersion}
      />

      <ConfirmModal
        open={confirmAction === 'shutdown'}
        onClose={() => setConfirmAction(null)}
        onConfirm={() => handleAction('shutdown')}
        title="Shutdown Deployment"
        message="Are you sure you want to shutdown this deployment? All MongoDB processes will be stopped."
        confirmText="Shutdown"
        confirmVariant="danger"
        loading={actionLoading}
      />

      <ConfirmModal
        open={confirmAction === 'restart'}
        onClose={() => setConfirmAction(null)}
        onConfirm={() => handleAction('restart')}
        title="Restart Deployment"
        message="Are you sure you want to restart this deployment? This will perform a rolling restart of all MongoDB processes."
        confirmText="Restart"
        loading={actionLoading}
      />

      <ConfirmModal
        open={confirmAction === 'delete'}
        onClose={() => setConfirmAction(null)}
        onConfirm={() => handleAction('delete')}
        title="Delete Deployment"
        message={`Are you sure you want to delete deployment "${deployment.displayName || deployment.deploymentId}"? This action cannot be undone.`}
        confirmText="Delete"
        confirmVariant="danger"
        loading={actionLoading}
      />
    </div>
  );
}
