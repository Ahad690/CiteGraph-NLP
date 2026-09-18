"""API authentication.

The service exposes a background-job API that performs outbound HTTP requests
on behalf of the caller, so it should not be anonymous once it is reachable
from the internet. Authentication is driven by the ``API_KEY`` setting:

* ``API_KEY`` set   -> every ``/api`` route requires a matching ``X-API-Key``
  header (``?api_key=`` is also accepted so browser clients that cannot set
  headers on a download link still work).
* ``API_KEY`` unset -> routes stay open, which keeps the local demo and the
  Docker Compose quickstart working with no configuration.

Leaving it unset in a deployed environment is logged as a warning at startup.
"""

import hmac
import logging

from fastapi import Header, HTTPException, Query, status

from citegraph.config import settings

logger = logging.getLogger(__name__)


def auth_enabled() -> bool:
    return bool(settings.api_key)


def warn_if_unauthenticated() -> None:
    """Log a startup warning when a non-development deployment has no API key."""
    if auth_enabled():
        return
    if settings.app_env.lower() in {"development", "dev", "local", "test"}:
        logger.info("API_KEY is not set; API is open (app_env=%s)", settings.app_env)
    else:
        logger.warning(
            "API_KEY is not set but app_env=%s: every endpoint is reachable "
            "anonymously. Set API_KEY before exposing this service publicly.",
            settings.app_env,
        )


async def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    api_key: str | None = Query(default=None, include_in_schema=False),
) -> None:
    """Reject requests without a valid API key, when one is configured."""
    expected = settings.api_key
    if not expected:
        return

    supplied = x_api_key or api_key
    # compare_digest keeps the check constant-time; it needs str, not None.
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "X-API-Key"},
        )
