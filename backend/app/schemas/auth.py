from pydantic import BaseModel, EmailStr
from typing import Optional

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    full_name: str
    role: str

class UserProfile(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
