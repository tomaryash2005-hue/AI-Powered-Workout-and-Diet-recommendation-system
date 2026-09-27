import base64
import json
import logging
from functools import lru_cache
from typing import Any, Literal

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pywebpush import WebPushException, webpush

from app.config import settings
from app.models import PushSubscription

log = logging.getLogger(__name__)

PushResult = Literal["sent", "gone", "failed"]


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


@lru_cache
def public_key_for(private_key: str) -> str:
    value = int.from_bytes(b64url_decode(private_key.strip()), "big")
    key = ec.derive_private_key(value, ec.SECP256R1())
    return b64url_encode(key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint))


def public_key() -> str | None:
    """The browser-facing VAPID key, derived from FITAI_VAPID_PRIVATE_KEY."""
    if not settings.vapid_private_key:
        return None
    try:
        return public_key_for(settings.vapid_private_key)
    except ValueError:
        log.error("FITAI_VAPID_PRIVATE_KEY is not a valid key; generate one with `python -m app.vapid_keys`")
        return None


def push_enabled() -> bool:
    return public_key() is not None


def send_push(sub: PushSubscription, payload: dict[str, Any]) -> PushResult:
    try:
        webpush(
            subscription_info={"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}},
            data=json.dumps(payload),
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject},
            ttl=4 * 3600,
            timeout=10,
        )
        return "sent"
    except WebPushException as e:
        status = e.response.status_code if e.response is not None else None
        if status in (404, 410):
            return "gone"  # the browser unsubscribed or the subscription expired
        log.warning("Push to subscription %s failed: %s", sub.id, e)
        return "failed"
