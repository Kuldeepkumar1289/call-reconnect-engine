from datetime import datetime, timedelta, timezone
from typing import Any, Union
import bcrypt
from jose import jwt
from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:

    plain_password_bytes = plain_password.encode("utf-8")[:72]
    hashed_password_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(plain_password_bytes, hashed_password_bytes)


def get_password_hash(plain_password: str) -> str:
    # 72 bytes safe truncation
    plain_password_bytes = plain_password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password_bytes, salt).decode("utf-8")


def create_access_token(
    user_identity: Union[str, Any],
    token_validation_duration: timedelta | None = None,
) -> str:
    current_time = datetime.now(timezone.utc)

    if token_validation_duration:
        token_expiry_time = current_time + token_validation_duration
    else:
        token_expiry_time = current_time + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    token_payload = {
        "sub": str(user_identity),
        "exp": token_expiry_time,
        "iat": current_time,
    }

    encoded_jwt_token = jwt.encode(
        token_payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt_token