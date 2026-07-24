import os
import json
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"))
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
os.makedirs(DATA_DIR, exist_ok=True)

class ConfigManager:
    def __init__(self):
        self.config = {}
        self.load()

    def load(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            # Fallback to env vars
            self.config = {
                "TG_BOT_TOKEN": os.getenv("TG_BOT_TOKEN", ""),
                "TG_ALLOWED_USERS": os.getenv("TG_ALLOWED_USERS", ""),
                "MEDIASEEK_URL": os.getenv("MEDIASEEK_URL", os.getenv("MEDIADO_URL", "http://mediaseek:8000")).rstrip("/"),
                "MEDIASEEK_USERNAME": os.getenv("MEDIASEEK_USERNAME", os.getenv("MEDIADO_USERNAME", "admin")),
                "MEDIASEEK_PASSWORD": os.getenv("MEDIASEEK_PASSWORD", os.getenv("MEDIADO_PASSWORD", "admin")),
                "TG_PROXY": os.getenv("TG_PROXY", "").strip()
            }
            self.save()

    def save(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4)

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()

    @property
    def tg_bot_token(self):
        return self.get("TG_BOT_TOKEN", "")

    @property
    def tg_allowed_users(self):
        users_str = self.get("TG_ALLOWED_USERS", "")
        if not users_str: return []
        try:
            return [int(uid.strip()) for uid in str(users_str).split(",") if uid.strip()]
        except ValueError:
            return []

    @property
    def mediaseek_url(self):
        return self.get("MEDIASEEK_URL", "http://mediaseek:8000").rstrip("/")

    @property
    def mediaseek_username(self):
        return self.get("MEDIASEEK_USERNAME", "admin")

    @property
    def mediaseek_password(self):
        return self.get("MEDIASEEK_PASSWORD", "admin")

    @property
    def tg_proxy(self):
        return str(self.get("TG_PROXY", "")).strip() or None

    def apply_proxy_env(self):
        proxy = self.tg_proxy
        if proxy:
            os.environ['HTTP_PROXY'] = proxy
            os.environ['HTTPS_PROXY'] = proxy
            os.environ['http_proxy'] = proxy
            os.environ['https_proxy'] = proxy
            os.environ['NO_PROXY'] = 'localhost,127.0.0.0/8,192.168.0.0/16,10.0.0.0/8,172.16.0.0/12,169.254.0.0/16,mediaseek'
            os.environ['no_proxy'] = os.environ['NO_PROXY']
        else:
            for k in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'NO_PROXY', 'no_proxy']:
                if k in os.environ:
                    del os.environ[k]

config_mgr = ConfigManager()
