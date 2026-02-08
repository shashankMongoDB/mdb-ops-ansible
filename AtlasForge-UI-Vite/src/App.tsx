import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ToastProvider } from './components/Toast';
import { Layout } from './components/Layout';
import { TenantsPage } from './pages/TenantsPage';
import { TenantDetailsPage } from './pages/TenantDetailsPage';
import { DeploymentDetailsPage } from './pages/DeploymentDetailsPage';
import { AboutPage } from './pages/AboutPage';

function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<TenantsPage />} />
            <Route path="/tenants/:tenantId" element={<TenantDetailsPage />} />
            <Route path="/tenants/:tenantId/deployments/:deploymentId" element={<DeploymentDetailsPage />} />
            <Route path="/about" element={<AboutPage />} />
          </Routes>
        </Layout>
      </ToastProvider>
    </BrowserRouter>
  );
}

export default App;
