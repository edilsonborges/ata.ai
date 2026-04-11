import pytest
from app.security import (
    create_token, decode_token, encrypt_secret, decrypt_secret,
    hash_password, verify_password,
)


def test_password_roundtrip():
    h = hash_password("ksjao10so!")
    assert verify_password("ksjao10so!", h)
    assert not verify_password("wrong", h)


def test_token_roundtrip_access():
    tok = create_token("user-123", "access")
    assert decode_token(tok, "access") == "user-123"


def test_token_type_mismatch_raises():
    tok = create_token("user-123", "access")
    with pytest.raises(ValueError):
        decode_token(tok, "refresh")


def test_fernet_roundtrip():
    ct = encrypt_secret("sk-ant-xyz")
    assert decrypt_secret(ct) == "sk-ant-xyz"
