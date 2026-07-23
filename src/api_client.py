import requests
import logging
import config

logger = logging.getLogger(__name__)

class MediadoClient:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = config.MEDIADO_URL
        self.username = config.MEDIADO_USERNAME
        self.password = config.MEDIADO_PASSWORD
        self.logged_in = False

    def login(self):
        """登录主程序以获取 Session 验证"""
        login_url = f"{self.base_url}/login"
        payload = {
            "username": self.username,
            "password": self.password
        }
        try:
            response = self.session.post(login_url, data=payload, timeout=5)
            # Flask 的登录如果不成功通常会重新渲染登录页（包含"用户名或密码错误"）
            # 或者没有设置 session cookie
            if "用户名或密码错误" in response.text:
                logger.error("登录 Mediado 失败：用户名或密码错误。")
                self.logged_in = False
                return False
            
            # 如果成功，通常会重定向或返回有效 session
            self.logged_in = True
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"连接 Mediado 失败: {e}")
            self.logged_in = False
            return False

    def ensure_auth(self):
        """确保在发送请求前处于登录状态，如果未登录则尝试登录"""
        # 可以通过请求 /tasks 来测试当前 session 是否有效
        if self.logged_in:
            try:
                res = self.session.get(f"{self.base_url}/tasks", timeout=3, allow_redirects=False)
                if res.status_code == 302 and "/login" in res.headers.get("Location", ""):
                    # Session 失效，需要重新登录
                    self.logged_in = False
            except:
                pass
        
        if not self.logged_in:
            return self.login()
        return True

    def get_tasks(self):
        """获取所有任务列表"""
        if not self.ensure_auth():
            return None, "无法连接到下载服务器或登录失败"
        
        try:
            res = self.session.get(f"{self.base_url}/tasks", timeout=5)
            if res.status_code == 200:
                return res.json(), None
            else:
                return None, f"请求失败，状态码: {res.status_code}"
        except Exception as e:
            return None, f"连接异常: {str(e)}"

    def get_status(self, task_id):
        """获取单个任务状态"""
        if not self.ensure_auth():
            return None, "无法连接到下载服务器或登录失败"
        
        try:
            res = self.session.get(f"{self.base_url}/status/{task_id}", timeout=5)
            if res.status_code == 200:
                return res.json(), None
            elif res.status_code == 404:
                return None, "任务不存在"
            else:
                return None, f"请求失败，状态码: {res.status_code}"
        except Exception as e:
            return None, f"连接异常: {str(e)}"

    def start_download(self, url, output_file=None):
        """提交下载任务"""
        if not self.ensure_auth():
            return None, "无法连接到下载服务器或登录失败"
            
        if not output_file:
            output_file = "download_from_tg"
            
        payload = {
            "url": url,
            "output_file": output_file,
            "save_path": "",  # 使用默认路径
            "test_download": "false"
        }
        
        try:
            res = self.session.post(f"{self.base_url}/download", data=payload, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if "error" in data:
                    return None, data["error"]
                return data.get("task_id"), None
            else:
                return None, f"请求失败，状态码: {res.status_code}"
        except Exception as e:
            return None, f"连接异常: {str(e)}"

    def pause_task(self, task_id):
        if not self.ensure_auth(): return False, "未登录"
        try:
            res = self.session.post(f"{self.base_url}/pause/{task_id}", timeout=5)
            return res.status_code == 200, res.text
        except Exception as e: return False, str(e)
        
    def resume_task(self, task_id):
        if not self.ensure_auth(): return False, "未登录"
        try:
            res = self.session.post(f"{self.base_url}/resume/{task_id}", timeout=5)
            return res.status_code == 200, res.text
        except Exception as e: return False, str(e)
        
    def stop_task(self, task_id):
        if not self.ensure_auth(): return False, "未登录"
        try:
            res = self.session.post(f"{self.base_url}/stop/{task_id}", timeout=5)
            return res.status_code == 200, res.text
        except Exception as e: return False, str(e)
        
    def delete_task(self, task_id):
        if not self.ensure_auth(): return False, "未登录"
        try:
            res = self.session.post(f"{self.base_url}/delete/{task_id}", timeout=5)
            return res.status_code == 200, res.text
        except Exception as e: return False, str(e)

# 全局单例
api = MediadoClient()
