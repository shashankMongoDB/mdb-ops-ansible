import { Fragment } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon, ClipboardDocumentIcon, CheckIcon } from '@heroicons/react/24/outline';
import { useState } from 'react';

interface PasswordRevealModalProps {
  open: boolean;
  onClose: () => void;
  username: string;
  password: string;
  onCopy: (text: string) => void;
}

export function PasswordRevealModal({ open, onClose, username, password, onCopy }: PasswordRevealModalProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    onCopy(password);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleClose = () => {
    setCopied(false);
    onClose();
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
          <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
        </Transition.Child>

        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Transition.Child
            as={Fragment}
            enter="ease-out duration-300"
            enterFrom="opacity-0 scale-95"
            enterTo="opacity-100 scale-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100 scale-100"
            leaveTo="opacity-0 scale-95"
          >
            <Dialog.Panel className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
              <div className="flex items-center justify-between mb-4">
                <Dialog.Title className="text-xl font-semibold text-gray-900">
                  Prometheus Password Revealed
                </Dialog.Title>
                <button onClick={handleClose} className="text-gray-400 hover:text-gray-600">
                  <XMarkIcon className="h-6 w-6" />
                </button>
              </div>

              {/* Warning */}
              <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                <p className="text-sm text-yellow-800 font-medium">
                  ⚠️ This password is shown only once. Copy and save it securely now.
                </p>
                <p className="text-xs text-yellow-700 mt-1">
                  After closing this dialog, you won't be able to see the full password again until you rotate it.
                </p>
              </div>

              {/* Username */}
              <div className="mb-3">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Username:
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={username}
                    readOnly
                    className="input font-mono text-sm flex-1 bg-gray-50"
                  />
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(username);
                    }}
                    className="btn-secondary text-xs px-3"
                  >
                    Copy
                  </button>
                </div>
              </div>

              {/* Password */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Password:
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={password}
                    readOnly
                    className="input font-mono text-sm flex-1 bg-gray-50"
                  />
                  <button
                    onClick={handleCopy}
                    className={`btn-primary text-xs px-3 flex items-center gap-1 ${copied ? 'bg-green-600' : ''}`}
                  >
                    {copied ? (
                      <>
                        <CheckIcon className="h-4 w-4" />
                        Copied!
                      </>
                    ) : (
                      <>
                        <ClipboardDocumentIcon className="h-4 w-4" />
                        Copy
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Instructions */}
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-md mb-4">
                <p className="text-sm text-blue-800">
                  <span className="font-medium">Next steps:</span>
                </p>
                <ol className="text-sm text-blue-800 mt-2 space-y-1 list-decimal list-inside">
                  <li>Copy this password to your password manager</li>
                  <li>Use it in your Prometheus configuration</li>
                  <li>Close this dialog when done</li>
                </ol>
              </div>

              {/* Close Button */}
              <div className="flex justify-end">
                <button onClick={handleClose} className="btn-primary">
                  I've Saved the Password
                </button>
              </div>
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition>
  );
}
