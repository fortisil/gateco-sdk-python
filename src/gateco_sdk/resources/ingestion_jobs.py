"""Ingestion jobs resource — async ingestion queue."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gateco_sdk.client import AsyncGatecoClient

TERMINAL_STATUSES = {"completed", "partial", "failed", "dead_letter", "cancelled"}


class IngestionJobsResource:
    """Namespace for async ingestion jobs. Accessed as ``client.ingest.jobs``.

    Requires the ``async_ingestion`` feature (Team plan and above) to enqueue.
    """

    def __init__(self, client: AsyncGatecoClient) -> None:
        self._client = client

    async def enqueue(
        self,
        connector_id: str,
        job_type: str,
        payload: dict[str, Any],
        *,
        max_attempts: int = 3,
    ) -> dict[str, Any]:
        """Enqueue an async ingestion job (202). job_type: document | batch."""
        body: dict[str, Any] = {
            "connector_id": connector_id,
            "job_type": job_type,
            "payload": payload,
            "max_attempts": max_attempts,
        }
        return await self._client._request("POST", "/api/v1/ingest/jobs", json=body)

    async def get(self, job_id: str) -> dict[str, Any]:
        """Get one job's status and progress."""
        return await self._client._request("GET", f"/api/v1/ingest/jobs/{job_id}")

    async def list(
        self, *, status: str | None = None, limit: int = 50, offset: int = 0,
    ) -> dict[str, Any]:
        """List the org's jobs newest-first."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        return await self._client._request(
            "GET", "/api/v1/ingest/jobs", params=params,
        )

    async def cancel(self, job_id: str) -> dict[str, Any]:
        """Cancel a queued job (running jobs are not cancellable)."""
        return await self._client._request(
            "POST", f"/api/v1/ingest/jobs/{job_id}/cancel",
        )

    async def wait_for(
        self, job_id: str, *, poll_seconds: float = 2.0, timeout: float = 600.0,
    ) -> dict[str, Any]:
        """Poll until the job reaches a terminal status (or raise TimeoutError)."""
        elapsed = 0.0
        while elapsed < timeout:
            job = await self.get(job_id)
            if job.get("status") in TERMINAL_STATUSES:
                return job
            await asyncio.sleep(poll_seconds)
            elapsed += poll_seconds
        raise TimeoutError(f"Ingestion job {job_id} did not finish within {timeout}s")
