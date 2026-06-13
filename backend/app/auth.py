from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings

_bearer = HTTPBearer(auto_error=False)


def require_auth(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    """Single-user bearer-token guard.

    The frontend obtains the token from POST /auth/login (which checks the
    password) and sends it as 'Authorization: Bearer <token>'.
    """
    if creds is None or creds.credentials != settings.app_api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
