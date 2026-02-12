import { Fragment, useState } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon } from '@heroicons/react/24/outline';

interface CreateUserModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: { username: string; db: string; rolePreset: string }) => Promise<void>;
  loading?: boolean;
}

export function CreateUserModal({ open, onClose, onSubmit, loading = false }: CreateUserModalProps) {
  const [username, setUsername] = useState('');
  const [db, setDb] = useState('appdb');
  const [rolePreset, setRolePreset] = useState('readWrite');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!username.trim() || !db.trim()) {
      return;
    }

    await onSubmit({ username: username.trim(), db: db.trim(), rolePreset });
    
    // Reset form
    setUsername('');
    setDb('appdb');
    setRolePreset('readWrite');
  };

  const handleClose = () => {
    if (!loading) {
      setUsername('');
      setDb('appdb');
      setRolePreset('readWrite');
      onClose();
    }
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
                    Create DB User
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
                  <div>
                    <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
                      Username
                    </label>
                    <input
                      type="text"
                      id="username"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      className="input w-full"
                      placeholder="appUser"
                      required
                      disabled={loading}
                    />
                  </div>

                  <div>
                    <label htmlFor="db" className="block text-sm font-medium text-gray-700 mb-1">
                      Database
                    </label>
                    <input
                      type="text"
                      id="db"
                      value={db}
                      onChange={(e) => setDb(e.target.value)}
                      className="input w-full"
                      placeholder="appdb"
                      required
                      disabled={loading}
                    />
                  </div>

                  <div>
                    <label htmlFor="rolePreset" className="block text-sm font-medium text-gray-700 mb-1">
                      Role
                    </label>
                    <select
                      id="rolePreset"
                      value={rolePreset}
                      onChange={(e) => setRolePreset(e.target.value)}
                      className="input w-full"
                      disabled={loading}
                    >
                      <option value="readWrite">Read/Write on this DB</option>
                      <option value="read">Read-only on this DB</option>
                      <option value="dbAdmin">DB Admin on this DB</option>
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                      Role will be applied to the specified database only
                    </p>
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
                      disabled={loading || !username.trim() || !db.trim()}
                      className="btn-primary"
                    >
                      {loading ? 'Creating...' : 'Create User'}
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
