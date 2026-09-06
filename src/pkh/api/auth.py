"""RBAC auth."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException

from pkh.config.settings import get_settings

ROLES = {
    "ADMIN": {"ingest", "query", "context", "graph", "audit", "health"},
    "ARCHITECT": {"query", "context", "graph", "audit", "health"},
    "DEVELOPER": {"query", "context", "graph", "ingest", "health"},
    "VIEWER": {"query", "context", "health"},
    "SERVICE": {"query", "context", "health"},
}


def get_current_role(
    authorization: str | None = Header(default=None),
    x_role: str | None = Header(default=None),
) -> str:
    settings = get_settings()
    if not settings.governance.rbac_enabled:
        return "ADMIN"
    # RBAC enabled: require JWT Bearer token, do not trust X-Role
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
        if not token:
            raise HTTPException(status_code=401, detail="Invalid token")
        secret = getattr(settings.governance, "jwt_secret", None)
        algorithm = getattr(settings.governance, "jwt_algorithm", "HS256")
        # If no secret configured, decode without verification for test/dev (extract role claim)
        try:
            # import lazily to avoid hard dependency at import time
            from jose import jwt
        except ImportError as e:
            raise HTTPException(status_code=500, detail=f"JWT support missing: {e}") from e
        try:
            if secret:
                payload = jwt.decode(token, secret, algorithms=[algorithm])
            else:
                # insecure fallback for tests: get unverified claims
                payload = jwt.get_unverified_claims(token)
        except Exception as e:  # JWTError
            raise HTTPException(status_code=401, detail=f"Invalid token: {e}") from e
        role = (
            payload.get("role") or payload.get("roles") or payload.get("preferred_role") or "VIEWER"
        )
        if isinstance(role, list):
            role = role[0] if role else "VIEWER"
        return str(role).upper()
    # No valid JWT -> unauthorized (do not fallback to X-Role when RBAC enabled)
    raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")


def require_permission(permission: str):
    def dep(role: str = Depends(get_current_role)):
        perms = ROLES.get(role, set())
        if permission not in perms:
            raise HTTPException(
                status_code=403, detail=f"Role {role} lacks permission {permission}"
            )
        return role

    return dep
