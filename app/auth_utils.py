import os
from datetime import datetime, timedelta, timezone
from jose import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from fastapi import HTTPException, Depends, Security
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from user_crud import get_user_by_id
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRY = 7 # days

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def create_access_token(data: dict):
    """ Creates a new JWT access token

    Args:
        data (dict): Payload containing user realated data

    Returns:
        str: Encoded JWT string

    Raises:
        ValueError: If the token payload cannot be encoded

    Notes:
        - the token has expiration timestamp('exp')
        - the 'sub' field is explicitly converted to string
        - the 'sub' field is an integer (user_id)
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRY)
    to_encode.update({"exp": expire})
    
    if 'sub' in to_encode:
        to_encode['sub'] = str(to_encode['sub'])

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Security(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    """ Fetches the current user data from the database from a token

    Args:
        token (str): The JWT access token which is provided via 'Authorization' header
        db (AsyncSession): The database session dependency

    Returns:
        UserResponse: Authenticated user data

    Raises:
        HTTPException: If credentials are invalid or toke has expired or the token is invalid
    
    Notes:
        - decodes the token and extracts the user_id from the 'sub' field
        - validates if a user exists with this user_id then returns it
    """
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
