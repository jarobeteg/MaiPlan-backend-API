import os
from datetime import datetime, timedelta, timezone
from jose import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from fastapi import HTTPException, Depends, Security
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from crud import get_user_by_id
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRY = 1 # days

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
security = HTTPBearer()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRY)
    to_encode.update({"exp": expire})
    
    if 'sub' in to_encode:
        to_encode['sub'] = str(to_encode['sub'])

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Security(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credential_exception = HTTPException(status_code=401, detail={"code": 1, "message": "Could not validate credentials"})

    try: 
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        user_id: str = payload.get("sub")

        if user_id is None:
            raise credential_exception

        user = await get_user_by_id(db, int(user_id))

        if user is None:
            raise credential_exception
        
        return user
    
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail={"code": 2, "message": "Token has expired"})
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail={"code": 3, "message": "Invalid token"})
