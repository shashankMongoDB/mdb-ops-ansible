import { Fragment, useState } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon, ClipboardDocumentIcon, CheckIcon } from '@heroicons/react/24/outline';

interface UserConnectionModalProps {
  open: boolean;
  onClose: () => void;
  username: string;
  externalUri?: string | null;
  externalPrimaryUri?: string | null;
  externalSecondaryUri?: string | null;
  internalUri?: string | null;
}

export function UserConnectionModal({ 
  open, 
  onClose, 
  username,
  externalUri,
  externalPrimaryUri,
  externalSecondaryUri,
  internalUri
}: UserConnectionModalProps) {
  const [connectionMode, setConnectionMode] = useState<'primary' | 'secondary'>('primary');
  const [copiedExternal, setCopiedExternal] = useState(false);
  const [copiedInternal, setCopiedInternal] = useState(false);
  const [copiedExternalMongosh, setCopiedExternalMongosh] = useState(false);
  const [copiedInternalMongosh, setCopiedInternalMongosh] = useState(false);

  const handleCopy = async (text: string, type: 'external' | 'internal' | 'externalMongosh' | 'internalMongosh') => {
    try {
      // Try modern clipboard API first
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
      }
      
      if (type === 'external') {
        setCopiedExternal(true);
        setTimeout(() => setCopiedExternal(false), 2000);
      } else if (type === 'internal') {
        setCopiedInternal(true);
        setTimeout(() => setCopiedInternal(false), 2000);
      } else if (type === 'externalMongosh') {
        setCopiedExternalMongosh(true);
        setTimeout(() => setCopiedExternalMongosh(false), 2000);
      } else if (type === 'internalMongosh') {
        setCopiedInternalMongosh(true);
        setTimeout(() => setCopiedInternalMongosh(false), 2000);
      }
    } catch (err) {
      console.error('Failed to copy:', err);
      alert('Failed to copy to clipboard. Please copy manually.');
    }
  };

  const withReadPreference = (uri: string, mode: 'primary' | 'secondary') => {
    const pref = mode === 'primary' ? 'primary' : 'secondaryPreferred';
    if (uri.includes('readPreference=')) {
      return uri.replace(/readPreference=[^&]*/g, `readPreference=${pref}`);
    }
    return uri.includes('?') ? `${uri}&readPreference=${pref}` : `${uri}?readPreference=${pref}`;
  };

  const selectedExternalUri = connectionMode === 'primary'
    ? (externalPrimaryUri || (externalUri ? withReadPreference(externalUri, 'primary') : null))
    : (externalSecondaryUri || (externalUri ? withReadPreference(externalUri, 'secondary') : null));
  const selectedInternalUri = internalUri ? withReadPreference(internalUri, connectionMode) : null;

  return (
    <Transition appear show={open} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
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
              <Dialog.Panel className="w-full max-w-2xl transform overflow-hidden rounded-lg bg-white p-6 shadow-xl transition-all">
                <div className="flex items-center justify-between mb-4">
                  <Dialog.Title className="text-lg font-semibold text-gray-900">
                    Connection URIs for {username}
                  </Dialog.Title>
                  <button
                    onClick={onClose}
                    className="text-gray-400 hover:text-gray-500"
                  >
                    <XMarkIcon className="h-5 w-5" />
                  </button>
                </div>

                <div className="space-y-6">
                  <div>
                    <label className="text-sm font-medium text-gray-700 block mb-2">Connection Target</label>
                    <div className="flex gap-3">
                      <label className="inline-flex items-center gap-2 text-sm">
                        <input
                          type="radio"
                          name="connection-mode"
                          checked={connectionMode === 'primary'}
                          onChange={() => setConnectionMode('primary')}
                        />
                        Primary (read/write)
                      </label>
                      <label className="inline-flex items-center gap-2 text-sm">
                        <input
                          type="radio"
                          name="connection-mode"
                          checked={connectionMode === 'secondary'}
                          onChange={() => setConnectionMode('secondary')}
                        />
                        Secondary preferred (reads)
                      </label>
                    </div>
                  </div>

                  {/* External Connection */}
                  {selectedExternalUri && (
                    <div>
                      <h3 className="text-sm font-semibold text-gray-900 mb-3">
                        External Connection <span className="text-xs text-gray-500 font-normal">(from VPC clients)</span>
                      </h3>
                      
                      {/* External URI */}
                      <div className="mb-3">
                        <div className="flex items-center justify-between mb-2">
                          <label className="text-xs font-medium text-gray-600">Connection String</label>
                          <button
                            onClick={() => handleCopy(selectedExternalUri, 'external')}
                            className="flex items-center gap-1 text-xs text-mongodb-green hover:text-mongodb-green-dark"
                          >
                            {copiedExternal ? (
                              <>
                                <CheckIcon className="h-3 w-3" />
                                Copied
                              </>
                            ) : (
                              <>
                                <ClipboardDocumentIcon className="h-3 w-3" />
                                Copy
                              </>
                            )}
                          </button>
                        </div>
                        <div className="bg-mongodb-green bg-opacity-5 p-3 rounded-md border border-mongodb-green font-mono text-xs break-all">
                          {selectedExternalUri}
                        </div>
                      </div>

                      {/* External mongosh Command */}
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <label className="text-xs font-medium text-gray-600">mongosh Command</label>
                          <button
                            onClick={() => handleCopy(`mongosh "${selectedExternalUri}"`, 'externalMongosh')}
                            className="flex items-center gap-1 text-xs text-mongodb-green hover:text-mongodb-green-dark"
                          >
                            {copiedExternalMongosh ? (
                              <>
                                <CheckIcon className="h-3 w-3" />
                                Copied
                              </>
                            ) : (
                              <>
                                <ClipboardDocumentIcon className="h-3 w-3" />
                                Copy
                              </>
                            )}
                          </button>
                        </div>
                        <div className="bg-gray-900 p-3 rounded-md font-mono text-xs text-green-400 break-all">
                          mongosh "{selectedExternalUri}"
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Internal Connection */}
                  {selectedInternalUri && (
                    <div className="pt-4 border-t">
                      <h3 className="text-sm font-semibold text-gray-900 mb-3">
                        Internal Connection <span className="text-xs text-gray-500 font-normal">(from inside K8s cluster)</span>
                      </h3>
                      
                      {/* Internal URI */}
                      <div className="mb-3">
                        <div className="flex items-center justify-between mb-2">
                          <label className="text-xs font-medium text-gray-600">Connection String</label>
                          <button
                            onClick={() => handleCopy(selectedInternalUri, 'internal')}
                            className="flex items-center gap-1 text-xs text-mongodb-green hover:text-mongodb-green-dark"
                          >
                            {copiedInternal ? (
                              <>
                                <CheckIcon className="h-3 w-3" />
                                Copied
                              </>
                            ) : (
                              <>
                                <ClipboardDocumentIcon className="h-3 w-3" />
                                Copy
                              </>
                            )}
                          </button>
                        </div>
                        <div className="bg-gray-50 p-3 rounded-md border border-gray-200 font-mono text-xs break-all">
                          {selectedInternalUri}
                        </div>
                      </div>

                      {/* Internal mongosh Command */}
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <label className="text-xs font-medium text-gray-600">mongosh Command</label>
                          <button
                            onClick={() => handleCopy(`mongosh "${selectedInternalUri}"`, 'internalMongosh')}
                            className="flex items-center gap-1 text-xs text-mongodb-green hover:text-mongodb-green-dark"
                          >
                            {copiedInternalMongosh ? (
                              <>
                                <CheckIcon className="h-3 w-3" />
                                Copied
                              </>
                            ) : (
                              <>
                                <ClipboardDocumentIcon className="h-3 w-3" />
                                Copy
                              </>
                            )}
                          </button>
                        </div>
                        <div className="bg-gray-900 p-3 rounded-md font-mono text-xs text-green-400 break-all">
                          mongosh "{selectedInternalUri}"
                        </div>
                      </div>
                    </div>
                  )}

                  {!selectedExternalUri && !selectedInternalUri && (
                    <div className="text-center py-8 text-gray-500">
                      No connection URIs available
                    </div>
                  )}
                </div>

                <div className="flex justify-end pt-4">
                  <button onClick={onClose} className="btn-secondary">
                    Close
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}
