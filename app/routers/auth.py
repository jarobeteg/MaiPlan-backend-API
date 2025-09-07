from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas import UserRegister, UserLogin, UserResponse, UserResetPassword, Token
from user_crud import get_user_by_email, get_user_by_username, create_user, reset_user_password
from auth_utils import create_access_token, get_current_user
from password_utils import verify_password, is_valid_password, do_passwords_match
import re

router = APIRouter()

EMAIL_REGEX = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"

def validate_email(email: str):
    """ Validates the email field and the email format

    Args:
        email (str): The email address that needs to be validated
    
    Returns:
        str: Validated email string

    Raises:
        HTTPException: If email field is empty or the email format is invalid    
    """
    email = email.strip()
    if not email:
        raise HTTPException(status_code=400, detail={"code": 1, "message": "Email field cannot be empty!"})
    if not re.match(EMAIL_REGEX, email):
        raise HTTPException(status_code=400, detail={"code": 2, "message": "Invalid email format!"})
    return email

async def validate_email_existence(db: AsyncSession, email: str):
    """ Validates the email existence in the database

    Args:
        db (AsyncSession): The database session dependency
        email (str): The email address that need to be checked if it's registered in the database or not
    
    Returns:
        UserResponse: Basic user data

    Raises:
        HTTPException: If email is not yet registered in the database
    """
    existing_user = await get_user_by_email(db, email)
    if not existing_user:
        raise HTTPException(status_code=401, detail={"code": 3, "message": "Email is not yet registered!"})
    return existing_user

def validate_password(password: str):
    """ Validates password field

    Args:
        password (str): The password that needs to be validated

    Returns:
        str: Validated password string

    Raises:
        HTTPException: If password is empty
    """
    password = password.strip()
    if not password:
        raise HTTPException(status_code=400, detail={"code": 4, "message": "Password field cannot be empty!"})
    return password

def validate_password_strength(password: str):
    """ Validates the password strength

    Args:
        password (str): The password that's strength needs to be validated

    Raises:
        HTTPException: If the password is not strong enough
    """
    if not is_valid_password(password):
        raise HTTPException(status_code=400, detail={"code": 5, "message": "Password is not strong enough!"})

def validate_passwords(password: str, password_again: str):
    """ Validates if the passwords match

    Args:
        password (str): The password that needs to be same as the password_again
        password_again (str): The password_again needs to be the same as password and not be empty

    Raises: 
        HTTPException: If the password_again field is empty or the passwords do not match
    """
    if not password_again:
        raise HTTPException(status_code=400, detail={"code": 6, "message": "Password again field cannot be empty!"})
    if not do_passwords_match(password, password_again):
        raise HTTPException(status_code=400, detail={"code": 7, "message": "Passwords do not match!"})

def get_access_token(user_id: str):
    """ Generates an access token for the user

    Args:
        user_id (int): An id number that identifies the correct user
    
    Returns:
        str: A JWT access token encoded as string for user authentication 
    """
    token_data = {"sub": user_id}
    return create_access_token(data=token_data)

@router.post("/register", response_model=UserResponse)
async def register(user: UserRegister, db: AsyncSession = Depends(get_db)):
    user.email = validate_email(user.email)
    user.username = user.username.strip()

    if await get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail={"code": 8, "message": "Email is already taken!"})
    if not user.username:
        raise HTTPException(status_code=400, detail={"code": 9, "message": "Username field cannot be empty!"})
    if await get_user_by_username(db, user.username):
        raise HTTPException(status_code=400, detail={"code": 10, "message": "Username is already taken!"})

    new_user = await create_user(db, user)

    return UserResponse(
        user_id=new_user.user_id,
        email=new_user.email,
        username=new_user.username
    )

@router.post("/login", response_model=Token)
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    """ This API Logins an existing user

    Args:
        user (UserLogin): Holds all the data that needs to be checked in the database to authorize the user
        db (AsyncSession): The database session dependency

    Returns:
        Token: When the given credentials from the UserLogin matches a User in the database a Token is generated and passed forward to the frontend
    
    Raises:
        HTTPException: If there are any validation error from the UserLogin data
    """
    user.email = validate_email(user.email)
    existing_user = await validate_email_existence(db, user.email)

    user.password = validate_password(user.password)
    if not verify_password(user.password, existing_user.password_hash):
        raise HTTPException(status_code=401, detail={"code": 8, "message": "Incorrect password!"})

    return Token(access_token=get_access_token(existing_user.user_id), token_type="bearer")

@router.post("/reset-password", response_model=Token)
async def reset_password(user: UserResetPassword, db: AsyncSession = Depends(get_db)):
    """ This API Resets the user password

    Args:
        user (UserResetPassword): Holds all the data that are needed to reset the user password in the database
        db (AsyncSession): The database session dependency

    Returns:
        Token: When the password is changed in the database a Token is generated and passed forward to the frontend

    Raises:
        HTTPException: If there are any validation error from the UserResetPassword data
    """
    user.email = validate_email(user.email)
    existing_user = await validate_email_existence(db, user.email)

    user.password = validate_password(user.password)
    validate_password_strength(user.password)
    validate_passwords(user.password, user.password_again.strip())
    await reset_user_password(db, user)

    return Token(access_token=get_access_token(existing_user.user_id), token_type="bearer")

@router.post("/token-refresh", response_model=Token)
async def token_refresh(current_user: UserResponse = Depends(get_current_user)):
    """ This API Refreshes the old token for a new token since tokens expire after 7 days,
    so the refresh only happens to users that have a token that is not expired yet

    Args:
        current_user (UserResponse): The authenticated user obtained from the dependency get_current_user which needs a token

    Returns:
        Token: A new Token is generated and passed forward to the frontend
    """
    return Token(access_token=get_access_token(current_user.user_id), token_type="bearer")

# an example of a protected route by jwt
@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: UserResponse = Depends(get_current_user)):
    """ This API returns user data from token

    Args:
        current_user (UserResponse): The authenticated user obtained from the dependency get_current_user which needs a token

    Returns:
        UserResponse: Basic user data
    """
    return current_user
