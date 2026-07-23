import telebot
from telebot import apihelper
import logging
import time
import re
from config import TG_BOT_TOKEN, TG_ALLOWED_USERS, TG_PROXY, check_config
from api_client import api

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置代理 (如果环境变量提供了代理)
if TG_PROXY:
    logger.info(f"使用代理服务器: {repr(TG_PROXY)} (已通过环境变量全局注入)")

def check_network():
    if not TG_PROXY:
        return
    logger.info("进行网络连通性自检...")
    try:
        import requests
        res = requests.get('https://api.telegram.org', timeout=5)
        logger.info(f"自检成功: API 返回状态码 {res.status_code}")
        return True
    except Exception as e:
        logger.error(f"自检失败，底层 requests 无法连接 Telegram: {e}")
        try:
            import socket
            from urllib.parse import urlparse
            parsed = urlparse(TG_PROXY)
            logger.info(f"尝试原生 Socket 连接到代理机 {parsed.hostname}:{parsed.port}...")
            s = socket.create_connection((parsed.hostname, parsed.port), timeout=3)
            s.close()
            logger.info("原生 Socket 连接代理机成功！这说明是 requests 库或者 telebot 的代理配置问题。")
        except Exception as sock_e:
            logger.error(f"原生 Socket 连接代理机也失败了: {sock_e}。容器此时可能还没有通往代理的路由。")
        return False

# 检查配置
try:
    check_config()
except ValueError as e:
    logger.error(str(e))
    exit(1)

# 初始化 Bot
bot = telebot.TeleBot(TG_BOT_TOKEN)

# 鉴权装饰器：只允许授权用户使用
def auth_required(func):
    def wrapper(message, *args, **kwargs):
        if TG_ALLOWED_USERS and message.from_user.id not in TG_ALLOWED_USERS:
            logger.warning(f"未授权用户尝试访问: ID={message.from_user.id}, Username={message.from_user.username}")
            bot.reply_to(message, "⚠️ 您没有权限使用此机器人。")
            return
        return func(message, *args, **kwargs)
    return wrapper

@bot.message_handler(commands=['start', 'help'])
@auth_required
def send_welcome(message):
    help_text = (
        "🤖 **Mediado 下载助手**\n\n"
        "你可以直接向我发送 HTTP/HTTPS 链接，我会将其发送给核心下载器。\n\n"
        "**可用命令:**\n"
        "/status - 查看所有任务当前的状态\n"
        "/help - 显示此帮助信息\n\n"
        "**如何下载:**\n"
        "直接发送视频 URL，例如:\n"
        "`https://example.com/video.m3u8`\n\n"
        "或者指定文件名 (URL和文件名之间用空格或换行分隔):\n"
        "`https://example.com/video.m3u8 我的视频`"
    )
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['status', 'list'])
@auth_required
def check_status(message):
    bot.send_chat_action(message.chat.id, 'typing')
    tasks, err = api.get_tasks()
    
    if err:
        bot.reply_to(message, f"❌ 无法获取状态: {err}")
        return
        
    if not tasks:
        bot.reply_to(message, "目前没有任何下载任务。")
        return
        
    status_text = "📊 **当前下载任务列表**\n\n"
    active_count = 0
    
    for task in tasks:
        if task['status'] == 'completed':
            continue
            
        active_count += 1
        name = task.get('output_file', 'Unknown')
        status = task.get('status', 'Unknown')
        progress = task.get('progress', 0)
        speed = task.get('speed', 0)
        
        emoji = "⏳"
        if status == "downloading": emoji = "⬇️"
        elif status == "paused": emoji = "⏸️"
        elif status == "failed": emoji = "❌"
        
        status_text += f"{emoji} **{name}**\n"
        status_text += f"状态: {status} | 进度: {progress:.1f}%\n"
        if status == "downloading":
            status_text += f"速度: {speed:.1f} KB/s\n"
        status_text += "------------------------\n"
    
    if active_count == 0:
        status_text = "目前所有任务均已完成，没有正在进行中的下载。"
        
    if len(status_text) > 4000:
        status_text = status_text[:4000] + "\n...(内容过长截断)"
        
    bot.reply_to(message, status_text, parse_mode='Markdown')


@bot.message_handler(func=lambda message: True)
@auth_required
def handle_text(message):
    text = message.text.strip()
    
    parts = re.split(r'\s+', text, 1)
    url = parts[0]
    filename = parts[1] if len(parts) > 1 else None
    
    if not url.startswith(('http://', 'https://')):
        bot.reply_to(message, "⚠️ 请发送有效的 HTTP/HTTPS 链接。")
        return
        
    reply = bot.reply_to(message, "⏳ 正在将任务提交给核心下载器...")
    
    task_id, err = api.start_download(url, filename)
    
    if err:
        bot.edit_message_text(f"❌ 提交失败:\n{err}", chat_id=message.chat.id, message_id=reply.message_id)
    else:
        bot.edit_message_text(f"✅ 任务已成功提交!\n任务ID: `{task_id}`\n可以使用 /status 命令查看进度。", 
                              chat_id=message.chat.id, 
                              message_id=reply.message_id,
                              parse_mode='Markdown')

if __name__ == '__main__':
    logger.info("Bot 进程启动...")
    # 强制进行一次初始网络检查
    check_network()
    
    while True:
        try:
            logger.info("开始连接 Telegram 服务器 (bot.polling)...")
            bot.polling(none_stop=True, interval=1, timeout=20)
        except Exception as e:
            logger.error(f"Bot 运行出错: {e}")
            logger.info("准备在 5 秒后重试...")
            time.sleep(5)
            # 每次重试前都检查一下网络，看是否恢复
            check_network()
            # 强制重建 requests Session，防止旧连接池缓存了错误的路由/DNS状态
            import requests
            apihelper.session = requests.Session()
