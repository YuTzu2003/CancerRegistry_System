"""Cross-cutting HTTP security: response headers and same-origin enforcement."""

from urllib.parse import urlsplit

from flask import jsonify, request

_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "frame-ancestors 'self'"
)


def _request_host(value):
    host = urlsplit(value).netloc if "//" in value else value
    return host.casefold()


def _cross_origin():
    """True when a browser-sent Origin/Referer does not match this host.

    Requests without either header (same-origin GET navigations, non-browser
    clients, tests) are allowed: browsers always attach Origin to cross-site
    unsafe-method requests, which is the attack this guards against.
    """
    origin = request.headers.get("Origin")
    if origin and origin != "null":
        return _request_host(origin) != request.host.casefold()
    referer = request.headers.get("Referer")
    if referer:
        return _request_host(referer) != request.host.casefold()
    return False


def register_security(app):
    @app.before_request
    def reject_cross_origin_writes():
        if request.method in _UNSAFE_METHODS and _cross_origin():
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "跨站請求已被拒絕。"}), 403
            return "跨站請求已被拒絕。", 403
        return None

    @app.after_request
    def set_security_headers(response):
        headers = response.headers
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        headers.setdefault("Referrer-Policy", "same-origin")
        headers.setdefault("Content-Security-Policy", _CSP)
        return response
