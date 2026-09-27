import json
import logging
import urllib.error
import urllib.request

from app.config import settings

log = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"


def email_enabled() -> bool:
    return bool(settings.resend_api_key) or settings.environment == "development"


def send_email(to: str, subject: str, text: str) -> bool:
    """Send via Resend when configured; in development, print the email to the server log."""
    if not settings.resend_api_key:
        if settings.environment == "development":
            log.warning("Email (dev mode, not sent) to %s — %s\n%s", to, subject, text)
            return True
        log.error("Email not sent: FITAI_RESEND_API_KEY is not configured")
        return False

    body = json.dumps({"from": settings.email_from, "to": [to], "subject": subject, "text": text}).encode()
    request = urllib.request.Request(
        RESEND_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "FitAI",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10):
            return True
    except (urllib.error.URLError, TimeoutError) as e:
        log.error("Sending email to %s failed: %s", to, e)
        return False
