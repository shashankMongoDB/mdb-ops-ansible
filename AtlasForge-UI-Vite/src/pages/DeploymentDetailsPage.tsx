import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { ArrowPathIcon, ChevronLeftIcon, TrashIcon } from '@heroicons/react/24/outline';
import { deploymentsApi, tenantsApi } from '@/lib/api';
import { StatusBadge } from '@/components/StatusBadge';
import { ScaleModal } from '@/components/ScaleModal';
import { UpgradeVersionModal } from '@/components/UpgradeVersionModal';
import { ConfirmModal } from '@/components/ConfirmModal';
import { ConnectionInfo } from '@/components/ConnectionInfo';
import { PrometheusCard } from '@/components/PrometheusCard';
import { BackupPanel } from '@/components/BackupPanelReadOnly';
import { CreateUserModal } from '@/components/CreateUserModal';
import { UserConnectionModal } from '@/components/UserConnectionModal';
import { EditUserModal } from '@/components/EditUserModal';
import { useToast } from '@/components/Toast';
import { formatTimestamp } from '@/lib/utils';
import type { Deployment, Tenant } from '@/lib/types';

type ActionType = 'shutdown' | 'restart' | 'delete' | null;
type TabType = 'overview' | 'users' | 'backup' | 'monitoring';

export function DeploymentDetailsPage() {
  const { tenantId, deploymentId } = useParams<{ tenantId: string; deploymentId: string }>();
  const navigate = useNavigate();
  const [deployment, setDeployment] = useState<Deployment | null>(null);
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [showScaleModal, setShowScaleModal] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [confirmAction, setConfirmAction] = useState<ActionType>(null);
  const [actionLoading, setActionLoading] = useState(false);
  
  // DB Users state
  const [dbUsers, setDbUsers] = useState<any[]>([]);
  const [dbUsersLoading, setDbUsersLoading] = useState(false);
  const [showCreateUserModal, setShowCreateUserModal] = useState(false);
  const [creatingUser, setCreatingUser] = useState(false);
  const [showUserConnectionModal, setShowUserConnectionModal] = useState(false);
  const [selectedUserConnection, setSelectedUserConnection] = useState<any>(null);
  const [showEditUserModal, setShowEditUserModal] = useState(false);
  const [editingUser, setEditingUser] = useState<any>(null);
  const [updatingUser, setUpdatingUser] = useState(false);
  const [deletingUser, setDeletingUser] = useState<string | null>(null);
  
  const { showSuccess, showError } = useToast();

  const tenantPlan = tenant?.plan || 'enterprise';

  const loadData = async () => {
    if (!tenantId || !deploymentId) return;

    try {
      setLoading(true);
      const [deploymentData, tenantData] = await Promise.all([
        deploymentsApi.getById(tenantId, deploymentId),
        tenantsApi.getById(tenantId)
      ]);
      console.log('=== DEPLOYMENT API RESPONSE ===');
      console.log('Full response:', JSON.stringify(deploymentData, null, 2));
      console.log('Type field:', deploymentData.type);
      console.log('Members field:', deploymentData.members);
      console.log('Tenant plan:', tenantData.plan);
      console.log('===============================');
      setDeployment(deploymentData);
      setTenant(tenantData);
    } catch (error: any) {
      console.error('Failed to load deployment:', error);
      showError('Failed to load deployment details', error.detail || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [tenantId, deploymentId]); // Removed auto-refresh to prevent flickering

  // DB Users handlers (must be before conditional returns)
  const loadDBUsers = async () => {
    if (!tenantId || !deploymentId) return;
    
    setDbUsersLoading(true);
    try {
      const users = await deploymentsApi.listDBUsers(tenantId, deploymentId);
      setDbUsers(users);
    } catch (error: any) {
      showError('Failed to load DB users', error.detail);
    } finally {
      setDbUsersLoading(false);
    }
  };

  const handleCreateUser = async (data: { username: string; db: string; roles: Array<{ db: string; name: string }> }) => {
    if (!tenantId || !deploymentId) return;
    
    setCreatingUser(true);
    try {
      await deploymentsApi.createDBUser(tenantId, deploymentId, data);
      showSuccess('User Created', `Database user ${data.username} has been created successfully with ${data.roles.length} role(s)`);
      setShowCreateUserModal(false);
      await loadDBUsers();
    } catch (error: any) {
      showError('Failed to create user', error.detail);
    } finally {
      setCreatingUser(false);
    }
  };

  const handleViewConnection = async (username: string) => {
    if (!tenantId || !deploymentId) return;
    
    try {
      const connection = await deploymentsApi.getUserConnection(tenantId, deploymentId, username);
      setSelectedUserConnection(connection);
      setShowUserConnectionModal(true);
    } catch (error: any) {
      showError('Failed to load connection', error.detail);
    }
  };

  const handleEditUser = (user: any) => {
    setEditingUser(user);
    setShowEditUserModal(true);
  };

  const handleUpdateUserRoles = async (roles: Array<{ db: string; name: string }>) => {
    if (!tenantId || !deploymentId || !editingUser) return;
    
    setUpdatingUser(true);
    try {
      await deploymentsApi.updateDBUser(tenantId, deploymentId, editingUser.username, { roles });
      showSuccess('Roles Updated', `Roles for ${editingUser.username} have been updated successfully`);
      setShowEditUserModal(false);
      setEditingUser(null);
      await loadDBUsers();
    } catch (error: any) {
      showError('Failed to update roles', error.detail);
    } finally {
      setUpdatingUser(false);
    }
  };

  const handleDeleteUser = async (username: string) => {
    if (!tenantId || !deploymentId) return;
    
    const confirmed = window.confirm(
      `Delete user "${username}"?\n\nThis will:\n- Remove the user from MongoDB\n- Delete the user's credentials\n- Remove all access permissions\n\nThis action cannot be undone.`
    );
    
    if (!confirmed) return;
    
    setDeletingUser(username);
    try {
      await deploymentsApi.deleteDBUser(tenantId, deploymentId, username);
      showSuccess('User Deleted', `User ${username} has been deleted successfully`);
      await loadDBUsers();
    } catch (error: any) {
      showError('Failed to delete user', error.detail);
    } finally {
      setDeletingUser(null);
    }
  };

  // Load DB users when switching to users tab
  useEffect(() => {
    if (activeTab === 'users' && tenantId && deploymentId) {
      loadDBUsers();
    }
  }, [activeTab, tenantId, deploymentId]);

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
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-mongodb-forest">
                {deployment.displayName || deployment.deploymentId}
              </h1>
              {tenantPlan === 'community' ? (
                <span className="badge badge-blue">Community</span>
              ) : (
                <span className="badge badge-green">Enterprise</span>
              )}
            </div>
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
          {(['overview', 'users', 'backup', 'monitoring'] as TabType[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-2 px-1 border-b-2 font-medium text-sm capitalize ${
                activeTab === tab
                  ? 'border-mongodb-green text-mongodb-green'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab === 'users' ? 'DB Users' : tab}
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
              {deployment.type === 'ReplicaSet' && deployment.members && (
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
            <p className="text-sm text-gray-500 mt-2">
              Deployment Type: <span className="font-semibold">{deployment.type || '(not set in API response)'}</span>
              {deployment.members && ` | Current Members: ${deployment.members}`}
            </p>
            {!deployment.type && (
              <p className="text-xs text-red-600 mt-1">
                ⚠️ API is not returning 'type' field. Please restart the FastAPI service after deploying the fix.
              </p>
            )}
          </div>

          <ConnectionInfo tenantId={deployment.tenantId} deploymentId={deployment.deploymentId} />
        </div>
      )}

      {activeTab === 'monitoring' && (
        <div>
          <PrometheusCard tenantId={deployment.tenantId} deploymentId={deployment.deploymentId} />
        </div>
      )}

      {activeTab === 'users' && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-2xl font-semibold text-mongodb-forest">Database Users</h2>
            <button onClick={() => setShowCreateUserModal(true)} className="btn-primary">
              Create DB User
            </button>
          </div>

          {dbUsersLoading ? (
            <div className="card">
              <p className="text-gray-500">Loading users...</p>
            </div>
          ) : dbUsers.length === 0 ? (
            <div className="card text-center py-12">
              <p className="text-gray-500 mb-4">No database users yet</p>
              <button onClick={() => setShowCreateUserModal(true)} className="btn-primary">
                Create First User
              </button>
            </div>
          ) : (
            <div className="card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Username
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Database
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Roles
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Created At
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {dbUsers.map((user) => (
                      <tr key={user.username}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {user.username}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {user.db}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-500">
                          <div className="flex flex-wrap gap-1">
                            {user.roles.map((r: any, idx: number) => (
                              <span key={idx} className="badge badge-gray text-xs">
                                {r.name}@{r.db}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {new Date(user.createdAt).toLocaleString()}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <div className="flex items-center gap-3">
                            <button
                              onClick={() => handleViewConnection(user.username)}
                              className="text-mongodb-green hover:text-mongodb-green-dark font-medium"
                            >
                              View Connection
                            </button>
                            <button
                              onClick={() => handleEditUser(user)}
                              className="text-blue-600 hover:text-blue-800 font-medium"
                            >
                              Edit Roles
                            </button>
                            <button
                              onClick={() => handleDeleteUser(user.username)}
                              disabled={deletingUser === user.username}
                              className="text-red-600 hover:text-red-800 font-medium disabled:opacity-50"
                            >
                              {deletingUser === user.username ? 'Deleting...' : 'Delete'}
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'backup' && (
        <BackupPanel 
          tenantId={deployment.tenantId} 
          deploymentId={deployment.deploymentId}
          tenantPlan={tenantPlan}
        />
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

      {/* DB Users Modals */}
      <CreateUserModal
        open={showCreateUserModal}
        onClose={() => setShowCreateUserModal(false)}
        onSubmit={handleCreateUser}
        loading={creatingUser}
      />

      <EditUserModal
        open={showEditUserModal}
        onClose={() => {
          setShowEditUserModal(false);
          setEditingUser(null);
        }}
        onSubmit={handleUpdateUserRoles}
        loading={updatingUser}
        username={editingUser?.username || ''}
        db={editingUser?.db || ''}
        currentRoles={editingUser?.roles || []}
      />

      <UserConnectionModal
        open={showUserConnectionModal}
        onClose={() => {
          setShowUserConnectionModal(false);
          setSelectedUserConnection(null);
        }}
        username={selectedUserConnection?.username || ''}
        externalUri={selectedUserConnection?.externalUri}
        internalUri={selectedUserConnection?.internalUri}
      />
    </div>
  );
}
