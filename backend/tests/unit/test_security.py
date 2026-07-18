from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)

settings = get_settings()


def test_password_hash_round_trip() -> None:
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


def test_password_hash_is_salted() -> None:
    assert hash_password("same-password") != hash_password("same-password")


def test_access_token_round_trip() -> None:
    token = create_access_token(user_id=42)
    payload = decode_access_token(token)
    assert payload["sub"] == "42"


def test_access_token_expired_raises() -> None:
    now = datetime.now(UTC)
    expired_payload = {
        "sub": "1",
        "iat": now - timedelta(hours=1),
        "exp": now - timedelta(minutes=1),
    }
    expired_token = jwt.encode(expired_payload, settings.secret_key, algorithm="HS256")
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired_token)


def test_access_token_bad_signature_raises() -> None:
    token = create_access_token(user_id=1)
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token, "wrong-secret", algorithms=["HS256"])


def test_generate_refresh_token_hash_matches() -> None:
    plain, token_hash, expires_at = generate_refresh_token()
    assert hash_refresh_token(plain) == token_hash
    assert expires_at > datetime.now(UTC)


def test_refresh_tokens_are_unique() -> None:
    plain_a, _, _ = generate_refresh_token()
    plain_b, _, _ = generate_refresh_token()
    assert plain_a != plain_b
