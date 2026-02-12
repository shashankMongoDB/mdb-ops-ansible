"""
Ops Manager Project REST API Client

Handles project lookup and creation in Ops Manager.
Uses Digest authentication with OM_PUBLIC_KEY and OM_PRIVATE_KEY.

Reference: https://www.mongodb.com/docs/ops-manager/current/reference/api/projects/
"""

import requests
from requests.auth import HTTPDigestAuth
from typing import Dict, Any, Optional, List
from app import config


class OpsManagerProjectClient:
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

    def get_project_by_name(self, org_id: str, project_name: str) -> Optional[Dict[str, Any]]:
        """
        Get project by name within an organization.
        
        Returns project dict with 'id' field (projectId) or None if not found.
        """
        try:
            path = f"/orgs/{org_id}/groups"  # groups = projects in OM API
            result = self._get(path)
            
            # OM returns "results" array of projects
            projects = result.get("results", [])
            
            # Find project by name
            for project in projects:
                if project.get("name") == project_name:
                    return project
            
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def create_project(self, org_id: str, project_name: str) -> Dict[str, Any]:
        """
        Create a new project in Ops Manager.
        
        Returns the created project dict with 'id' field (projectId).
        """
        path = f"/orgs/{org_id}/groups"
        data = {
            "name": project_name
        }
        return self._post(path, data)

    def ensure_project(self, org_id: str, project_name: str) -> Dict[str, Any]:
        """
        Ensure project exists, creating it if necessary.
        
        Returns project dict with 'id' field (projectId).
        """
        # Try to find existing project
        existing_project = self.get_project_by_name(org_id, project_name)
        
        if existing_project:
            return existing_project
        
        # Project doesn't exist, create it
        return self.create_project(org_id, project_name)


_om_project_client: Optional[OpsManagerProjectClient] = None


def get_om_project_client() -> OpsManagerProjectClient:
    """Get singleton Ops Manager project client"""
    global _om_project_client
    if _om_project_client is None:
        _om_project_client = OpsManagerProjectClient()
    return _om_project_client
