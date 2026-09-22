"""Viora – DPDP Consent middleware."""
from __future__ import annotations

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ConsentMiddleware(BaseHTTPMiddleware):
    """
    Injects consent-tracking headers into relevant responses.
    Actual consent capture happens in-call via the agent worker.
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Data-Controller"] = "Viora Healthcare AI"
        response.headers["X-Data-Purpose"] = "Patient call assistance"
        response.headers["X-Retention-Policy"] = "Audio:7d Transcript:365d"
        return response
