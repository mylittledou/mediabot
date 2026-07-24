import threading
import time
import logging
from bot import run_bot, stop_bot_polling

logger = logging.getLogger(__name__)

bot_thread = None
running = False

def bot_worker():
    global running
    while running:
        try:
            run_bot()
            if running:
                time.sleep(5)
        except Exception as e:
            if not running:
                break
            logger.error(f"Bot loop crashed: {e}")
            time.sleep(5)

def start_bot():
    global bot_thread, running
    if bot_thread and bot_thread.is_alive():
        return
    
    running = True
    bot_thread = threading.Thread(target=bot_worker, daemon=True)
    bot_thread.start()
    logger.info("Bot thread started.")

def stop_bot():
    global bot_thread, running
    running = False
    stop_bot_polling()
    if bot_thread:
        bot_thread.join(timeout=3)
    logger.info("Bot thread stopped.")

def restart_bot():
    stop_bot()
    time.sleep(1)
    start_bot()
