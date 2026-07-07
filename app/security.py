from typing import Annotated
import secrets

from fastapi import Form, HTTPException, Request, status


CSRF_SESSION_KEY = "csrf_token"


def get_csrf_token(request: Request) -> str:
    """Return the per-session CSRF token, creating it lazily for rendered forms."""
    token = request.session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[CSRF_SESSION_KEY] = token
    return token


def require_csrf_token(request: Request, csrf_token: Annotated[str, Form()] = "") -> None:
    """FastAPI dependency that verifies a submitted form token against the session."""
    expected_token = request.session.get(CSRF_SESSION_KEY)
    if not expected_token or not secrets.compare_digest(csrf_token, expected_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")
