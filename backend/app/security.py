import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timezone

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import settings

PBKDF2_ITERATIONS = 310_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_text, digest_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.secret_key, salt="legalease-session")


def create_session_token(user_id: int) -> str:
    return _serializer().dumps(
        {"user_id": user_id, "issued_at": datetime.now(timezone.utc).isoformat()}
    )


def read_session_token(token: str) -> int | None:
    try:
        payload = _serializer().loads(token, max_age=settings.session_max_age)
        user_id = payload.get("user_id")
        return int(user_id) if user_id is not None else None
    except (BadSignature, SignatureExpired, TypeError, ValueError):
        return None


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def csrf_matches(candidate: str | None, expected: str | None) -> bool:
    return bool(candidate and expected and hmac.compare_digest(candidate, expected))
