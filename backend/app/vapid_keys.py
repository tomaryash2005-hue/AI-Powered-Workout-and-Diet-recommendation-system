"""Generate a VAPID key for push notifications: python -m app.vapid_keys"""

from cryptography.hazmat.primitives.asymmetric import ec

from app.services.push import public_key_for, b64url_encode


def generate_private_key() -> str:
    key = ec.generate_private_key(ec.SECP256R1())
    return b64url_encode(key.private_numbers().private_value.to_bytes(32, "big"))


if __name__ == "__main__":
    private = generate_private_key()
    print(f"FITAI_VAPID_PRIVATE_KEY={private}")
    print(f"# public key (derived automatically, shown for reference): {public_key_for(private)}")
