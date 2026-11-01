import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.database import get_connection
from app.passwords import password_hasher
from app.schemas import LoginInput, PasswordChange


router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)
SESSION_SECONDS = 3600


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def require_admin(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if credentials is not None:
        with get_connection() as connection:
            session = connection.execute(
                "SELECT user_id, token_hash FROM sessions "
                "WHERE token_hash = %s AND expires_at > CURRENT_TIMESTAMP",
                (hash_token(credentials.credentials),),
            ).fetchone()
        if session is not None:
            return session
    raise HTTPException(401, "A valid administrator token is required", headers={"WWW-Authenticate": "Bearer"})


@router.post("/login")
def login(body: LoginInput):
    with get_connection() as connection:
        user = connection.execute(
            "SELECT id, password_hash FROM users WHERE username = %s", (body.username,)
        ).fetchone()
        if user is None:
            raise HTTPException(401, "Invalid username or password")
        try:
            password_hasher.verify(user["password_hash"], body.password)
        except (VerificationError, InvalidHashError):
            raise HTTPException(401, "Invalid username or password") from None

        token = secrets.token_urlsafe(32)
        connection.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (%s, %s, %s)",
            (hash_token(token), user["id"], datetime.now(timezone.utc) + timedelta(seconds=SESSION_SECONDS)),
        )
    return {"accessToken": token, "tokenType": "Bearer", "expiresIn": SESSION_SECONDS}


@router.post("/logout", status_code=204)
def logout(session=Depends(require_admin)):
    with get_connection() as connection:
        deleted = connection.execute(
            "DELETE FROM sessions WHERE token_hash = %s RETURNING token_hash",
            (session["token_hash"],),
        ).fetchone()
    if deleted is None:
        raise HTTPException(401, "Session is no longer active")
    return Response(status_code=204)


@router.put("/password", status_code=204)
def change_password(body: PasswordChange, session=Depends(require_admin)):
    with get_connection() as connection:
        user = connection.execute(
            "SELECT password_hash FROM users WHERE id = %s FOR UPDATE", (session["user_id"],)
        ).fetchone()
        if user is None:
            raise HTTPException(401, "User no longer exists")
        try:
            password_hasher.verify(user["password_hash"], body.currentPassword)
        except (VerificationError, InvalidHashError):
            raise HTTPException(403, "Current password is incorrect") from None
        connection.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (password_hasher.hash(body.newPassword), session["user_id"]),
        )
    return Response(status_code=204)
