import time

from app.core.security import hash_password, verify_password

password = "MySecretPassword123"

# 1. Hash the same password twice
hash_1 = hash_password(password)
hash_2 = hash_password(password)

print("Hash 1:", hash_1)
print("Hash 2:", hash_2)
print("Length of hash:", len(hash_1))
print("Same password, same hash?", hash_1 == hash_2)

# 2. Both hashes still verify the original password
print("Hash 1 verifies correct password:", verify_password(password, hash_1))
print("Hash 2 verifies correct password:", verify_password(password, hash_2))

# 3. A wrong password fails
print("Wrong password accepted?", verify_password("WrongPassword", hash_1))

# 4. Tiny differences also fail (passwords are case-sensitive)
print("Different case accepted?", verify_password("mysecretpassword123", hash_1))

# 5. A broken stored value fails safely instead of crashing
print("Invalid hash accepted?", verify_password(password, "not-a-real-hash"))

# 6. Hashing is deliberately slow
start = time.perf_counter()
hash_password(password)
elapsed_ms = (time.perf_counter() - start) * 1000
print(f"Time to hash once: {elapsed_ms:.0f} ms")