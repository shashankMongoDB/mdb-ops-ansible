import { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { HomeIcon, InformationCircleIcon } from '@heroicons/react/24/outline';
import { config } from '@/lib/config';

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation();

  const navItems = [
    { name: 'Tenants', path: '/', icon: HomeIcon },
    { name: 'About', path: '/about', icon: InformationCircleIcon },
  ];

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <div className="min-h-screen flex bg-mongodb-gray-light">
      {/* Sidebar */}
      <div className="w-64 bg-mongodb-forest text-white flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-mongodb-green-dark">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🍃</span>
            <span className="text-xl font-semibold">AtlasForge</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4">
          <ul className="space-y-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <li key={item.path}>
                  <Link
                    to={item.path}
                    className={`flex items-center gap-3 px-4 py-2.5 rounded-md transition-colors ${
                      isActive(item.path)
                        ? 'bg-mongodb-green text-white'
                        : 'text-mongodb-slate-light hover:bg-mongodb-green-dark'
                    }`}
                  >
                    <Icon className="h-5 w-5" />
                    <span>{item.name}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Environment Badge */}
        <div className="p-4 border-t border-mongodb-green-dark">
          <div className="px-3 py-1.5 bg-mongodb-green-dark rounded-md text-center text-sm">
            {config.environment}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="max-w-7xl mx-auto p-8">
          {children}
        </div>
      </main>
    </div>
  );
}
