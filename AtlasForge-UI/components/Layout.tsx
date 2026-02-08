import React, { ReactNode } from 'react';
import { useRouter } from 'next/router';
import SideNav, { SideNavGroup, SideNavItem } from '@leafygreen-ui/side-nav';
import { LeafyGreenProvider } from '@leafygreen-ui/leafygreen-provider';
import Badge from '@leafygreen-ui/badge';
import { config } from '@/lib/config';

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const router = useRouter();

  return (
    <LeafyGreenProvider>
      <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: '#f9fbfa' }}>
        <SideNav
          aria-label="Main Navigation"
          widthOverride={240}
        >
          <SideNavGroup
            header="AtlasForge"
            glyph={<span style={{ fontSize: '24px' }}>🍃</span>}
          >
            <SideNavItem
              active={router.pathname === '/' || router.pathname.startsWith('/tenants')}
              onClick={() => router.push('/')}
            >
              Tenants
            </SideNavItem>
            <SideNavItem
              active={router.pathname === '/about'}
              onClick={() => router.push('/about')}
            >
              About
            </SideNavItem>
          </SideNavGroup>
          
          <div style={{ 
            position: 'absolute', 
            bottom: 16, 
            left: 16,
            right: 16,
          }}>
            <Badge variant="lightgray">{config.environment}</Badge>
          </div>
        </SideNav>

        <main style={{ 
          flex: 1, 
          padding: '32px',
          maxWidth: '1400px',
          margin: '0 auto',
          width: '100%'
        }}>
          {children}
        </main>
      </div>
    </LeafyGreenProvider>
  );
}
