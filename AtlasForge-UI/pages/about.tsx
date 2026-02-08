import React from 'react';
import { H1, H2, Body } from '@leafygreen-ui/typography';
import Card from '@leafygreen-ui/card';
import Badge from '@leafygreen-ui/badge';
import { config } from '@/lib/config';

export default function AboutPage() {
  return (
    <div>
      <H1>About AtlasForge UI</H1>
      
      <Card style={{ padding: '24px', marginTop: '32px' }}>
        <H2>Overview</H2>
        <Body style={{ marginTop: '16px', lineHeight: '1.6' }}>
          AtlasForge UI is a MongoDB-themed web interface for managing your MDBaaS (MongoDB Database as a Service) control plane.
          It provides a comprehensive interface for managing tenants, MongoDB deployments, and day-2 operations.
        </Body>

        <H2 style={{ marginTop: '32px' }}>Features</H2>
        <ul style={{ marginTop: '16px', marginLeft: '24px', lineHeight: '1.8' }}>
          <li>
            <Body>Tenant management: Onboard and manage multiple tenants</Body>
          </li>
          <li>
            <Body>Deployment lifecycle: Create, scale, upgrade, and manage MongoDB deployments</Body>
          </li>
          <li>
            <Body>Real-time status monitoring with auto-refresh</Body>
          </li>
          <li>
            <Body>Connection information and connection string management</Body>
          </li>
          <li>
            <Body>Prometheus monitoring integration</Body>
          </li>
          <li>
            <Body>Backup enrollment tracking</Body>
          </li>
        </ul>

        <H2 style={{ marginTop: '32px' }}>Deployment Types</H2>
        <div style={{ marginTop: '16px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <Badge variant="green">Standalone</Badge>
          <Badge variant="green">Replica Set</Badge>
          <Badge variant="lightgray">Sharded Cluster (Coming Soon)</Badge>
        </div>

        <H2 style={{ marginTop: '32px' }}>Configuration</H2>
        <div style={{ marginTop: '16px' }}>
          <Body style={{ fontWeight: 600 }}>API Base URL:</Body>
          <Body style={{ color: '#5C6C75', marginTop: '4px' }}>{config.apiBaseUrl}</Body>
        </div>
        <div style={{ marginTop: '12px' }}>
          <Body style={{ fontWeight: 600 }}>Environment:</Body>
          <Badge variant="lightgray" style={{ marginTop: '4px' }}>{config.environment}</Badge>
        </div>

        <H2 style={{ marginTop: '32px' }}>Technology Stack</H2>
        <ul style={{ marginTop: '16px', marginLeft: '24px', lineHeight: '1.8' }}>
          <li>
            <Body>Next.js + React + TypeScript</Body>
          </li>
          <li>
            <Body>MongoDB LeafyGreen UI Components</Body>
          </li>
          <li>
            <Body>REST API Integration with FastAPI Control Plane</Body>
          </li>
        </ul>

        <Body style={{ marginTop: '32px', color: '#5C6C75', fontSize: '14px' }}>
          Version 0.1.0
        </Body>
      </Card>
    </div>
  );
}
