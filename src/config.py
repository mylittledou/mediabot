import os
from dotenv import load_dotenv

# 加载本地 .env 文件（如果存在）
load_dotenv()

# Telegram Bot Token
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")

# 允许访问的 Telegram User IDs（逗号分隔的数字）
_allowed_users_str = os.getenv("TG_ALLOWED_USERS", "")
TG_ALLOWED_USERS = []
if _allowed_users_str:
    try:
        TG_ALLOWED_USERS = [int(uid.strip()) for uid in _allowed_users_str.split(",") if uid.strip()]
    except ValueError:
        print("警告: TG_ALLOWED_USERS 格式错误，应为逗号分隔的数字。")

# mediado 主程序的 API 地址，默认 http://127.0.0.1:5000
MEDIADO_URL = os.getenv("MEDIADO_URL", "http://127.0.0.1:5000").rstrip("/")

# mediado 主程序的网页登录账号和密码
MEDIADO_USERNAME = os.getenv("MEDIADO_USERNAME", "admin")
MEDIADO_PASSWORD = os.getenv("MEDIADO_PASSWORD", "password")

def check_config():
    if not TG_BOT_TOKEN:
        raise ValueError("请设置 TG_BOT_TOKEN 环境变量")
    if not TG_ALLOWED_USERS:
        print("警告: TG_ALLOWED_USERS 未设置或为空，任何用户都可以使用此机器人！建议设置您的 User ID。")
