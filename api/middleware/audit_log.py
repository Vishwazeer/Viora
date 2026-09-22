"""Viora – Immutable audit log writer."""
from __future__ import annotations

import logging

from db.models import AuditEvent, AuditEventType
from db.session import get_db_context

logger = logging.getLogger(__name__)


async def write_audit_event(
    event_type: AuditEventType,
    call_log_id=None,
    actor: str = "viora_agent",
    detail: dict | None = None,
) -> None:
    """Write an immutable audit event. Never raises — failures are logged only."""
    try:
        async with get_db_context() as db:
            event = AuditEvent(
                call_log_id=call_log_id,
                event_type=event_type,
                actor=actor,
                detail=detail or {},
            )
            db.add(event)
    except Exception as e:
        logger.error("Audit log write failed: %s | event=%s", e, event_type)
