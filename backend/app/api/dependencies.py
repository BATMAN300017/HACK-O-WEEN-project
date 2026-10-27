from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Header
import sqlite3
from app.core.database import get_db_connection
from app.core.security import decode_access_token
from app.core.permissions import Role, Permission, has_permission

def get_db() -> Generator[sqlite3.Connection, None, None]:
    with get_db_connection() as conn:
        yield conn

def get_current_user(
    authorization: Optional[str] = Header(None),
    db: sqlite3.Connection = Depends(get_db)
) -> dict:
    # Development demo fallback if no token provided: standard investigator
    if not authorization:
        return {
            "id": "USR-INVESTIGATOR-01",
            "username": "sarah_investigator",
            "full_name": "Sarah Lin",
            "role": Role.INVESTIGATOR.value
        }
        
    try:
        scheme, token = authorization.split(" ")
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth scheme")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header format")
        
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired or invalid signature")
        
    cursor = db.cursor()
    cursor.execute("SELECT id, username, full_name, role FROM users WHERE id = ?", (payload.get("sub"),))
    user = cursor.fetchone()
    if not user:
        return {
            "id": payload.get("sub", "USR-DEMO"),
            "username": payload.get("username", "demo_user"),
            "full_name": payload.get("full_name", "Demo User"),
            "role": payload.get("role", Role.INVESTIGATOR.value)
        }
    return dict(user)

def require_permission(perm: Permission):
    def checker(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("role", Role.INVESTIGATOR.value)
        if not has_permission(user_role, perm):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action prohibited: Role '{user_role}' lacks permission '{perm.value}'"
            )
        return current_user
    return checker
