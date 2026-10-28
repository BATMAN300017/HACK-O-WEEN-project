from fastapi import APIRouter, Depends, HTTPException, status
import sqlite3
from app.api.dependencies import get_db, get_current_user
from app.schemas.auth import LoginRequest, TokenResponse
from app.core.security import verify_password, create_access_token

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, username, full_name, role, hashed_password FROM users WHERE username = ? AND is_active = 1",
        (req.username.strip().lower(),),
    )
    row = cursor.fetchone()
    if not row or not verify_password(req.password, row["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    u_data = dict(row)
        
    token = create_access_token({
        "sub": u_data["id"],
        "username": u_data["username"],
        "full_name": u_data["full_name"],
        "role": u_data["role"]
    })
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": u_data["id"],
        "username": u_data["username"],
        "full_name": u_data["full_name"],
        "role": u_data["role"]
    }

@router.post("/logout")
def logout():
    return {"message": "Logged out successfully"}

@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return current_user
