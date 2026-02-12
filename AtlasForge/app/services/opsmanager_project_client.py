"""
Ops Manager Project REST API Client

READ-ONLY: Only looks up existing projects by name.
Does NOT create or delete projects (that's done by MongoDB operators).
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
            url = f"{self.base_url}/api/public/v1.0{path}"
            print(f"[OM_PROJECT] Calling: GET {url}")
            
            result = self._get(path)
            
            # OM returns "results" array of projects
            projects = result.get("results", [])
            print(f"[OM_PROJECT] Found {len(projects)} projects in org {org_id}")
            
            # Find project by name
            for project in projects:
                print(f"[OM_PROJECT] Checking project: {project.get('name')} (id={project.get('id')})")
                if project.get("name") == project_name:
                    print(f"[OM_PROJECT] MATCH! Found project '{project_name}' with id={project.get('id')}")
                    return project
            
            print(f"[OM_PROJECT] Project '{project_name}' not found in {len(projects)} projects")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"[OM_PROJECT] HTTP Error {e.response.status_code}: {e.response.text}")
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            print(f"[OM_PROJECT] Exception: {type(e).__name__}: {str(e)}")
            raise

    # NOTE: create_project and ensure_project removed
    # Projects are created by MongoDB operators, not by this control plane


_om_project_client: Optional[OpsManagerProjectClient] = None


def get_om_project_client() -> OpsManagerProjectClient:
    """Get singleton Ops Manager project client"""
    global _om_project_client
    if _om_project_client is None:
        _om_project_client = OpsManagerProjectClient()
    return _om_project_client
