import bcrypt
import re

# unused code but I leave it here just in case
def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password, hashed_password) -> bool:
    plain_password_bytes = plain_password.encode('utf-8')
    hashed_password_bytes = hashed_password.encode('utf-8')
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
