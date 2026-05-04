from urllib.parse import quote
import os

def make_url_safe_password(password: str) -> str:
    return quote(password, safe='')

# example usage
if __name__ == "__main__":
    raw_password = 'KBF_ve-JymN+QZd-kyWQ,6*WU3EZQWywV=8dM{DN)t$2&-/!Ri%qcu;6({{%rE(y?)[,L^N;8<7SH:'
    safe_password = make_url_safe_password(raw_password)

    print("Raw: ", raw_password)
    print("Safe:", safe_password)