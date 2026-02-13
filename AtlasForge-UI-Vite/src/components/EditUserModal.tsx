import { Fragment, useState, useEffect } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon } from '@heroicons/react/24/outline';

interface EditUserModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (roles: Array<{ db: string; name: string }>) => Promise<void>;
  loading?: boolean;
  username: string;
  db: string;
  currentRoles: Array<{ db: string; name: string }>;
}

// Common MongoDB roles
const ADMIN_ROLES = [
  { name: 'clusterMonitor', description: 'Monitor cluster metrics' },
  { name: 'readAnyDatabase', description: 'Read any database' },
  { name: 'readWriteAnyDatabase', description: 'Read/write any database' },
  { name: 'userAdminAnyDatabase', description: 'Manage users on any database' },
  { name: 'dbAdminAnyDatabase', description: 'Admin any database' },
  { name: 'backup', description: 'Backup operations' },
  { name: 'restore', description: 'Restore operations' },
  { name: 'root', description: 'Superuser (all privileges)' },
];

const DB_ROLES = [
  { name: 'read', description: 'Read data' },
  { name: 'readWrite', description: 'Read and write data' },
  { name: 'dbAdmin', description: 'Database administration' },
  { name: 'dbOwner', description: 'Database owner (all privileges)' },
  { name: 'userAdmin', description: 'Manage users' },
];

export function EditUserModal({ 
  open, 
  onClose, 
  onSubmit, 
  loading = false,
  username,
  db,
  currentRoles
}: EditUserModalProps) {
  const [selectedDbRoles, setSelectedDbRoles] = useState<string[]>([]);
  const [selectedAdminRoles, setSelectedAdminRoles] = useState<string[]>([]);

  // Initialize selected roles from current roles
  useEffect(() => {
    if (open && currentRoles) {
      const dbRoles = currentRoles.filter(r => r.db === db).map(r => r.name);
      const adminRoles = currentRoles.filter(r => r.db === 'admin').map(r => r.name);
      setSelectedDbRoles(dbRoles);
      setSelectedAdminRoles(adminRoles);
    }
  }, [open, currentRoles, db]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Build roles array
    const roles: Array<{ db: string; name: string }> = [];
    
    // Add database roles
    selectedDbRoles.forEach(roleName => {
      roles.push({ db, name: roleName });
    });
    
    // Add admin roles
    selectedAdminRoles.forEach(roleName => {
      roles.push({ db: 'admin', name: roleName });
    });

    // Must have at least one role
    if (roles.length === 0) {
      alert('Please select at least one role');
      return;
    }

    await onSubmit(roles);
  };

  const handleClose = () => {
    if (!loading) {
      onClose();
    }
  };

  const handleDbRoleToggle = (roleName: string) => {
    setSelectedDbRoles(prev => 
      prev.includes(roleName) 
        ? prev.filter(r => r !== roleName)
        : [...prev, roleName]
    );
  };

  const handleAdminRoleToggle = (roleName: string) => {
    setSelectedAdminRoles(prev => 
      prev.includes(roleName) 
        ? prev.filter(r => r !== roleName)
        : [...prev, roleName]
    );
  };

  const removeDbRole = (roleName: string) => {
    setSelectedDbRoles(prev => prev.filter(r => r !== roleName));
  };

  const removeAdminRole = (roleName: string) => {
    setSelectedAdminRoles(prev => prev.filter(r => r !== roleName));
  };

  return (
    <Transition appear show={open} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={handleClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black bg-opacity-25" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-lg bg-white p-6 shadow-xl transition-all">
                <div className="flex items-center justify-between mb-4">
                  <Dialog.Title className="text-lg font-semibold text-gray-900">
                    Edit Roles for {username}
                  </Dialog.Title>
                  <button
                    onClick={handleClose}
                    disabled={loading}
                    className="text-gray-400 hover:text-gray-500"
                  >
                    <XMarkIcon className="h-5 w-5" />
                  </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="bg-gray-50 p-3 rounded border border-gray-200">
                    <p className="text-sm text-gray-600">
                      <strong>Database:</strong> {db}
                    </p>
                  </div>

                  {/* Database Roles */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Database Roles ({db})
                    </label>
                    
                    {/* Selected badges */}
                    {selectedDbRoles.length > 0 && (
                      <div className="flex flex-wrap gap-2 mb-2 p-2 bg-gray-50 rounded border border-gray-200 min-h-[40px]">
                        {selectedDbRoles.map((roleName) => (
                          <span
                            key={roleName}
                            className="inline-flex items-center gap-1 px-3 py-1 bg-mongodb-green text-white text-xs font-medium rounded-full"
                          >
                            {roleName}@{db}
                            <button
                              type="button"
                              onClick={() => removeDbRole(roleName)}
                              disabled={loading}
                              className="hover:bg-mongodb-green-dark rounded-full p-0.5"
                            >
                              <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                              </svg>
                            </button>
                          </span>
                        ))}
                      </div>
                    )}
                    
                    {/* Clickable list */}
                    <div className="border border-gray-200 rounded-md max-h-40 overflow-y-auto">
                      {DB_ROLES.map((role) => (
                        <label
                          key={role.name}
                          className={`flex items-start gap-3 p-3 cursor-pointer hover:bg-gray-50 border-b border-gray-100 last:border-b-0 ${
                            selectedDbRoles.includes(role.name) ? 'bg-green-50' : ''
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={selectedDbRoles.includes(role.name)}
                            onChange={() => handleDbRoleToggle(role.name)}
                            disabled={loading}
                            className="mt-1"
                          />
                          <div className="flex-1">
                            <div className="text-sm font-medium text-gray-900">
                              {role.name}@{db}
                            </div>
                            <div className="text-xs text-gray-500">{role.description}</div>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Admin Roles */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Admin Roles (Optional)
                    </label>
                    
                    {/* Selected badges */}
                    {selectedAdminRoles.length > 0 && (
                      <div className="flex flex-wrap gap-2 mb-2 p-2 bg-gray-50 rounded border border-gray-200 min-h-[40px]">
                        {selectedAdminRoles.map((roleName) => (
                          <span
                            key={roleName}
                            className="inline-flex items-center gap-1 px-3 py-1 bg-gray-700 text-white text-xs font-medium rounded-full"
                          >
                            {roleName}@admin
                            <button
                              type="button"
                              onClick={() => removeAdminRole(roleName)}
                              disabled={loading}
                              className="hover:bg-gray-800 rounded-full p-0.5"
                            >
                              <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                              </svg>
                            </button>
                          </span>
                        ))}
                      </div>
                    )}
                    
                    {/* Clickable list */}
                    <div className="border border-gray-200 rounded-md max-h-48 overflow-y-auto">
                      {ADMIN_ROLES.map((role) => (
                        <label
                          key={role.name}
                          className={`flex items-start gap-3 p-3 cursor-pointer hover:bg-gray-50 border-b border-gray-100 last:border-b-0 ${
                            selectedAdminRoles.includes(role.name) ? 'bg-gray-100' : ''
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={selectedAdminRoles.includes(role.name)}
                            onChange={() => handleAdminRoleToggle(role.name)}
                            disabled={loading}
                            className="mt-1"
                          />
                          <div className="flex-1">
                            <div className="text-sm font-medium text-gray-900">
                              {role.name}@admin
                            </div>
                            <div className="text-xs text-gray-500">{role.description}</div>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>

                  <div className="flex justify-end gap-3 pt-4">
                    <button
                      type="button"
                      onClick={handleClose}
                      disabled={loading}
                      className="btn-secondary"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={loading || (selectedDbRoles.length === 0 && selectedAdminRoles.length === 0)}
                      className="btn-primary"
                    >
                      {loading ? 'Updating...' : 'Update Roles'}
                    </button>
                  </div>
                </form>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}
