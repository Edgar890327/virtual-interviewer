"""Authentication and authorization utilities."""

import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Optional
from app.database import UserDB
from app.config import JWT_SECRET_KEY

ALGORITHM = "HS256"
TOKEN_EXPIRATION_DAYS = 30


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(user_id: str) -> str:
    """Create JWT access token."""
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(days=TOKEN_EXPIRATION_DAYS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[str]:
    """Decode JWT token and return user_id."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.InvalidTokenError:
        return None


def register_user(username: str, email: str, password: str) -> Optional[str]:
    """Register a new user. Returns user_id if successful."""
    # Check if user already exists
    if UserDB.get_user_by_username(username) or UserDB.get_user_by_email(email):
        return None
    
    # Create user with hashed password
    password_hash = hash_password(password)
    return UserDB.create_user(username, email, password_hash)


def authenticate_user(username: str, password: str) -> Optional[tuple]:
    """Authenticate user and return (user_id, access_token)."""
    user = UserDB.get_user_by_username(username)
    if not user or not verify_password(password, user["password_hash"]):
        return None
    
    token = create_access_token(user["id"])
    return (user["id"], token)
