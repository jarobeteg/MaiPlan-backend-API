import re

from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

# unused code but I leave it here just in case
def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(plain_password, hashed_password) -> bool:
    return password_hash.verify(plain_password, hashed_password)

def is_valid_password(password: str) -> bool:
    if len(password) < 8:
        return False

    if not re.search(r"[a-z]", password):
        return False

    if not re.search(r"[A-Z]", password):
        return False

    if not re.search(r"[0-9]", password):
        return False

    return re.search(r"[!_@#$?]", password) is not None

def do_passwords_match(password: str, password_again: str) -> bool:
    return password == password_again
