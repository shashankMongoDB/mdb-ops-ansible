import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from app import config

logger = logging.getLogger(__name__)


class MongoRepository:
    def __init__(self):
        self.client = MongoClient(config.MCP_MONGODB_URI)
        self.db = self.client[config.MCP_DB_NAME]
        self.tenants = self.db["tenants"]
        self.deployments = self.db["deployments"]
        self.db_users = self.db["db_users"]

    def get_tenant(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        return self.tenants.find_one({"_id": tenant_id})

    def list_tenants(self) -> list[Dict[str, Any]]:
        """List all tenants"""
        return list(self.tenants.find())

    def insert_tenant(self, doc: Dict[str, Any]) -> None:
        try:
            self.tenants.insert_one(doc)
        except DuplicateKeyError:
            raise ValueError(f"Tenant {doc['_id']} already exists")

    def update_tenant(self, tenant_id: str, patch: Dict[str, Any]) -> None:
        """Update tenant fields"""
        self.tenants.update_one({"_id": tenant_id}, {"$set": patch})

    def get_deployment(self, tenant_id: str, deployment_id: str) -> Optional[Dict[str, Any]]:
        doc_id = f"{tenant_id}:{deployment_id}"
        logger.debug(f"Querying deployment with _id: {doc_id}")
        result = self.deployments.find_one({"_id": doc_id})
        logger.debug(f"Query result for {doc_id}: {'Found' if result else 'Not found'}")
        return result

    def insert_deployment(self, doc: Dict[str, Any]) -> None:
        try:
            logger.info(f"Inserting deployment document with _id: {doc['_id']}")
            self.deployments.insert_one(doc)
            logger.info(f"Successfully inserted deployment: {doc['_id']}")
        except DuplicateKeyError as e:
            logger.error(f"Duplicate key error inserting deployment {doc['_id']}: {e}")
            raise ValueError(f"Deployment {doc['_id']} already exists")

    def update_deployment(self, tenant_id: str, deployment_id: str, patch: Dict[str, Any]) -> None:
        doc_id = f"{tenant_id}:{deployment_id}"
        patch["lastUpdatedAt"] = datetime.now(timezone.utc).isoformat()
        self.deployments.update_one({"_id": doc_id}, {"$set": patch})

    def list_deployments(self, tenant_id: str) -> list[Dict[str, Any]]:
        return list(self.deployments.find({"tenantId": tenant_id}))

    def delete_deployment(self, tenant_id: str, deployment_id: str) -> bool:
        """Delete a deployment. Returns True if deleted, False if not found."""
        doc_id = f"{tenant_id}:{deployment_id}"
        result = self.deployments.delete_one({"_id": doc_id})
        return result.deleted_count > 0

    def delete_tenant(self, tenant_id: str) -> bool:
        """Delete a tenant. Returns True if deleted, False if not found."""
        result = self.tenants.delete_one({"_id": tenant_id})
        return result.deleted_count > 0

    def delete_all_tenant_deployments(self, tenant_id: str) -> int:
        """Delete all deployments for a tenant. Returns count of deleted documents."""
        result = self.deployments.delete_many({"tenantId": tenant_id})
        return result.deleted_count

    # DB Users
    def insert_db_user(self, doc: Dict[str, Any]) -> None:
        """Insert a DB user metadata document"""
        try:
            self.db_users.insert_one(doc)
        except DuplicateKeyError:
            raise ValueError(f"DB user {doc['_id']} already exists")

    def get_db_user(self, tenant_id: str, deployment_id: str, username: str) -> Optional[Dict[str, Any]]:
        """Get a DB user by tenant, deployment, and username"""
        doc_id = f"{tenant_id}:{deployment_id}:{username}"
        return self.db_users.find_one({"_id": doc_id})

    def list_db_users(self, tenant_id: str, deployment_id: str) -> list[Dict[str, Any]]:
        """List all DB users for a deployment"""
        return list(self.db_users.find({
            "tenantId": tenant_id,
            "deploymentId": deployment_id
        }))

    def close(self):
        self.client.close()


_repo_instance: Optional[MongoRepository] = None


def get_repo() -> MongoRepository:
    global _repo_instance
    if _repo_instance is None:
        _repo_instance = MongoRepository()
    return _repo_instance
