import { Fragment, useState } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon, ClipboardDocumentIcon, CheckIcon } from '@heroicons/react/24/outline';

interface UserConnectionModalProps {
  open: boolean;
  onClose: () => void;
  username: string;
  externalUri?: string | null;
  internalUri?: string | null;
}

export function UserConnectionModal({ 
  open, 
  onClose, 
  username,
  externalUri,
  internalUri
}: UserConnectionModalProps) {
  const [copiedExternal, setCopiedExternal] = useState(false);
  const [copiedInternal, setCopiedInternal] = useState(false);

  const handleCopy = async (text: string, type: 'external' | 'internal') => {
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
      } else {
        setCopiedInternal(true);
        setTimeout(() => setCopiedInternal(false), 2000);
      }
    } catch (err) {
      console.error('Failed to copy:', err);
      alert('Failed to copy to clipboard. Please copy manually.');
    }
  };

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

                <div className="space-y-4">
                  {/* External URI */}
                  {externalUri && (
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="text-sm font-medium text-gray-700">
                          External URI
                          <span className="text-xs text-gray-500 ml-2">(from VPC clients)</span>
                        </label>
                        <button
                          onClick={() => handleCopy(externalUri, 'external')}
                          className="flex items-center gap-1 text-sm text-mongodb-green hover:text-mongodb-green-dark"
                        >
                          {copiedExternal ? (
                            <>
                              <CheckIcon className="h-4 w-4" />
                              Copied
                            </>
                          ) : (
                            <>
                              <ClipboardDocumentIcon className="h-4 w-4" />
                              Copy
                            </>
                          )}
                        </button>
                      </div>
                      <div className="bg-mongodb-green bg-opacity-5 p-3 rounded-md border border-mongodb-green font-mono text-xs break-all">
                        {externalUri}
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        Use from VMs or apps that can reach the node IP and port
                      </p>
                    </div>
                  )}

                  {/* Internal URI */}
                  {internalUri && (
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="text-sm font-medium text-gray-700">
                          Internal URI
                          <span className="text-xs text-gray-500 ml-2">(from inside K8s cluster)</span>
                        </label>
                        <button
                          onClick={() => handleCopy(internalUri, 'internal')}
                          className="flex items-center gap-1 text-sm text-mongodb-green hover:text-mongodb-green-dark"
                        >
                          {copiedInternal ? (
                            <>
                              <CheckIcon className="h-4 w-4" />
                              Copied
                            </>
                          ) : (
                            <>
                              <ClipboardDocumentIcon className="h-4 w-4" />
                              Copy
                            </>
                          )}
                        </button>
                      </div>
                      <div className="bg-gray-50 p-3 rounded-md border border-gray-200 font-mono text-xs break-all">
                        {internalUri}
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        Use from apps running inside the Kubernetes cluster
                      </p>
                    </div>
                  )}

                  {!externalUri && !internalUri && (
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
