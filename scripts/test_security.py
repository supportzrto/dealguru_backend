
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

password = "TestPassword123!"

hashed = hash_password(password)

print("Password hashing:", bool(hashed))
print("Password verification:", verify_password(password, hashed))
print("Wrong password rejected:", not verify_password("WrongPassword", hashed))

token = create_access_token("test-user-123")
decoded = decode_access_token(token)

print("JWT generation:", bool(token))
print("JWT subject:", decoded["sub"])
