import base64
import json
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token


def decode_part(part: str) -> dict:
    """Base64URL-decode one part of a JWT WITHOUT checking the signature."""
    padded = part + "=" * (-len(part) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))


def encode_part(data: dict) -> str:
    """Base64URL-encode a dict the way JWTs do (no padding)."""
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


# 1. Create a token for user 12
token = create_access_token(user_id=12, token_version=0)
header_part, payload_part, signature_part = token.split(".")
print("Token:", token)
print("\nNumber of parts:", len(token.split(".")))

# 2. Anyone can READ the header and payload
print("Header (readable by anyone):", decode_part(header_part))
payload = decode_part(payload_part)
print("Payload (readable by anyone):", payload)
print("Expires at:", datetime.fromtimestamp(payload["exp"], tz=timezone.utc))

# 3. A valid token is accepted
print("\nValid token:", decode_access_token(token))

# 4. Tampering: change the user ID from 12 to 1, keep original signature
forged_payload = {**payload, "sub": "1"}
forged_token = f"{header_part}.{encode_part(forged_payload)}.{signature_part}"
print("Tampered token (sub changed to 1):", decode_access_token(forged_token))

# 5. A token signed with a different secret key
wrong_key_token = jwt.encode(
    payload,
    "a-completely-different-secret-key-1234567890",
    algorithm="HS256",
)
print("Token signed with another key:", decode_access_token(wrong_key_token))

# 6. An expired token
past = datetime.now(timezone.utc) - timedelta(hours=2)
expired_payload = {**payload, "iat": past, "exp": past + timedelta(minutes=60)}
expired_token = jwt.encode(
    expired_payload,
    settings.jwt_secret_key,
    algorithm=settings.jwt_algorithm,
)
print("Expired token:", decode_access_token(expired_token))

# 7. The "alg: none" attack
none_header = encode_part({"alg": "none", "typ": "JWT"})
none_token = f"{none_header}.{payload_part}."
print("Unsigned 'alg: none' token:", decode_access_token(none_token))

# 8. A correctly signed token that is not an access token
other_type_token = jwt.encode(
    {**payload, "type": "refresh"},
    settings.jwt_secret_key,
    algorithm=settings.jwt_algorithm,
)
print("Token with type 'refresh':", decode_access_token(other_type_token))

# 9. Complete garbage
print("Random text:", decode_access_token("this.is.not-a-token"))