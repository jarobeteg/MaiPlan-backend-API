from passlib.context import CryptContext
import re

# deprecated auto means that if brcypt gets a new update then passlib will rehash old passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """ Hashes a plain text password

    Args:
        password (str): The plain text password that needs to be hashed

    Returns:
        str: The hashed password
    """
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password) -> bool:
    """ Verifies if a plain password matches the hashed password

    Args:
        plain_password (str): The plain text password to check
        hashed_password (str): The hashed password to compare with

    Returns:
        bool: True of the password match, otherwise False    
    """
    return pwd_context.verify(plain_password, hashed_password)

def is_valid_password(password: str) -> bool:
    """ Validates a password strength based on criterias

    The password must: 
        - Be at least 8 characters long
        - Have at least one lowercase letter
        - Have at least on uppercase letter
        - Have at least one digit
        - Have at least one special character from !_@#$?

    Args:
        password (str): The password to validate

    Returns:
        bool: True if the password meets the strength criteria, otherwise False    
    """
    if len(password) < 8:
        return False

    if not re.search(r"[a-z]", password):
        return False

    if not re.search(r"[A-Z]", password):
        return False

    if not re.search(r"[0-9]", password):
        return False

    if not re.search(r"[!_@#$?]", password):
        return False

    return True

def do_passwords_match(password: str, password_again: str) -> bool:
    """ Compare if two passwords match
    
    Args:
        password (str): The first password to compare
        password_again (str): The second password to compare

    Returns:
        bool: True if the passwords match, otherwise False
    """
    return password == password_again
