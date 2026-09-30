import statistics
import sys
import time

from fastapi.testclient import TestClient

from app.main import app

if len(sys.argv) != 2:
    print("Usage: python -m scripts.time_login <registered-email>")
    sys.exit(1)

registered_email = sys.argv[1]
client = TestClient(app)
ROUNDS = 10


def average_ms(email: str) -> float:
    """Average response time (ms) of failed logins for this email."""
    timings = []
    for _ in range(ROUNDS):
        start = time.perf_counter()
        response = client.post(
            "/api/auth/login",
            json={"email": email, "password": "DefinitelyWrong123"},
        )
        timings.append((time.perf_counter() - start) * 1000)
        assert response.status_code == 401, response.text
    return statistics.mean(timings)


client.post("/api/auth/login", json={"email": registered_email, "password": "warmup"})  # warm-up

registered = average_ms(registered_email)
unknown = average_ms("nobody-here-at-all@example.com")

print(f"Registered email, wrong password: {registered:6.1f} ms")
print(f"Unknown email:                    {unknown:6.1f} ms")
print(f"Difference:                       {abs(registered - unknown):6.1f} ms")
