"""Controller layer: Flask Blueprints that turn HTTP requests into service calls."""

from urllib.parse import urlparse

from flask import request, url_for


def safe_next(default_endpoint: str = "catalogue.index") -> str:
    """Return the 'next' target only if it stays on this site (no open redirect)."""
    target = request.form.get("next") or request.args.get("next") or ""
    parsed = urlparse(target)
    if target.startswith("/") and not target.startswith("//") and not parsed.netloc:
        return target
    return url_for(default_endpoint)
