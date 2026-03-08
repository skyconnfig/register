"""
工具函数
"""
import random
import string
import time
import json
from datetime import datetime
from config import EMAIL_PREFIX, EMAIL_DOMAIN, API_KEYS_FILE


def generate_random_suffix(length=8):
    """生成随机字符串后缀"""
    characters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def generate_email(email_prefix=None):
    """生成随机邮箱地址"""
    # 使用动态前缀 + 随机后缀
    if email_prefix is None:
        prefix = EMAIL_PREFIX  # 使用配置文件中的默认前缀
    else:
        prefix = email_prefix

    suffix = generate_random_suffix()
    return f"{prefix}-{suffix}@{EMAIL_DOMAIN}"


def save_api_key(email, api_key, password=None):
    """保存API key和账户信息到文件（简化格式）"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 简化格式：邮箱,密码,API Key,注册时间;
    account_line = f"{email},{password if password else 'N/A'},{api_key},{timestamp};\n"

    # 追加到文件末尾
    try:
        with open(API_KEYS_FILE, 'a', encoding='utf-8') as f:
            f.write(account_line)
    except FileNotFoundError:
        # 如果文件不存在，创建新文件
        with open(API_KEYS_FILE, 'w', encoding='utf-8') as f:
            f.write(account_line)

    print(f"✅ 账户信息已保存到 {API_KEYS_FILE}")
    print(f"📧 邮箱: {email}")
    print(f"🔐 密码: {password if password else 'N/A'}")
    print(f"🔑 API Key: {api_key}")
    print(f"⏰ 时间: {timestamp}")


def save_cookies(cookies, filename):
    """保存cookies到文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(cookies, f, indent=2)


def load_cookies(filename):
    """从文件加载cookies"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def wait_with_message(seconds, message="等待中"):
    """带消息的等待函数"""
    print(f"⏳ {message}，等待 {seconds} 秒...")
    time.sleep(seconds)
