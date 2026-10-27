from fastapi import APIRouter, Depends, HTTPException, status
import sqlite3
from app.api.dependencies import get_db, get_current_user
from app.schemas.auth import LoginRequest, TokenResponse, UserProfile
from app.core.security import verify_password, create_access_token
from app.core.permissions import Role

router = APIRouter()

DEMO_USERS = {
    "sarah_investigator": {
        "id": "USR-INV-01",
        "username": "sarah_investigator",
        "full_name": "Sarah Lin (Investigator)",
        "role": Role.INVESTIGATOR.value,
        "email": "sarah.lin@sentinelflow.bank"
    },
    "marcus_senior": {
        "id": "USR-SR-02",
        "username": "marcus_senior",
        "full_name": "Marcus Vance (Senior Investigator)",
        "role": Role.SENIOR_INVESTIGATOR.value,
        "email": "marcus.vance@sentinelflow.bank"
    },
    "elena_admin": {
        "id": "USR-ADM-03",
        "username": "elena_admin",
        "full_name": "Elena Rostova (Fraud Ops Admin)",
        "role": Role.FRAUD_ADMIN.value,
        "email": "elena.rostova@sentinelflow.bank"
    },
    "arthur_auditor": {
        "id": "USR-AUD-04",
        "username": "arthur_auditor",
        "full_name": "Arthur Pendelton (Internal Auditor)",
        "role": Role.AUDITOR.value,
        "email": "arthur.pendelton@sentinelflow.bank"
    }
}

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: sqlite3.Connection = Depends(get_db)):
    u_data = DEMO_USERS.get(req.username.lower())
    if not u_data or req.password != "password123":
        # Check DB users
        cursor = db.cursor()
        cursor.execute("SELECT id, username, full_name, role, hashed_password FROM users WHERE username = ?", (req.username,))
        row = cursor.fetchone()
        if not row or not verify_password(req.password, row["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password. (Hint for local demo: use 'sarah_investigator' and 'password123')"
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
