"""Authentification locale légère (Bearer token).

Rôles :
- ``user``  : peut interroger le chat (``POST /api/v1/ask``).
- ``admin`` : peut aussi ingérer des documents (``POST /api/v1/documents``).

Les tokens sont configurés via ``settings.auth_admin_token`` et
``settings.auth_user_tokens`` (variables d'environnement / .env), jamais dans
le code. Quand ``settings.auth_enabled`` est faux, tous les rôles sont accordés
(mode de développement local).
"""
from typing import Optional

from fastapi import Header, HTTPException

from app.core.config import settings


def _parse_bearer(authorization: Optional[str]) -> Optional[str]:
    """Extrait le token d'un en-tête ``Authorization: Bearer <token>``."""
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        token = parts[1].strip()
        return token or None
    return None


def _user_tokens() -> list:
    return [t.strip() for t in settings.auth_user_tokens.split(",") if t.strip()]


def _role_for(token: Optional[str]) -> Optional[str]:
    """Retourne ``admin``, ``user`` ou ``None`` selon le token."""
    if not token:
        return None
    if token == settings.auth_admin_token:
        return "admin"
    if token in _user_tokens():
        return "user"
    return None


def verify(authorization: Optional[str] = None) -> dict:
    """Valide un token Bearer. Retourne ``{"authenticated": True, "role": ...}``.

    Lève 401 si l'authentification est requise et le token invalide/absent.
    """
    if not settings.auth_enabled:
        return {"authenticated": True, "role": "admin"}
    role = _role_for(_parse_bearer(authorization))
    if role is None:
        raise HTTPException(
            status_code=401,
            detail="Authentification requise (token invalide ou absent).",
        )
    return {"authenticated": True, "role": role}


def require_user(authorization: Optional[str] = Header(default=None)) -> str:
    """Dépendance FastAPI : autorise tout token valide (user ou admin)."""
    return verify(authorization)["role"]


def require_admin(authorization: Optional[str] = Header(default=None)) -> str:
    """Dépendance FastAPI : autorise uniquement le token admin."""
    role = verify(authorization)["role"]
    if role != "admin":
        raise HTTPException(status_code=403, detail="Accès admin requis.")
    return role
