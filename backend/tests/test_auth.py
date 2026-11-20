import pytest
import uuid
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    decrypt_secret,
    encrypt_secret,
    hash_password,
    verify_password,
)


def test_password_hashing():
    raw = "MySecretPassword123!"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_generation_and_decode():
    user_id = str(uuid.uuid4())
    token = create_access_token(subject=user_id, extra_claims={"role": "ADMIN"})
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["role"] == "ADMIN"
    assert payload["type"] == "access"


def test_refresh_token():
    user_id = str(uuid.uuid4())
    token = create_refresh_token(subject=user_id)
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["type"] == "refresh"
    assert "jti" in payload


def test_fernet_credential_encryption():
    secret_pass = "SuperSecretPostgresPassword#2026"
    encrypted = encrypt_secret(secret_pass)
    assert encrypted != secret_pass
    decrypted = decrypt_secret(encrypted)
    assert decrypted == secret_pass

