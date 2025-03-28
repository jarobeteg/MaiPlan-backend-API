from sqlalchemy.future import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
from schemas import UserRegister, UserResetPassword
from password_utils import hash_password

async def get_user_by_id(db: AsyncSession, user_id: int):
    """ Fetch a user by given id
    
    Args:
        db (AsyncSession): The database session
        user_id (int): The id of the user to fetch

    Returns:
        UserResponse: The user data connected to the given id
    """
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalars().first()

async def get_user_by_email(db: AsyncSession, email: str):
    """ Fetch a user by given email

    Args:
        db (AsyncSession): The database session
        email (str): The email address of the user

    Returns:
        UserResponse: The user data connected to the given email
    """
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()

async def get_user_by_username(db: AsyncSession, username: str):
    """ Fetch a user by given username

    Args:
        db (AsyncSession): The database session
        username (str): The username of the user

    Returns:
        UserResponse: The user data connected to the given username
    """
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()

async def reset_user_password(db: AsyncSession, user: UserResetPassword):
    """ Reset the given user's password
    
    Args:
        db (AsyncSession): The database session
        user (UserResetPassword): Holds all the user data that are needed to correctly reset the password
    """
    hashed_password = hash_password(user.password)
    
    stmt = (
            update(User)
            .where(User.email == user.email)
            .values(password_hash=hashed_password)
            .execution_options(synchronize_session="fetch")
    )

    await db.execute(stmt)
    await db.commit()

async def create_user(db: AsyncSession, user: UserRegister):
    """ Creates a new user
    
    Args:
        db (AsyncSession): The database session
        user (UserRegister): Holds all the user data that needs to be added to the database

    Returns:
        UserResponse: Newly created user
    """
    hashed_password = hash_password(user.password)
    new_user = User(email=user.email, username=user.username, password_hash=hashed_password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
