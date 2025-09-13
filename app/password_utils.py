from passlib.context import CryptContext
import re

# deprecated auto means that if brcypt gets a new update then passlib will rehash old passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# unused code but I leave it here just in case
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def is_valid_password(password: str) -> bool:
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
    return password == password_again
