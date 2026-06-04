"""Venture context middleware — extracts venture_id and sets RLS context."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from ai_flywheel.core.traces import _current_venture_id


class VentureContextMiddleware(BaseHTTPMiddleware):
    """Extract venture_id from request and set trace context.

    Venture ID can come from:
    1. X-Venture-ID header
    2. Path parameter (for /api/ventures/{id}/... routes)
    3. JWT claim (when auth is implemented)
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Extract venture_id from header
        venture_id = request.headers.get("X-Venture-ID")

        if venture_id:
            _current_venture_id.set(venture_id)

        response = await call_next(request)

        # Clear context after request
        _current_venture_id.set(None)

        return response
