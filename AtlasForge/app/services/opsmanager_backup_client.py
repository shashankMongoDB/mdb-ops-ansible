"""
Ops Manager Backup REST API Client

Wraps Ops Manager REST API endpoints for backup operations.
Uses Digest authentication with OM_PUBLIC_KEY and OM_PRIVATE_KEY.

Reference: https://www.mongodb.com/docs/ops-manager/current/reference/api/
"""

import requests
from requests.auth import HTTPDigestAuth
from typing import Dict, Any, List, Optional
from app import config


class OpsManagerBackupClient:
    def __init__(self):
        self.base_url = config.MCP_OPS_MANAGER_URL.rstrip('/')
        self.public_key = config.MCP_OM_GLOBAL_PUBLIC_KEY
        self.private_key = config.MCP_OM_GLOBAL_PRIVATE_KEY
        self.auth = HTTPDigestAuth(self.public_key, self.private_key)
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make GET request to Ops Manager API"""
        url = f"{self.base_url}/api/public/v1.0{path}"
        response = requests.get(url, auth=self.auth, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def _post(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make POST request to Ops Manager API"""
        url = f"{self.base_url}/api/public/v1.0{path}"
        response = requests.post(url, auth=self.auth, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    def _patch(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make PATCH request to Ops Manager API"""
        url = f"{self.base_url}/api/public/v1.0{path}"
        response = requests.patch(url, auth=self.auth, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    def get_backup_config(self, project_id: str, cluster_name: str) -> Optional[Dict[str, Any]]:
        """
        Get backup configuration for a cluster.
        
        Returns backup config or None if not found.
        """
        try:
            path = f"/groups/{project_id}/backupConfigs/{cluster_name}"
            return self._get(path)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def list_backup_policies(self, project_id: str) -> List[Dict[str, Any]]:
        """
        List all backup policies in a project.
        
        Returns list of policies with id, name, frequencies, retention.
        """
        path = f"/groups/{project_id}/backupConfigs"
        result = self._get(path)
        # OM returns "results" array
        return result.get("results", [])

    def update_backup_config(self, project_id: str, cluster_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update backup configuration for a cluster.
        
        Used to change policy, enable/disable backup, etc.
        """
        path = f"/groups/{project_id}/backupConfigs/{cluster_name}"
        return self._patch(path, config)

    def set_backup_policy(self, project_id: str, cluster_name: str, policy_id: str) -> Dict[str, Any]:
        """
        Set backup policy for a cluster.
        
        Ops Manager requires GET full config, modify, PUT back.
        """
        path = f"/groups/{project_id}/backupConfigs/{cluster_name}"
        
        print(f"[OM_BACKUP] Getting current backup config for {cluster_name}")
        
        # GET current backup config
        current_config = self.get_backup_config(project_id, cluster_name)
        
        if not current_config:
            raise ValueError(f"No backup configuration found for cluster {cluster_name}")
        
        print(f"[OM_BACKUP] Current config: policyItemId={current_config.get('policyItemId')}, statusName={current_config.get('statusName')}")
        
        # Modify policy field (OM uses 'policyItemId' not 'policyId')
        current_config['policyItemId'] = policy_id
        
        print(f"[OM_BACKUP] Setting policyItemId to: {policy_id}")
        print(f"[OM_BACKUP] Updating backup config: PUT {self.base_url}/api/public/v1.0{path}")
        
        # PUT full config back
        response = requests.put(
            f"{self.base_url}/api/public/v1.0{path}",
            auth=self.auth,
            headers=self.headers,
            json=current_config
        )
        response.raise_for_status()
        
        print(f"[OM_BACKUP] Policy updated successfully")
        return response.json()

    def trigger_snapshot(self, project_id: str, cluster_name: str, description: str = "On-demand snapshot") -> Dict[str, Any]:
        """
        Trigger an on-demand snapshot.
        
        Ops Manager 8.x endpoint for creating on-demand snapshots.
        Reference: https://www.mongodb.com/docs/ops-manager/current/reference/api/snapshots-create-one/
        
        POST /groups/{groupId}/backup/snapshots/{clusterName}
        """
        # Correct endpoint for OM 8.x
        path = f"/groups/{project_id}/backup/snapshots/{cluster_name}"
        
        data = {
            "description": description,
            "retentionDays": 7
        }
        
        print(f"[OM_BACKUP] Triggering snapshot: POST {self.base_url}/api/public/v1.0{path}")
        print(f"[OM_BACKUP] Data: {data}")
        
        return self._post(path, data)

    def list_snapshots(self, project_id: str, cluster_name: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        List snapshots for a cluster.
        
        Returns list of snapshots with id, status, created time, etc.
        """
        path = f"/groups/{project_id}/clusters/{cluster_name}/snapshots"
        params = {"itemsPerPage": limit}
        result = self._get(path, params=params)
        return result.get("results", [])

    def get_snapshot_status(self, project_id: str, cluster_name: str, snapshot_id: str) -> Dict[str, Any]:
        """
        Get status of a specific snapshot.
        """
        path = f"/groups/{project_id}/clusters/{cluster_name}/snapshots/{snapshot_id}"
        return self._get(path)


_om_backup_client: Optional[OpsManagerBackupClient] = None


def get_om_backup_client() -> OpsManagerBackupClient:
    """Get singleton Ops Manager backup client"""
    global _om_backup_client
    if _om_backup_client is None:
        _om_backup_client = OpsManagerBackupClient()
    return _om_backup_client
