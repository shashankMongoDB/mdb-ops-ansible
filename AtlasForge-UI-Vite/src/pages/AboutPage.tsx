import { config } from '@/lib/config';

export function AboutPage() {
  return (
    <div>
      <h1 className="text-3xl font-bold text-mongodb-forest mb-2">About AtlasForge UI</h1>
      <p className="text-mongodb-slate mb-8">MongoDB Control Plane Management Interface</p>

      <div className="card mb-6">
        <h2 className="text-2xl font-semibold text-mongodb-forest mb-4">Overview</h2>
        <p className="text-gray-700 leading-relaxed">
          AtlasForge UI is a MongoDB-themed web interface for managing your MDBaaS (MongoDB Database as a Service)
          control plane. It provides a comprehensive interface for managing tenants, MongoDB deployments, and day-2
          operations.
        </p>
      </div>

      <div className="card mb-6">
        <h2 className="text-2xl font-semibold text-mongodb-forest mb-4">Features</h2>
        <ul className="space-y-2 text-gray-700">
          <li className="flex items-start">
            <span className="text-mongodb-green mr-2">✓</span>
            Tenant management: Onboard and manage multiple tenants
          </li>
          <li className="flex items-start">
            <span className="text-mongodb-green mr-2">✓</span>
            Deployment lifecycle: Create, scale, upgrade, and manage MongoDB deployments
          </li>
          <li className="flex items-start">
            <span className="text-mongodb-green mr-2">✓</span>
            Real-time status monitoring with auto-refresh
          </li>
          <li className="flex items-start">
            <span className="text-mongodb-green mr-2">✓</span>
            Connection information and connection string management
          </li>
          <li className="flex items-start">
            <span className="text-mongodb-green mr-2">✓</span>
            Prometheus monitoring integration
          </li>
          <li className="flex items-start">
            <span className="text-mongodb-green mr-2">✓</span>
            Backup enrollment tracking
          </li>
        </ul>
      </div>

      <div className="card mb-6">
        <h2 className="text-2xl font-semibold text-mongodb-forest mb-4">Deployment Types</h2>
        <div className="flex gap-3 flex-wrap">
          <span className="badge badge-green">Standalone</span>
          <span className="badge badge-green">Replica Set</span>
          <span className="badge badge-gray">Sharded Cluster (Coming Soon)</span>
        </div>
      </div>

      <div className="card mb-6">
        <h2 className="text-2xl font-semibold text-mongodb-forest mb-4">Configuration</h2>
        <div className="space-y-3">
          <div>
            <p className="text-sm font-medium text-gray-700">API Base URL:</p>
            <p className="text-sm text-mongodb-slate font-mono">{config.apiBaseUrl}</p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-700">Environment:</p>
            <span className="badge badge-gray">{config.environment}</span>
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="text-2xl font-semibold text-mongodb-forest mb-4">Technology Stack</h2>
        <ul className="space-y-2 text-gray-700">
          <li>• Vite + React + TypeScript</li>
          <li>• Tailwind CSS</li>
          <li>• React Router</li>
          <li>• HeadlessUI Components</li>
          <li>• Axios for API Integration</li>
        </ul>
        <p className="text-xs text-mongodb-slate mt-6">Version 1.0.0</p>
      </div>
    </div>
  );
}
