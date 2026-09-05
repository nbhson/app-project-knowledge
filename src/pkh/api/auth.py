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


def get_current_role(x_role: str | None = Header(default=None)) -> str:
    settings = get_settings()
    if not settings.governance.rbac_enabled:
        return "ADMIN"
    if not x_role:
        return "VIEWER"
    return x_role.upper()


def require_permission(permission: str):
    def dep(role: str = Depends(get_current_role)):
        perms = ROLES.get(role, set())
        if permission not in perms:
            raise HTTPException(
                status_code=403, detail=f"Role {role} lacks permission {permission}"
            )
        return role

    return dep
