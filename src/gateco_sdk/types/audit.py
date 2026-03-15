"""Types for audit log endpoints."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class AuditEventType(str, Enum):
    """Audit event types for the audit trail."""

    user_login = "user_login"
    user_logout = "user_logout"
    settings_changed = "settings_changed"
    connector_added = "connector_added"
    connector_updated = "connector_updated"
    connector_tested = "connector_tested"
    connector_removed = "connector_removed"
    connector_sync_started = "connector_sync_started"
    connector_synced = "connector_synced"
    connector_sync_failed = "connector_sync_failed"
    idp_added = "idp_added"
    idp_updated = "idp_updated"
    idp_removed = "idp_removed"
    idp_sync_started = "idp_sync_started"
    idp_synced = "idp_synced"
    idp_sync_failed = "idp_sync_failed"
    policy_created = "policy_created"
    policy_updated = "policy_updated"
    policy_activated = "policy_activated"
    policy_archived = "policy_archived"
    policy_deleted = "policy_deleted"
    resource_updated = "resource_updated"
    pipeline_created = "pipeline_created"
    pipeline_updated = "pipeline_updated"
    pipeline_run = "pipeline_run"
    pipeline_error = "pipeline_error"
    retrieval_allowed = "retrieval_allowed"
    retrieval_denied = "retrieval_denied"
    metadata_bound = "metadata_bound"
    document_ingested = "document_ingested"
    batch_ingested = "batch_ingested"
    ingestion_failed = "ingestion_failed"
    retroactive_registered = "retroactive_registered"


class AuditEvent(BaseModel):
    """An audit log event."""

    id: str
    event_type: str
    actor_id: str | None = None
    actor_name: str | None = None
    principal_id: str | None = None
    details: str | None = None
    ip_address: str | None = None
    timestamp: str | None = None
    resource_ids: list[str] = []


class AuditExportRequest(BaseModel):
    """Parameters for audit log export."""

    event_types: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    format: str = "json"
