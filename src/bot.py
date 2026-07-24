import telebot
from telebot import apihelper, types
import logging
import time
import json
import os
from config import config_mgr, DATA_DIR
from api_client import api

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = None
PREFS_FILE = os.path.join(DATA_DIR, "user_prefs.json")
user_prefs = {}
user_states = {}

def load_prefs():
    global user_prefs
    if os.path.exists(PREFS_FILE):
        try:
            with open(PREFS_FILE, 'r') as f:
                user_prefs = json.load(f)
        except:
            user_prefs = {}

def save_prefs():
    with open(PREFS_FILE, 'w') as f:
        json.dump(user_prefs, f)

load_prefs()

def check_network():
    if not config_mgr.tg_proxy:
        return
    logger.info("进行网络连通性自检...")
    try:
        import requests
        res = requests.get('https://api.telegram.org', proxies={"http": config_mgr.tg_proxy, "https": config_mgr.tg_proxy}, timeout=5)
        logger.info(f"自检成功: API 返回状态码 {res.status_code}")
    except Exception as e:
        logger.error(f"自检失败: {e}")

def auth_required(func):
    def wrapper(message, *args, **kwargs):
        allowed = config_mgr.tg_allowed_users
        uid = message.from_user.id if hasattr(message, 'from_user') else message.message.from_user.id
        
        if allowed and uid not in allowed:
            if hasattr(message, 'chat'):
                bot.send_message(message.chat.id, "⚠️ 您没有权限使用此机器人。")
            return
        return func(message, *args, **kwargs)
    return wrapper

def init_bot():
    global bot
    config_mgr.apply_proxy_env()
    token = config_mgr.tg_bot_token
    if not token:
        logger.error("未配置 TG_BOT_TOKEN，Bot 无法启动")
        return False
    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=['start', 'help', 'menu'])
    @auth_required
    def send_welcome(message):
        show_main_menu(message.chat.id)

    @bot.callback_query_handler(func=lambda call: call.data == "main_menu")
    @auth_required
    def cb_main_menu(call):
        bot.answer_callback_query(call.id)
        show_main_menu(call.message.chat.id, call.message.message_id)

    def show_main_menu(chat_id, message_id=None):
        user_states[chat_id] = {'state': 'idle'}
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("➕ 新增下载", callback_data="new_download"),
            types.InlineKeyboardButton("▶️ 正在下载", callback_data="list_active"),
            types.InlineKeyboardButton("📜 历史记录", callback_data="list_history")
        )
        text = "🤖 **MediaSeek 下载控制台**\n\n请选择操作："
        if message_id:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data in ["list_active", "list_history"])
    @auth_required
    def cb_list_tasks(call):
        bot.answer_callback_query(call.id)
        is_active = call.data == "list_active"
        tasks, err = api.get_tasks() if is_active else api.get_history()
        
        if err:
            bot.send_message(call.message.chat.id, f"❌ 无法获取状态: {err}")
            return
            
        if not tasks:
            bot.send_message(call.message.chat.id, "目前没有相关任务。")
            show_main_menu(call.message.chat.id)
            return
            
        status_text = "📊 **正在下载的任务**\n\n" if is_active else "📜 **历史任务**\n\n"
        for task in tasks[:10]:
            name = task.get('title') or task.get('filename', 'Unknown')
            status = task.get('status', 'Unknown')
            progress = task.get('progress', 0)
            
            emoji = "⏳"
            if status == "downloading": emoji = "⬇️"
            elif status == "completed": emoji = "✅"
            elif status == "failed": emoji = "❌"
            
            status_text += f"{emoji} **{name}**\n状态: {status} | 进度: {progress:.1f}%\n---\n"
            
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("返回主菜单", callback_data="main_menu"))
        bot.edit_message_text(status_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data == "new_download")
    @auth_required
    def cb_new_download(call):
        bot.answer_callback_query(call.id)
        msg = bot.edit_message_text("🔗 请发送你需要下载的网页地址或 M3U8 链接：", chat_id=call.message.chat.id, message_id=call.message.message_id)
        user_states[call.message.chat.id] = {'state': 'waiting_url', 'msg_id': msg.message_id}

    @bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get('state') == 'waiting_url')
    @auth_required
    def handle_url_input(message):
        url = message.text.strip()
        chat_id = message.chat.id
        bot.delete_message(chat_id, message.message_id) # Delete user's URL message to keep chat clean
        
        state = user_states[chat_id]
        if not url.startswith(('http://', 'https://')):
            bot.edit_message_text("⚠️ 链接无效，请输入 http:// 或 https:// 开头的链接。请重新发送：", chat_id=chat_id, message_id=state['msg_id'])
            return
            
        bot.edit_message_text("⏳ 正在解析网页，请稍候...", chat_id=chat_id, message_id=state['msg_id'])
        
        result, err = api.extract_video(url)
        if err or not result:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("返回主菜单", callback_data="main_menu"))
            bot.edit_message_text(f"❌ 解析失败:\n{err or '未知错误'}", chat_id=chat_id, message_id=state['msg_id'], reply_markup=markup)
            user_states[chat_id]['state'] = 'idle'
            return
            
        if result.get("status") == "error" or not result.get("m3u8_urls"):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("返回主菜单", callback_data="main_menu"))
            bot.edit_message_text(f"⚠️ 解析警告:\n{result.get('message', '未找到视频流')}", chat_id=chat_id, message_id=state['msg_id'], reply_markup=markup)
            user_states[chat_id]['state'] = 'idle'
            return
            
        # Parse success
        title = result.get("title", "未命名视频")
        target_m3u8 = result["m3u8_urls"][0] # Just use the first one for simplicity
        
        state['url'] = target_m3u8
        state['title'] = title
        state['filename'] = f"{title}.mp4"
        state['state'] = 'confirm_name'
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton(f"✅ 使用名称: {title}", callback_data="confirm_name_default"),
            types.InlineKeyboardButton("✏️ 重命名", callback_data="rename_video"),
            types.InlineKeyboardButton("❌ 取消", callback_data="main_menu")
        )
        bot.edit_message_text(f"🎉 解析成功！\n\n**原始标题:** {title}\n**流地址:** `{target_m3u8}`\n\n请确认视频名称：", chat_id=chat_id, message_id=state['msg_id'], reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data in ["confirm_name_default", "rename_video"])
    @auth_required
    def cb_name_choice(call):
        bot.answer_callback_query(call.id)
        chat_id = call.message.chat.id
        state = user_states.get(chat_id, {})
        
        if call.data == "rename_video":
            bot.edit_message_text("✏️ 请输入新的视频名称：", chat_id=chat_id, message_id=call.message.message_id)
            state['state'] = 'waiting_rename'
        else:
            proceed_to_folder_selection(chat_id, call.message.message_id)

    @bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get('state') == 'waiting_rename')
    @auth_required
    def handle_rename_input(message):
        chat_id = message.chat.id
        new_title = message.text.strip()
        bot.delete_message(chat_id, message.message_id)
        
        state = user_states[chat_id]
        state['title'] = new_title
        state['filename'] = f"{new_title}.mp4"
        proceed_to_folder_selection(chat_id, state['msg_id'])

    def proceed_to_folder_selection(chat_id, msg_id):
        state = user_states[chat_id]
        state['state'] = 'select_folder'
        
        # Get folders
        folders = api.get_folders()
        pref_folder = user_prefs.get(str(chat_id), "/")
        
        if pref_folder not in folders:
            folders.append(pref_folder)
            
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        # Add default option
        markup.add(types.InlineKeyboardButton(f"✅ 默认 ({pref_folder})", callback_data=f"select_dir|{pref_folder}"))
        
        for f in set(folders):
            if f != pref_folder:
                # Callback data limit is 64 bytes. We might need to hash or map long paths, but keeping it simple for now.
                safe_f = f[:50]
                markup.add(types.InlineKeyboardButton(f"📁 {f}", callback_data=f"select_dir|{safe_f}"))
                
        markup.add(types.InlineKeyboardButton("❌ 取消", callback_data="main_menu"))
        
        text = f"📦 **最后一步：选择下载目录**\n\n即将下载: `{state['title']}`\n请选择要保存在服务器上的哪个文件夹？\n*(本次选择将作为下次的默认选项)*"
        bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("select_dir|"))
    @auth_required
    def cb_select_dir(call):
        bot.answer_callback_query(call.id)
        chat_id = call.message.chat.id
        folder = call.data.split("|", 1)[1]
        
        # Save preference
        user_prefs[str(chat_id)] = folder
        save_prefs()
        
        state = user_states.get(chat_id, {})
        if not state.get('url'):
            bot.edit_message_text("⚠️ 任务已过期，请重新开始。", chat_id=chat_id, message_id=call.message.message_id)
            return
            
        bot.edit_message_text(f"⏳ 正在向核心下载器提交任务 (保存至 {folder})...", chat_id=chat_id, message_id=call.message.message_id)
        
        # We append the chosen subfolder to the backend's base download dir
        # Wait, the backend uses `save_path`. If we just pass the folder name, we need the backend to join it?
        # Let's pass it as is. If the user selects "/", we pass empty.
        save_path = "" if folder == "/" else folder
        
        task_id, err = api.start_download(state['url'], title=state['title'], filename=state['filename'], save_path=save_path)
        
        if err:
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("返回主菜单", callback_data="main_menu"))
            bot.edit_message_text(f"❌ 提交失败:\n{err}", chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)
        else:
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("查看进度", callback_data="list_active"), types.InlineKeyboardButton("继续下载", callback_data="new_download"))
            bot.edit_message_text(f"✅ 任务提交成功！\n任务名称: `{state['title']}`\n保存目录: `{folder}`", chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup, parse_mode="Markdown")
            
        user_states[chat_id]['state'] = 'idle'
        
    @bot.message_handler(func=lambda message: True)
    @auth_required
    def fallback_handler(message):
        bot.send_message(message.chat.id, "🤖 欢迎使用 MediaSeek Bot！\n请点击左下角菜单，或者发送 /start 来唤出主界面。")
        
    return True

def run_bot():
    if not init_bot():
        return
    check_network()
    logger.info("Bot 开始轮询 (bot.polling)...")
    bot.polling(none_stop=True, interval=1, timeout=20)

def stop_bot_polling():
    if bot:
        bot.stop_polling()
