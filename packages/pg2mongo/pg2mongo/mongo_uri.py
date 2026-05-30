from __future__ import annotations

from urllib.parse import parse_qsl, quote_plus, urlencode, urlparse, urlunparse


def uri_has_credentials(uri: str) -> bool:
    """Return True when the URI already includes username (and usually password)."""
    return urlparse(uri.strip()).username is not None


def sanitize_mongo_uri(uri: str) -> str:
    """
    Remove non-standard query params (e.g. Studio 3T ``3t.*`` keys) that pymongo
    does not recognize but are common in Atlas connection strings.
    """
    parsed = urlparse(uri.strip())
    if not parsed.query:
        return uri.strip()

    kept = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if not key.lower().startswith("3t.")]
    return urlunparse(parsed._replace(query=urlencode(kept)))


def build_mongo_uri(
    uri: str,
    username: str = "",
    password: str = "",
    *,
    sanitize: bool = True,
) -> str:
    """
    Build the final MongoDB connection URI.

    Supports:
      - ``mongodb://`` (replica set / standalone)
      - ``mongodb+srv://`` (MongoDB Atlas)

    If *uri* already contains credentials, it is returned unchanged (after optional
    sanitization). Otherwise *username* / *password* are injected when provided.
    """
    uri = uri.strip()
    if not uri:
        raise ValueError("Mongo URI must not be empty")

    if uri_has_credentials(uri):
        return sanitize_mongo_uri(uri) if sanitize else uri

    if not username:
        return sanitize_mongo_uri(uri) if sanitize else uri

    user = quote_plus(username)
    pw = quote_plus(password)

    if uri.startswith("mongodb+srv://"):
        rest = uri[len("mongodb+srv://") :]
        built = f"mongodb+srv://{user}:{pw}@{rest}"
    elif uri.startswith("mongodb://"):
        rest = uri[len("mongodb://") :]
        built = f"mongodb://{user}:{pw}@{rest}"
    else:
        raise ValueError(
            "Mongo URI must start with 'mongodb://' or 'mongodb+srv://'"
        )

    return sanitize_mongo_uri(built) if sanitize else built


def redact_mongo_uri(uri: str) -> str:
    """Return a copy of *uri* with credentials replaced by ``***``."""
    parsed = urlparse(uri.strip())
    if not parsed.username:
        return uri.strip()

    host = parsed.hostname or ""
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"

    netloc = host
    if parsed.username:
        netloc = f"***:***@{host}"

    return urlunparse(
        (
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )
