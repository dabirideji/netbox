"""Default HTTP security headers."""

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'self'; connect-src 'self' https://locate.measurementlab.net wss:; "
        "script-src 'self'; worker-src 'self'; style-src 'self'; "
        "img-src 'self' data: https://images.pexels.com; base-uri 'none'; frame-ancestors 'none'"
    ),
}
