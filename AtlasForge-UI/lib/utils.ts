import { DeploymentStatus } from './types';

export function getStatusColor(phase: DeploymentStatus['phase']): 'green' | 'blue' | 'gray' | 'red' | 'yellow' {
  switch (phase) {
    case 'Running':
      return 'green';
    case 'Provisioning':
    case 'Scaling':
      return 'blue';
    case 'Stopped':
      return 'gray';
    case 'Error':
      return 'red';
    case 'Deleted':
      return 'gray';
    default:
      return 'yellow';
  }
}

export function formatTimestamp(timestamp?: string): string {
  if (!timestamp) return 'N/A';
  const date = new Date(timestamp);
  return date.toLocaleString();
}

export function validateMembers(members: number): { valid: boolean; warning?: string; error?: string } {
  if (members < 3) {
    return { valid: false, error: 'Replica set must have at least 3 members' };
  }
  if (members % 2 === 0) {
    return { valid: true, warning: 'Even number of members can cause voting issues in split-brain scenarios' };
  }
  return { valid: true };
}

export function compareVersions(v1: string, v2: string): number {
  const parts1 = v1.replace('-ent', '').split('.').map(Number);
  const parts2 = v2.replace('-ent', '').split('.').map(Number);
  
  for (let i = 0; i < Math.max(parts1.length, parts2.length); i++) {
    const part1 = parts1[i] || 0;
    const part2 = parts2[i] || 0;
    
    if (part1 > part2) return 1;
    if (part1 < part2) return -1;
  }
  
  return 0;
}

export function isDowngrade(currentVersion: string, newVersion: string): boolean {
  return compareVersions(newVersion, currentVersion) < 0;
}

export function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    return navigator.clipboard.writeText(text);
  }
  
  const textArea = document.createElement('textarea');
  textArea.value = text;
  textArea.style.position = 'fixed';
  textArea.style.left = '-999999px';
  document.body.appendChild(textArea);
  textArea.select();
  
  try {
    document.execCommand('copy');
    return Promise.resolve();
  } catch (err) {
    return Promise.reject(err);
  } finally {
    document.body.removeChild(textArea);
  }
}
