"""Admin auth shared by the admin endpoints: the X-Admin-Token header must equal ADMIN_TOKEN."""
import hmac
import os
from typing import Optional

from fastapi import Header, HTTPException


def require_admin_token(token: Optional[str]) -> None:
    expected = os.environ.get("ADMIN_TOKEN")
    if not expected:
        raise HTTPException(status_code=404, detail="Not Found")
    if not token or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=403, detail="Forbidden")


def require_admin(x_admin_token: Optional[str] = Header(default=None)) -> None:
    """FastAPI dependency form."""
    require_admin_token(x_admin_token)
