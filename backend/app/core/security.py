import hashlib
import hmac
import base64
import json
import time
from typing import Optional, Dict, Any
from app.core.config import settings

def hash_password(password: str, salt: Optional[str] = None) -> str:
    if not salt:
        salt = base64.b64encode(hashlib.sha256(str(time.time()).encode()).digest()[:16]).decode()
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"{salt}${base64.b64encode(key).decode()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        parts = hashed_password.split("$")
        if len(parts) != 2:
            return False
        salt, stored_hash = parts[0], parts[1]
        recomputed = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return hmac.compare_digest(base64.b64encode(recomputed).decode(), stored_hash)
    except Exception:
        return False

def create_access_token(payload: Dict[str, Any], expires_minutes: Optional[int] = None) -> str:
    exp_mins = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    exp_time = int(time.time()) + (exp_mins * 60)
    data = dict(payload)
    data["exp"] = exp_time
    
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")
    
    signature = hmac.new(
        settings.SECRET_KEY.encode(),
        f"{header_b64}.{payload_b64}".encode(),
        hashlib.sha256
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    
    return f"{header_b64}.{payload_b64}.{sig_b64}"

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        
        expected_sig = hmac.new(
            settings.SECRET_KEY.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256
        ).digest()
        
        # Add padding back if necessary
        pad = len(sig_b64) % 4
        sig_padded = sig_b64 + ("=" * (4 - pad) if pad else "")
        decoded_sig = base64.urlsafe_b64decode(sig_padded)
        
        if not hmac.compare_digest(expected_sig, decoded_sig):
            return None
            
        pad_p = len(payload_b64) % 4
        payload_padded = payload_b64 + ("=" * (4 - pad_p) if pad_p else "")
        data = json.loads(base64.urlsafe_b64decode(payload_padded).decode())
        
        if data.get("exp", 0) < int(time.time()):
            return None # Expired
            
        return data
    except Exception:
        return None
