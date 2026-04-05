"""
AgentDNA Registry — Authentication Middleware

Supports two auth modes:
1. API Key auth (for agents/services) — header: Authorization: Bearer <key>
2. Admin token (for admin operations) — header: X-Admin-Token: <token>

Environment variables:
- AGENTDNA_API_KEYS: Comma-separated list of valid API keys
- AGENTDNA_ADMIN_TOKEN: Admin token for destructive operations
- AGENTDNA_AUTH_DISABLED: Set to "1" to disable auth (dev mode)

If no keys are configured, the registry runs in open mode with a warning.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import time
from dataclasses import dataclass, field
from functools import wraps
from typing import Optional

from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


# --- Configuration ---

def _load_api_keys() -> set[str]:
    """Load API keys from environment."""
    raw = os.environ.get("AGENTDNA_API_KEYS", "")
    return {k.strip() for k in raw.split(",") if k.strip()}


def _load_admin_token() -> Optional[str]:
    """Load admin token from environment."""
    return os.environ.get("AGENTDNA_ADMIN_TOKEN") or None


def _auth_disabled() -> bool:
    """Check if auth is disabled (dev mode)."""
    return os.environ.get("AGENTDNA_AUTH_DISABLED", "").lower() in ("1", "true", "yes")


def _rate_limit_disabled() -> bool:
    """Check if rate limiting is disabled (test/dev mode)."""
    return os.environ.get("AGENTDNA_RATE_LIMIT_DISABLED", "").lower() in ("1", "true", "yes")


@dataclass
class AuthConfig:
    """Auth configuration loaded from environment."""
    api_keys: set[str] = field(default_factory=set)
    admin_token: Optional[str] = None
    disabled: bool = False
    rate_limit_disabled: bool = False

    @classmethod
    def from_env(cls) -> "AuthConfig":
        return cls(
            api_keys=_load_api_keys(),
            admin_token=_load_admin_token(),
            disabled=_auth_disabled(),
            rate_limit_disabled=_rate_limit_disabled(),
        )

    @property
    def is_configured(self) -> bool:
        """Whether any auth is configured."""
        return bool(self.api_keys) or bool(self.admin_token)

    def generate_api_key(self) -> str:
        """Generate a new API key. Returns the plaintext key."""
        key = f"adna_{secrets.token_urlsafe(32)}"
        # Store hashed version
        self.api_keys.add(key)
        return key


# --- Rate Limiter ---

@dataclass
class RateLimitBucket:
    """Token bucket for rate limiting."""
    tokens: float
    last_refill: float
    max_tokens: float
    refill_rate: float  # tokens per second


class RateLimiter:
    """
    Token bucket rate limiter.

    Default: 60 requests per minute per API key / IP.
    Verification endpoint: 10 per minute (heavier operation).
    """

    def __init__(
        self,
        default_rate: int = 60,
        default_window: int = 60,
        verify_rate: int = 10,
        verify_window: int = 60,
    ):
        self.default_limit = default_rate
        self.default_window = default_window
        self.verify_limit = verify_rate
        self.verify_window = verify_window
        self._buckets: dict[str, RateLimitBucket] = {}

    def _get_bucket(self, key: str, max_tokens: int, window: int) -> RateLimitBucket:
        """Get or create a rate limit bucket."""
        if key not in self._buckets:
            self._buckets[key] = RateLimitBucket(
                tokens=max_tokens,
                last_refill=time.time(),
                max_tokens=max_tokens,
                refill_rate=max_tokens / window,
            )
        return self._buckets[key]

    def _consume(self, bucket: RateLimitBucket) -> bool:
        """Try to consume one token. Returns True if allowed."""
        now = time.time()
        elapsed = now - bucket.last_refill
        bucket.tokens = min(bucket.max_tokens, bucket.tokens + elapsed * bucket.refill_rate)
        bucket.last_refill = now

        if bucket.tokens >= 1:
            bucket.tokens -= 1
            return True
        return False

    def check(self, identifier: str, endpoint: str = "default") -> tuple[bool, dict]:
        """
        Check if a request is allowed.

        Args:
            identifier: API key or IP address
            endpoint: Endpoint name (affects rate limit)

        Returns:
            (allowed: bool, headers: dict) where headers contain rate limit info
        """
        if endpoint == "verify":
            limit = self.verify_limit
            window = self.verify_window
        else:
            limit = self.default_limit
            window = self.default_window

        bucket_key = f"{identifier}:{endpoint}"
        bucket = self._get_bucket(bucket_key, limit, window)
        allowed = self._consume(bucket)

        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(max(0, int(bucket.tokens))),
            "X-RateLimit-Reset": str(int(bucket.last_refill + window)),
        }

        return allowed, headers


# --- Global instances ---

_auth_config = AuthConfig.from_env()
_rate_limiter = RateLimiter()


# --- Middleware ---

# Endpoints that don't require auth
_PUBLIC_PATHS = {
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
}

# Endpoints that require admin token
_ADMIN_PATHS = set()

# Read-only methods
_READ_METHODS = {"GET", "HEAD", "OPTIONS"}


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication + rate limiting middleware.

    Rules:
    - GET requests to non-admin paths: open (no auth required)
    - POST/PUT/DELETE: require API key
    - Admin paths: require admin token
    - Rate limiting applies to all requests
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # Skip auth for public paths
        if path in _PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/openapi"):
            return await call_next(request)

        # Determine client identifier (API key or IP)
        client_ip = request.client.host if request.client else "unknown"
        api_key = _extract_api_key(request)

        # Rate limiting (always applies unless disabled)
        if not _auth_config.rate_limit_disabled:
            identifier = api_key or client_ip
            endpoint_type = "verify" if "/verify" in path and method == "POST" else "default"
            allowed, rate_headers = _rate_limiter.check(identifier, endpoint_type)

            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Try again later."},
                    headers=rate_headers,
                )
        else:
            rate_headers = {
                "X-RateLimit-Limit": "disabled",
                "X-RateLimit-Remaining": "unlimited",
            }

        # Auth check
        if _auth_config.disabled:
            # Dev mode — skip auth but still apply rate limiting
            response = await call_next(request)
            for k, v in rate_headers.items():
                response.headers[k] = v
            return response

        if not _auth_config.is_configured:
            # No keys configured — open mode with warning
            response = await call_next(request)
            for k, v in rate_headers.items():
                response.headers[k] = v
            return response

        # Admin paths require admin token
        if path in _ADMIN_PATHS or path.rstrip("/") in _ADMIN_PATHS:
            admin_token = request.headers.get("X-Admin-Token", "")
            if not _auth_config.admin_token or not secrets.compare_digest(admin_token, _auth_config.admin_token):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Admin token required."},
                    headers=rate_headers,
                )
            response = await call_next(request)
            for k, v in rate_headers.items():
                response.headers[k] = v
            return response

        # Read-only requests are open (search, list, get)
        if method in _READ_METHODS:
            response = await call_next(request)
            for k, v in rate_headers.items():
                response.headers[k] = v
            return response

        # Write operations require API key
        if not api_key or api_key not in _auth_config.api_keys:
            return JSONResponse(
                status_code=401,
                content={"detail": "Valid API key required. Pass via Authorization: Bearer <key>"},
                headers=rate_headers,
            )

        response = await call_next(request)
        for k, v in rate_headers.items():
            response.headers[k] = v
        return response


def _extract_api_key(request: Request) -> Optional[str]:
    """Extract API key from Authorization header."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


# --- Convenience for route handlers ---

def require_api_key(request: Request) -> str:
    """
    Dependency for route handlers that need the API key.

    Usage:
        @app.post("/api/v1/agents")
        async def register(request: Request, card: AgentCard):
            api_key = require_api_key(request)
            ...
    """
    if _auth_config.disabled:
        return "dev-mode"

    api_key = _extract_api_key(request)
    if not api_key or api_key not in _auth_config.api_keys:
        raise HTTPException(401, "Valid API key required")
    return api_key


def get_auth_status() -> dict:
    """Get current auth configuration status (for health endpoint)."""
    return {
        "auth_configured": _auth_config.is_configured,
        "auth_disabled": _auth_config.disabled,
        "rate_limit_disabled": _auth_config.rate_limit_disabled,
        "api_keys_registered": len(_auth_config.api_keys),
    }
