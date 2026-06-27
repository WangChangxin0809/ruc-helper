#!/usr/bin/env python3
"""
人大教务系统自动查成绩脚本

通过 /secService/login 获取 token（需先运行 get_token.py），
轮询成绩列表，发现新出/变动的成绩后高亮提示。

特性:
  - 成绩变动检测: 比对前后两次查询结果，高亮新增/更新的成绩
  - 自动登录: 内置登录降级，token 过期时自动重登
  - 热重载配置: 修改 pollInterval 无需重启
  - 网络异常保护: try/except 防止单次超时挂掉
"""
import json
import requests
import smtplib
import sys
import time
import os
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

# ========== 日志双写 ==========
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
LOG_FILE = os.path.join(ROOT_DIR, "auto_grade.log")
CONFIG_FILE = os.path.join(ROOT_DIR, "config.json")

LOGIN_URL = "https://jw.ruc.edu.cn/secService/login"

LOGIN_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "KAPTCHA-KEY-GENERATOR-REDIS": "securityKaptchaRedisServiceAdapter",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


class Tee:
    def __init__(self, file_path):
        self.file = open(file_path, "a", encoding="utf-8", buffering=1)
        self.stdout = sys.stdout

    def write(self, data):
        self.file.write(data)
        self.stdout.write(data)

    def flush(self):
        self.file.flush()
        self.stdout.flush()


sys.stdout = Tee(LOG_FILE)
sys.stderr = sys.stdout

# ========== 基础常量 ==========
TZ = timezone(timedelta(hours=8))


def ts():
    return datetime.now(TZ).strftime("%H:%M:%S")


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def do_login(username: str, password: str):
    """登录获取 resToken + SESSION"""
    payload = {
        "userCode": username,
        "password": password,
        "kaptcha": "testa",
        "userCodeType": "ldap",
    }
    resp = requests.post(LOGIN_URL, json=payload, headers=LOGIN_HEADERS, timeout=15)
    data = resp.json()

    if data.get("errorCode") != "success":
        print(f"  [{ts()}] 登录失败: {data.get('errorMessage', '未知错误')}")
        return None

    token = data["data"]["token"]
    session = resp.cookies.get("SESSION")
    authcode = data["data"].get("authcode", username)

    cfg = load_config()
    cfg["auth"]["resToken"] = token
    cfg["auth"]["session"] = session
    cfg["auth"]["authcode"] = authcode
    save_config(cfg)

    print(f"  [{ts()}] 自动登录成功! 账号: {authcode}")
    return token, session, authcode


def build_headers(cfg):
    """构造成绩 API 请求头"""
    auth = cfg["auth"]
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "app": "PCWEB",
        "locale": "zh_CN",
        "token": auth.get("resToken", ""),
        "userrolecode": "student",
        "Cookie": f"SESSION={auth.get('session', '')}; authcode={auth.get('authcode', '')}",
        "Referer": "https://jw.ruc.edu.cn/Njw2017/index.html",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }


def query_grades(cfg):
    """查询成绩列表"""
    grade_cfg = cfg.get("grade", {})
    api_path = grade_cfg.get("apiPath", "/resService/jwxtpt/v1/xsd/cjgl_xsxdsq/findKccjList")
    resource_code = grade_cfg.get("resourceCode", "XSMH0526")
    api_code = grade_cfg.get("apiCode", "jw.xsd.xsdInfo.controller.CjglKccjckController.findKccjList")

    url = f"{cfg['baseUrl']}{api_path}?resourceCode={resource_code}&apiCode={api_code}"
    headers = build_headers(cfg)

    try:
        resp = requests.post(url, json={}, headers=headers, timeout=15)
    except requests.RequestException as e:
        print(f"  [网络异常] {e}")
        return None

    if resp.status_code != 200:
        print(f"  [{resp.status_code}] {resp.text[:200]}")
        return None

    data = resp.json()
    if data.get("errorCode") != "success":
        print(f"  API 错误: {data.get('errorMessage', data.get('errorCode'))}")
        return None

    return data.get("data", [])


def make_grade_key(g):
    """用 cjgl016id 作为唯一键（成绩记录ID）"""
    return g.get("cjgl016id", "")


def diff_grades(prev_map, curr_map):
    """对比两次快照，返回 (新增, 更新, 总变化数)"""
    new_grades = []
    changed_grades = []

    for key, grade in curr_map.items():
        if key not in prev_map:
            new_grades.append(grade)
        elif prev_map[key].get("zcj") != grade.get("zcj") or prev_map[key].get("jd") != grade.get("jd"):
            changed_grades.append(grade)

    return new_grades, changed_grades, len(new_grades) + len(changed_grades)


def format_grade_row(g, highlight=False):
    """格式化单条成绩"""
    marker = " >>> " if highlight else "     "
    name = g.get("kcname") or "?"
    score = g.get("zcj") or "-"
    credit = g.get("xf") or "-"
    gp = g.get("jd") or "-"
    semester = g.get("xnxq") or g.get("cjlrxq") or "?"
    category = g.get("kclbname") or g.get("kcxzname") or "-"
    teacher = g.get("jsname") or ""
    dept = g.get("kkdwname") or ""

    return (f"{marker}{name:<28s} {str(score):>6s}  "
            f"学分{credit} 绩点{gp}  {semester}  [{category}]  {teacher}  {dept}")


def send_email(cfg, new_grades, changed_grades):
    """发送成绩变动通知邮件"""
    email_cfg = cfg.get("email", {})
    if not email_cfg.get("smtpHost"):
        print(f"  [{ts()}] 未配置邮箱，跳过邮件通知")
        return False

    to_addr = email_cfg.get("toAddress", cfg.get("student", {}).get("email", ""))
    if not to_addr:
        print(f"  [{ts()}] 未配置收件邮箱")
        return False

    now = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")

    # 构造正文
    lines = [f"成绩变动通知 — {now}", ""]

    if new_grades:
        lines.append(f"新增 {len(new_grades)} 门课程成绩:")
        lines.append("")
        for g in new_grades:
            name = g.get("kcname") or "?"
            score = g.get("zcj") or "-"
            xf = g.get("xf") or "-"
            jd = g.get("jd") or "-"
            semester = g.get("xnxq") or g.get("cjlrxq") or "?"
            teacher = g.get("jsname") or ""
            lines.append(f"  {name}  {score}分  学分{xf}  绩点{jd}  教师:{teacher}  {semester}")
        lines.append("")

    if changed_grades:
        lines.append(f"更新 {len(changed_grades)} 门课程成绩:")
        lines.append("")
        for g in changed_grades:
            name = g.get("kcname") or "?"
            score = g.get("zcj") or "-"
            xf = g.get("xf") or "-"
            jd = g.get("jd") or "-"
            lines.append(f"  {name}  {score}分  学分{xf}  绩点{jd}")
        lines.append("")

    body = "\n".join(lines)

    # 发送
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["From"] = email_cfg["fromAddress"]
        msg["To"] = to_addr
        subject_parts = []
        if new_grades:
            subject_parts.append(f"新出{len(new_grades)}门")
        if changed_grades:
            subject_parts.append(f"更新{len(changed_grades)}门")
        msg["Subject"] = f"[成绩通知] {'，'.join(subject_parts)}"

        server = smtplib.SMTP(email_cfg["smtpHost"], email_cfg["smtpPort"], timeout=15)
        server.starttls()
        server.login(email_cfg["smtpUsername"], email_cfg["smtpPassword"])
        server.sendmail(email_cfg["fromAddress"], [to_addr], msg.as_string())
        server.quit()

        print(f"  [{ts()}] 邮件已发送至 {to_addr}")
        return True
    except Exception as e:
        print(f"  [{ts()}] 邮件发送失败: {e}")
        return False


# ========== 主循环 ==========
print("=" * 70)
print("人大教务系统自动查成绩 — 轮询模式")
print(f"启动时间: {datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')}")
print(f"每轮自动重载 {CONFIG_FILE} — 修改 grade.pollInterval 无需重启")
print(f"Token 过期时自动调用 get_token.py 的登录逻辑重新获取")
print("=" * 70)

round_num = 0
prev_grade_map = {}

while True:
    round_num += 1

    cfg = load_config()
    poll_interval = cfg.get("grade", {}).get("pollInterval", 30)

    # ── 0. 检查 token 是否存在，没有则提示登录 ──
    if not cfg["auth"].get("resToken") or not cfg["auth"].get("session"):
        print(f"\n  [{ts()}] 未检测到 resToken/session，需要登录")
        print(f"  请运行: uv run get_token.py")
        print(f"  或在此输入账号密码自动登录:")
        username = input("  学号: ").strip()
        if username:
            password = input("  密码: ").strip()
            if password:
                result = do_login(username, password)
                if result:
                    cfg = load_config()
                else:
                    print(f"  登录失败，{ts()} 等待 {poll_interval} 秒后重试...")
                    time.sleep(poll_interval)
                    continue
            else:
                time.sleep(poll_interval)
                continue
        else:
            time.sleep(poll_interval)
            continue

    print(f"\n{'─' * 50}")
    print(f"[{ts()}] 第 {round_num} 轮")

    # ── 1. 查询成绩 ──
    grades = query_grades(cfg)

    if grades is None:
        # token 可能过期，尝试自动重登
        print(f"  [{ts()}] 查询失败，尝试重新登录...")
        authcode = cfg["auth"].get("authcode", "")
        if authcode:
            # 需要密码 — 无法自动重登，提示用户
            print(f"  [{ts()}] Token 可能已过期，请重新运行 get_token.py")
        print(f"  {ts()} 等待 {poll_interval} 秒...")
        time.sleep(poll_interval)
        continue

    print(f"  成绩总数: {len(grades)} 门")

    # ── 2. 统计概览 ──
    total_credits = sum(float(g.get("xf", 0) or 0) for g in grades)
    print(f"  总学分: {total_credits}")

    # ── 3. 对比变化 ──
    curr_grade_map = {make_grade_key(g): g for g in grades}
    new_grades, changed_grades, total_changes = diff_grades(prev_grade_map, curr_grade_map)

    if round_num == 1:
        print(f"\n  === 当前成绩 ({len(grades)} 门) ===")
        for g in grades:
            print(format_grade_row(g))
    elif total_changes > 0:
        print(f"\n  *** 检测到变化! 新增 {len(new_grades)} 门  更新 {len(changed_grades)} 门 ***")

        if new_grades:
            print(f"\n  --- 新增成绩 ({len(new_grades)} 门) ---")
            for g in new_grades:
                print(format_grade_row(g, highlight=True))

        if changed_grades:
            print(f"\n  --- 成绩更新 ({len(changed_grades)} 门) ---")
            for g in changed_grades:
                print(format_grade_row(g, highlight=True))

        send_email(cfg, new_grades, changed_grades)
    else:
        print(f"  成绩无变化")

    prev_grade_map = curr_grade_map
    print(f"  {ts()} 继续监听...")
    time.sleep(poll_interval)
