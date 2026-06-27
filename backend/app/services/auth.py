"""
登录服务 — 通过学号+密码获取 resToken + SESSION + authcode
"""
import requests
from datetime import datetime, timezone, timedelta
from cryptography.fernet import Fernet
import os

LOGIN_URL = "https://jw.ruc.edu.cn/secService/login"

LOGIN_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "KAPTCHA-KEY-GENERATOR-REDIS": "securityKaptchaRedisServiceAdapter",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

TZ = timezone(timedelta(hours=8))

# 简单密码加密（生产环境应使用环境变量注入的密钥）
_cipher_key = os.getenv("CIPHER_KEY", Fernet.generate_key().decode()).encode()
try:
    _cipher = Fernet(_cipher_key)
except Exception:
    _cipher = Fernet(Fernet.generate_key())


def encrypt_password(password: str) -> str:
    return _cipher.encrypt(password.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    return _cipher.decrypt(encrypted.encode()).decode()


def do_login(student_id: str, password: str) -> dict | None:
    """登录获取 token，返回 dict 或 None"""
    payload = {
        "userCode": student_id,
        "password": password,
        "kaptcha": "testa",
        "userCodeType": "ldap",
    }

    try:
        resp = requests.post(LOGIN_URL, json=payload, headers=LOGIN_HEADERS, timeout=15)
        data = resp.json()
    except Exception as e:
        print(f"[auth] 登录请求异常: {e}")
        return None

    if data.get("errorCode") != "success":
        print(f"[auth] 登录失败: {data.get('errorMessage', '未知错误')}")
        return None

    token = data["data"]["token"]
    session = resp.cookies.get("SESSION", "")
    authcode = data["data"].get("authcode", student_id)

    return {
        "resToken": token,
        "session": session,
        "authcode": authcode,
        "token_expires_at": (datetime.now(TZ) + timedelta(hours=3)).replace(tzinfo=None),
    }
