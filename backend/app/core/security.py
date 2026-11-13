import hmac

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class ApiTokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        path = request.url.path

        # Unauthenticated mobile pairing handshake & web companion assets
        if path == "/api/v1/mobile/pair" or path.startswith("/api/v1/mobile/web"):
            return await call_next(request)

        # Authenticated mobile session token bypasses desktop bearer token requirement
        session_token = (
            request.headers.get("X-Mobile-Session")
            or request.headers.get("X-Auth-Token")
            or request.query_params.get("token")
        )
        if session_token:
            dashboard = getattr(request.app.state, "dashboard_service", None)
            if dashboard is not None and dashboard.is_authenticated(session_token):
                return await call_next(request)

        expected = request.app.state.api_token
        if not expected:
            return JSONResponse(
                status_code=503,
                content={"detail": "Backend API token is not configured"},
            )

        authorization = request.headers.get("authorization", "")
        scheme, _, supplied = authorization.partition(" ")
        if scheme.lower() != "bearer" or not supplied or not hmac.compare_digest(
            supplied.encode("utf-8"), expected.encode("utf-8")
        ):
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await call_next(request)
