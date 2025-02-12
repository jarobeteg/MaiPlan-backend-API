from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas import UserRegister, UserLogin, UserResponse, UserResetPassword, Token
from crud import get_user_by_email, get_user_by_username, create_user, reset_user_password
from auth_utils import create_access_token, get_current_user
from password_utils import hash_password, verify_password, is_valid_password, do_passwords_match
from datetime import timedelta
import re

router = APIRouter()

EMAIL_REGEX = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"

@router.post("/register", response_model=Token)
async def register(user: UserRegister, db: AsyncSession = Depends(get_db)):
    if not user.email.strip():
        raise HTTPException(
                status_code=400,
                detail={"code": 1, "message": "Email field cannot be empty!"}
                )

    if not re.match(EMAIL_REGEX, user.email.strip()):
        raise HTTPException(
                status_code=400,
                detail={"code": 2, "message": "Invalid email format!"}
                )

    taken_email = await get_user_by_email(db, user.email.strip())
    
    if taken_email:
        raise HTTPException(
                status_code=400,
                detail={"code": 3, "message": "Email is already taken!"}
                )

    if not user.username.strip():
        raise HTTPException(
                status_code=400,
                detail={"code": 4, "message": "Username field cannot be empty!"}
                )

    taken_username = await get_user_by_username(db, user.username.strip())

    if taken_username:
        raise HTTPException(
                status_code=400,
                detail={"code": 5, "message": "Username is already taken!"}
                )

    if not user.password.strip():
        raise HTTPException(
                status_code=400,
                detail={"code": 6, "message": "Password field cannot be empty!"}
                )

    if not is_valid_password(user.password.strip()):
        raise HTTPException(
                status_code=400,
                detail={"code": 7, "message": "Password is not strong enough!"}
                )

    if not user.password_again.strip():
        raise HTTPException(
                status_code=400,
                detail={"code": 8, "message": "Password again field cannot be empty!"}
                )

    if not do_passwords_match(user.password.strip(), user.password_again.strip()):
        raise HTTPException(
                status_code=400,
                detail={"code": 9, "message": "Passwords do not match!"}
                )

    new_user = await create_user(db, user)
    existing_email = await get_user_by_email(db, new_user.email.strip())
    
    token_data = {"sub": existing_email.user_id}
    access_token = create_access_token(data=token_data)

    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    if not user.email.strip():
        raise HTTPException(
                status_code=400,
                detail={"code": 1, "message": "Email field cannot be empty!"}
                )

    if not re.match(EMAIL_REGEX, user.email.strip()):
        raise HTTPException(
                status_code=400,
                detail={"code": 2, "message": "Invalid email format!"}
                )

    if not user.password.strip():
        raise HTTPException(
                status_code=400,
                detail={"code": 3, "message": "Password field cannot be empty!"}
                )

    existing_email = await get_user_by_email(db, user.email.strip())
    if not existing_email:
        raise HTTPException(
                status_code=401,
                detail={"code": 4, "message": "Email is not yet registered!"}
                )

    if not verify_password(user.password.strip(), existing_email.password_hash):
        raise HTTPException(
                status_code=401,
                detail={"code": 5, "message": "Incorrect password!"}
                )
    
    token_data = {"sub": existing_email.user_id}
    access_token = create_access_token(data=token_data)

    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/reset-password", response_model=Token)
async def reset_password(user: UserResetPassword, db: AsyncSession = Depends(get_db)):
    if not user.email.strip():
        raise HTTPException(
                status_code=400,
                detail={"code": 1, "message": "Email field cannot be empty!"}
                )

    if not re.match(EMAIL_REGEX, user.email.strip()):
        raise HTTPException(
                status_code=400,
                detail={"code": 2, "message": "Invalid email format!"}
                )

    existing_email = await get_user_by_email(db, user.email.strip())
    if not existing_email:
        raise HTTPException(
                status_code=401,
                detail={"code": 3, "message": "Email is not yet registered!"}
                )

    if not user.password.strip():
        raise HTTPException(
                status_code=400,
                detail={"code": 4, "message": "Password field cannot be empty!"}
                )

    if not is_valid_password(user.password.strip()):
        raise HTTPException(
                status_code=400,
                detail={"code": 5, "message": "Password is not strong enough!"}
                )

    if not user.password_again.strip():
        raise HTTPException(
                status_code=400,
                detail={"code": 6, "message": "Password again field cannot be empty!"}
                )
   
    if not do_passwords_match(user.password.strip(), user.password_again.strip()):
        raise HTTPException(
                status_code=400,
                detail={"code": 7, "message": "Passwords do not match!"}
                )
    
    await reset_user_password(db, user)

    token_data = {"sub": existing_email.user_id}
    access_token = create_access_token(data=token_data)

    return {"access_token": access_token, "token_type": "bearer"}


# an example of a protected route by jwt
@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: UserResponse = Depends(get_current_user)):
    return current_user
