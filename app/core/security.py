from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

password_hasher = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hasher.verify(plain_password, hashed_password)

def get_password_hash(plain_password: str) -> str:
    return password_hasher.hash(plain_password)

def create_access_token(
    user_identity:Union[str, Any],
    token_validation_duration:timedelta | None=None
)->str:

    current_time=datetime.now(timezone.utc)

    if token_validation_duration:
        token_expiry_time= current_time + token_validation_duration
    else:
        token_expiry_time= current_time + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    token_payload={
        "sub"=str(user_identity),
        "exp"=token_expiry_time,
        "iat"=current_time
    }

    encoded_jwt_token= jwt.encode(
        token_payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt_token