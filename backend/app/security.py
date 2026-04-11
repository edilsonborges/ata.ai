from datetime import datetime, timedelta, timezone
from typing import Literal
from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import get_settings

settings = get_settings()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_fernet = Fernet(settings.fernet_key.encode())

TokenType = Literal["access", "refresh"]


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def create_token(subject: str, token_type: TokenType) -> str:
    ttl = (
        settings.jwt_access_ttl_seconds
        if token_type == "access"
        else settings.jwt_refresh_ttl_seconds
    )
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str, expected_type: TokenType) -> str:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise ValueError("invalid token") from exc
    if payload.get("type") != expected_type:
        raise ValueError(f"wrong token type, expected {expected_type}")
    return payload["sub"]


def encrypt_secret(plaintext: str) -> bytes:
    return _fernet.encrypt(plaintext.encode())


def decrypt_secret(ciphertext: bytes) -> str:
    return _fernet.decrypt(ciphertext).decode()
