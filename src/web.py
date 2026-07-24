import os
import sys
import logging
import traceback

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"))
os.makedirs(DATA_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(DATA_DIR, "web_startup.log"), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("web")
logger.info("==========================================")
logger.info("Web App 开始启动...")

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

try:
    import threading
    import time
    import requests
    from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
    from fastapi.responses import HTMLResponse, RedirectResponse
    from pydantic import BaseModel
except Exception as e:
    logger.error(f"导入依赖失败: {e}")
    raise

from config import config_mgr, DATA_DIR
import bot_runner

app = FastAPI(title="Media-Bot Config")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Media-Bot Configuration</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 40px auto; padding: 20px; background: #f5f5f5; color: #333; }
        .card { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { margin-top: 0; color: #2c3e50; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; font-size: 14px; }
        input[type="text"], input[type="password"] { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
        button { background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-size: 16px; width: 100%; }
        button:hover { background: #2980b9; }
        .btn-test { background: #2ecc71; margin-top: 10px; }
        .btn-test:hover { background: #27ae60; }
        .alert { padding: 15px; margin-bottom: 20px; border-radius: 5px; }
        .alert-success { background: #d4edda; color: #155724; }
        .alert-error { background: #f8d7da; color: #721c24; }
        .hint { font-size: 12px; color: #7f8c8d; margin-top: 5px; display: block; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Bot 配置面板</h1>
        {% if message %}
        <div class="alert alert-{{ msg_type }}">{{ message }}</div>
        {% endif %}
        
        <form method="post" action="/save">
            <div class="form-group">
                <label>Telegram Bot Token</label>
                <input type="password" name="TG_BOT_TOKEN" value="{{ config.TG_BOT_TOKEN }}">
                <span class="hint">通过 @BotFather 获取的机器令牌</span>
            </div>
            
            <div class="form-group">
                <label>Telegram 允许的用户 ID</label>
                <input type="text" name="TG_ALLOWED_USERS" value="{{ config.TG_ALLOWED_USERS }}">
                <span class="hint">多个用逗号分隔，留空则允许任何人使用 (非常危险)</span>
            </div>
            
            <div class="form-group">
                <label>代理服务器地址 (TG_PROXY)</label>
                <input type="text" name="TG_PROXY" id="tg_proxy" value="{{ config.TG_PROXY }}">
                <span class="hint">例如: http://192.168.1.10:7890 (国内必须填写)</span>
                <button type="button" class="btn-test" onclick="testProxy()">测试 Telegram 连通性</button>
                <div id="test-result" style="margin-top: 10px; font-size: 14px;"></div>
            </div>
            
            <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0;">
            
            <div class="form-group">
                <label>MediaSeek API 地址</label>
                <input type="text" name="MEDIASEEK_URL" value="{{ config.MEDIASEEK_URL }}">
                <span class="hint">例如: http://mediaseek:8000 (如果在同一个 docker-compose 内)</span>
            </div>
            
            <div class="form-group">
                <label>MediaSeek 用户名</label>
                <input type="text" name="MEDIASEEK_USERNAME" value="{{ config.MEDIASEEK_USERNAME }}">
            </div>
            
            <div class="form-group">
                <label>MediaSeek 密码</label>
                <input type="password" name="MEDIASEEK_PASSWORD" value="{{ config.MEDIASEEK_PASSWORD }}">
            </div>
            
            <button type="submit">保存并重启 Bot</button>
        </form>
    </div>
    
    <script>
        function testProxy() {
            const proxy = document.getElementById('tg_proxy').value;
            const resDiv = document.getElementById('test-result');
            resDiv.innerHTML = '<span style="color: #f39c12;">正在测试连通性，请稍候...</span>';
            
            fetch('/test-proxy', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'proxy=' + encodeURIComponent(proxy)
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    resDiv.innerHTML = '<span style="color: #27ae60;">✅ 测试成功！状态码: ' + data.status + '，耗时: ' + data.time + 's</span>';
                } else {
                    resDiv.innerHTML = '<span style="color: #c0392b;">❌ 测试失败: ' + data.error + '</span>';
                }
            })
            .catch(err => {
                resDiv.innerHTML = '<span style="color: #c0392b;">❌ 请求出错: ' + err + '</span>';
            });
        }
    </script>
</body>
</html>
"""

from jinja2 import Template

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, msg: str = "", type: str = ""):
    template = Template(HTML_TEMPLATE)
    html = template.render(
        config=config_mgr.config,
        message=msg,
        msg_type=type
    )
    return html

@app.post("/save")
async def save_config(
    TG_BOT_TOKEN: str = Form(""),
    TG_ALLOWED_USERS: str = Form(""),
    TG_PROXY: str = Form(""),
    MEDIASEEK_URL: str = Form(""),
    MEDIASEEK_USERNAME: str = Form(""),
    MEDIASEEK_PASSWORD: str = Form("")
):
    config_mgr.set("TG_BOT_TOKEN", TG_BOT_TOKEN)
    config_mgr.set("TG_ALLOWED_USERS", TG_ALLOWED_USERS)
    config_mgr.set("TG_PROXY", TG_PROXY)
    config_mgr.set("MEDIASEEK_URL", MEDIASEEK_URL)
    config_mgr.set("MEDIASEEK_USERNAME", MEDIASEEK_USERNAME)
    config_mgr.set("MEDIASEEK_PASSWORD", MEDIASEEK_PASSWORD)
    
    bot_runner.restart_bot()
    
    return RedirectResponse(url="/?msg=配置已保存并已重启机器人后端进程&type=success", status_code=303)

@app.post("/test-proxy")
async def test_proxy(proxy: str = Form("")):
    proxy = proxy.strip()
    proxies = None
    if proxy:
        proxies = {
            "http": proxy,
            "https": proxy
        }
    
    start = time.time()
    try:
        res = requests.get("https://api.telegram.org", proxies=proxies, timeout=5)
        elapsed = round(time.time() - start, 2)
        return {"success": True, "status": res.status_code, "time": elapsed}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.on_event("startup")
async def on_startup():
    bot_runner.start_bot()

@app.on_event("shutdown")
async def on_shutdown():
    bot_runner.stop_bot()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
