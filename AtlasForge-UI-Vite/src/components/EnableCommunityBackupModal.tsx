import { Fragment, useState } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon, InformationCircleIcon } from '@heroicons/react/24/outline';

interface EnableCommunityBackupModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (config: BackupConfig) => Promise<void>;
  loading?: boolean;
  deploymentId: string;
}

interface BackupConfig {
  s3Bucket: string;
  s3Prefix: string;
  s3Region: string;
  schedule: string;
  retentionDays: number;
}

export function EnableCommunityBackupModal({ 
  open, 
  onClose, 
  onSubmit, 
  loading = false,
  deploymentId
}: EnableCommunityBackupModalProps) {
  const [s3Bucket, setS3Bucket] = useState('');
  const [s3Prefix, setS3Prefix] = useState(`community-mongodb-backup/${deploymentId}/snapshots`);
  const [s3Region, setS3Region] = useState('us-east-1');
  const [schedule, setSchedule] = useState('0 */4 * * *');
  const [retentionDays, setRetentionDays] = useState(7);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!s3Bucket.trim()) {
      alert('S3 Bucket is required');
      return;
    }

    await onSubmit({
      s3Bucket: s3Bucket.trim(),
      s3Prefix: s3Prefix.trim(),
      s3Region: s3Region.trim(),
      schedule: schedule.trim(),
      retentionDays
    });
  };

  const handleClose = () => {
    if (!loading) {
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
              <Dialog.Panel className="w-full max-w-2xl transform overflow-hidden rounded-lg bg-white p-6 shadow-xl transition-all">
                <div className="flex items-center justify-between mb-4">
                  <Dialog.Title className="text-lg font-semibold text-gray-900">
                    Enable Community Backup
                  </Dialog.Title>
                  <button
                    onClick={handleClose}
                    disabled={loading}
                    className="text-gray-400 hover:text-gray-500"
                  >
                    <XMarkIcon className="h-5 w-5" />
                  </button>
                </div>

                {/* Prerequisites Section */}
                <div className="bg-blue-50 border border-blue-200 rounded-md p-4 mb-6">
                  <div className="flex items-start gap-2">
                    <InformationCircleIcon className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-sm font-semibold text-blue-900 mb-2">Prerequisites</h4>
                      <ul className="text-xs text-blue-800 space-y-1 list-disc list-inside">
                        <li>The S3 bucket must already exist in your AWS account</li>
                        <li>The backup CronJob requires IAM permissions: <code className="bg-blue-100 px-1 rounded">s3:PutObject</code>, <code className="bg-blue-100 px-1 rounded">s3:ListBucket</code>, <code className="bg-blue-100 px-1 rounded">s3:GetObject</code>, <code className="bg-blue-100 px-1 rounded">s3:DeleteObject</code></li>
                        <li><strong>Recommended:</strong> Use IRSA (IAM Roles for Service Accounts) for EKS clusters</li>
                        <li>Alternative: Configure IAM credentials via node role or Kubernetes secrets</li>
                      </ul>
                      <p className="text-xs text-blue-700 mt-2">
                        💡 <strong>What happens:</strong> The platform will create a Kubernetes CronJob that runs <code className="bg-blue-100 px-1 rounded">mongodump</code> on your schedule and uploads compressed backups to S3.
                      </p>
                    </div>
                  </div>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                  {/* S3 Bucket */}
                  <div>
                    <label htmlFor="s3Bucket" className="block text-sm font-medium text-gray-700 mb-1">
                      S3 Bucket Name <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      id="s3Bucket"
                      value={s3Bucket}
                      onChange={(e) => setS3Bucket(e.target.value)}
                      className="input w-full"
                      placeholder="my-mongodb-backups"
                      required
                      disabled={loading}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      The S3 bucket must already exist
                    </p>
                  </div>

                  {/* S3 Prefix */}
                  <div>
                    <label htmlFor="s3Prefix" className="block text-sm font-medium text-gray-700 mb-1">
                      S3 Prefix / Folder Path
                    </label>
                    <input
                      type="text"
                      id="s3Prefix"
                      value={s3Prefix}
                      onChange={(e) => setS3Prefix(e.target.value)}
                      className="input w-full"
                      placeholder="community-mongodb-backup/my-deployment/snapshots"
                      disabled={loading}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Optional folder path within the bucket. Default: <code className="bg-gray-100 px-1 rounded">community-mongodb-backup/{deploymentId}/snapshots</code>
                    </p>
                  </div>

                  {/* S3 Region */}
                  <div>
                    <label htmlFor="s3Region" className="block text-sm font-medium text-gray-700 mb-1">
                      S3 Region
                    </label>
                    <select
                      id="s3Region"
                      value={s3Region}
                      onChange={(e) => setS3Region(e.target.value)}
                      className="input w-full"
                      disabled={loading}
                    >
                      <option value="us-east-1">us-east-1 (N. Virginia)</option>
                      <option value="us-east-2">us-east-2 (Ohio)</option>
                      <option value="us-west-1">us-west-1 (N. California)</option>
                      <option value="us-west-2">us-west-2 (Oregon)</option>
                      <option value="eu-west-1">eu-west-1 (Ireland)</option>
                      <option value="eu-central-1">eu-central-1 (Frankfurt)</option>
                      <option value="ap-southeast-1">ap-southeast-1 (Singapore)</option>
                      <option value="ap-northeast-1">ap-northeast-1 (Tokyo)</option>
                    </select>
                  </div>

                  {/* Schedule */}
                  <div>
                    <label htmlFor="schedule" className="block text-sm font-medium text-gray-700 mb-1">
                      Backup Schedule (Cron)
                    </label>
                    <input
                      type="text"
                      id="schedule"
                      value={schedule}
                      onChange={(e) => setSchedule(e.target.value)}
                      className="input w-full font-mono"
                      placeholder="0 */4 * * *"
                      disabled={loading}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Cron format: <code className="bg-gray-100 px-1 rounded">0 */4 * * *</code> = Every 4 hours. Use <a href="https://crontab.guru" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">crontab.guru</a> for help.
                    </p>
                  </div>

                  {/* Retention Days */}
                  <div>
                    <label htmlFor="retentionDays" className="block text-sm font-medium text-gray-700 mb-1">
                      Retention (Days)
                    </label>
                    <input
                      type="number"
                      id="retentionDays"
                      value={retentionDays}
                      onChange={(e) => setRetentionDays(parseInt(e.target.value) || 7)}
                      className="input w-full"
                      min="1"
                      max="365"
                      disabled={loading}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Backups older than this will be automatically deleted
                    </p>
                  </div>

                  {/* IAM Reminder */}
                  <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3">
                    <p className="text-xs text-yellow-800">
                      ⚠️ <strong>Important:</strong> Ensure the Kubernetes backup service account has IAM access to the S3 bucket before enabling. Without proper permissions, backups will fail.
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
                      disabled={loading || !s3Bucket.trim()}
                      className="btn-primary"
                    >
                      {loading ? 'Enabling...' : 'Enable Backup'}
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
