import requests
import logging
from config import config_mgr

logger = logging.getLogger(__name__)

class MediaSeekClient:
    def __init__(self):
        self.session = requests.Session()
        self.token = None

    @property
    def base_url(self):
        return config_mgr.mediaseek_url

    def login(self):
        """登录 mediaseek 获取 token"""
        login_url = f"{self.base_url}/api/login"
        payload = {
            "username": config_mgr.mediaseek_username,
            "password": config_mgr.mediaseek_password
        }
        try:
            res = self.session.post(login_url, json=payload, timeout=5)
            if res.status_code == 200:
                data = res.json()
                self.token = data.get("token")
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                return True
            else:
                logger.error(f"登录 MediaSeek 失败: {res.text}")
                return False
        except Exception as e:
            logger.error(f"连接 MediaSeek 失败: {e}")
            return False

    def ensure_auth(self):
        if not self.token:
            return self.login()
        try:
            res = self.session.get(f"{self.base_url}/api/auth-check", timeout=3)
            if res.status_code != 200 or not res.json().get("authenticated"):
                return self.login()
            return True
        except:
            return self.login()

    def get_folders(self):
        if not self.ensure_auth():
            return []
        try:
            res = self.session.get(f"{self.base_url}/api/folders", timeout=5)
            if res.status_code == 200:
                return res.json()
            return ["/"]
        except:
            return ["/"]

    def extract_video(self, url):
        if not self.ensure_auth():
            return None, "无法连接到下载服务器或未授权"
        try:
            res = self.session.post(f"{self.base_url}/api/extract", json={"url": url}, timeout=45)
            if res.status_code == 200:
                return res.json(), None
            return None, f"解析失败: {res.status_code} - {res.text}"
        except Exception as e:
            return None, f"请求异常: {e}"

    def get_tasks(self):
        if not self.ensure_auth():
            return None, "未授权"
        try:
            res = self.session.get(f"{self.base_url}/api/tasks", timeout=5)
            if res.status_code == 200:
                return res.json(), None
            return None, f"请求失败: {res.status_code}"
        except Exception as e:
            return None, str(e)
            
    def get_history(self):
        if not self.ensure_auth():
            return None, "未授权"
        try:
            res = self.session.get(f"{self.base_url}/api/history", timeout=5)
            if res.status_code == 200:
                return res.json(), None
            return None, f"请求失败: {res.status_code}"
        except Exception as e:
            return None, str(e)

    def start_download(self, url, title=None, filename=None, save_path=None):
        if not self.ensure_auth():
            return None, "未授权"
        
        payload = {
            "url": url,
            "title": title or "Telegram Task",
            "filename": filename,
            "save_path": save_path
        }
        try:
            res = self.session.post(f"{self.base_url}/api/tasks", json=payload, timeout=5)
            if res.status_code == 200:
                return res.json().get("id"), None
            return None, f"提交失败: {res.status_code} - {res.text}"
        except Exception as e:
            return None, str(e)

api = MediaSeekClient()
