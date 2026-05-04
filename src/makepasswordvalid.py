from urllib.parse import quote
import os

def make_url_safe_password(password: str) -> str:
    return quote(password, safe='')

# example usage
if __name__ == "__main__":
    raw_password = os.getenv("LOGIN_PASSWORD")
    safe_password = make_url_safe_password(raw_password)

    print("Raw: ", raw_password)
    print("Safe:", safe_password)