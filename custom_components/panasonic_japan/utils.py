"""Shared helpers for the Panasonic Japan integration."""
from __future__ import annotations

from .const import (
    API_BASE_URL,
    AUTH0_DOMAIN,
    AUTH0_TOKEN_URL,
    EOJ_FRIDGE,
    KAPF_API_BASE_URL,
)


def normalize_eoj(eoj: str | None) -> str:
    """Return a normalized EOJ code (uppercase), or empty string."""
    return (eoj or "").upper()


def is_fridge_eoj(eoj: str | None) -> bool:
    """Return True if the EOJ corresponds to a supported refrigerator."""
    return normalize_eoj(eoj) == EOJ_FRIDGE


def encode_appliance_id(appliance_id: str) -> str:
    """Convert appliance_id to base64url path segment (matches Android z() method)."""
    return appliance_id.replace("+", "-").replace("/", "_")


def auth0_userinfo_url() -> str:
    """Return the Auth0 userinfo endpoint URL."""
    return f"https://{AUTH0_DOMAIN}/userinfo"


def user_info_url() -> str:
    """Return the KAPF user info endpoint URL."""
    return f"{KAPF_API_BASE_URL}/user/info"


def device_url(appliance_id: str, *path_parts: str) -> str:
    """Build a REIZO API URL under /devices/{id}/."""
    encoded = encode_appliance_id(appliance_id)
    suffix = "/".join(path_parts)
    return f"{API_BASE_URL}/devices/{encoded}/{suffix}"


def product_url(appliance_id: str, *path_parts: str) -> str:
    """Build a REIZO API URL under /products/{id}/."""
    encoded = encode_appliance_id(appliance_id)
    suffix = "/".join(path_parts)
    return f"{API_BASE_URL}/products/{encoded}/{suffix}"


def push_new_term_url() -> str:
    """Return the KAPF push registration endpoint URL."""
    return f"{KAPF_API_BASE_URL}/push/new-term"


def auth0_token_url() -> str:
    """Return the Auth0 token endpoint URL."""
    return AUTH0_TOKEN_URL
