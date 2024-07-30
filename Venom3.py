import subprocess
import time
import logging
import os
from aiogram import Bot
import asyncio
from asyncio.exceptions import TimeoutError
from keep_alive import keep_alive
import signal
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fetch environment variables
API_TOKEN = os.getenv('API_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')
MAX_RESTARTS = int(os.getenv('MAX_RESTARTS', 5))
RESTART_PERIOD = int(os.getenv('RESTART_PERIOD', 60))  # Seconds
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 5))  # Seconds
RESTART_DELAY = int(os.getenv('RESTART_DELAY', 10))  # Seconds
BOT_TIMEOUT = int(os.getenv('BOT_TIMEOUT', 300))  # Seconds for bot to stay alive before considering it crashed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
bot = Bot(API_TOKEN)

def start_bot():
    """Start the bot script as a subprocess."""
    return subprocess.Popen(['python', 'm.py'])

async def notify_admin(message):
    """Send a notification message to the admin via Telegram."""
    try:
        await bot.send_message(ADMIN_ID, message)
        logging.info("Admin notified: %s", message)
    except Exception as e:
        logging.error("Failed to send message to admin: %s", e)

async def health_check(process):
    """Perform periodic health checks to ensure the bot is responsive."""
    while True:
        if process.poll() is not None:
            logging.warning("Bot process is not running. Restart needed.")
            return
        try:
            await bot.get_me()
            logging.info("Bot is responsive.")
        except Exception as e:
            logging.error("Health check failed: %s", e)
        await asyncio.sleep(CHECK_INTERVAL)

async def monitor_bot(process):
    """Monitor the bot process and handle timeouts and restarts."""
    try:
        await asyncio.wait_for(process.wait(), timeout=BOT_TIMEOUT)
    except TimeoutError:
        logging.warning("Bot process timeout. Restarting...")
        await notify_admin("⚠️ Bot process timeout. Restarting...")

async def main():
    """Main function to manage bot process lifecycle."""
    restart_count = 0
    last_restart_time = time.time()

    while True:
        if restart_count >= MAX_RESTARTS:
            current_time = time.time()
            if current_time - last_restart_time < RESTART_PERIOD:
                wait_time = RESTART_PERIOD - (current_time - last_restart_time)
                logging.warning("Maximum restart limit reached. Waiting for %.2f seconds...", wait_time)
                await notify_admin(f"⚠️ Maximum restart limit reached. Waiting for {int(wait_time)} seconds before retrying.")
                await asyncio.sleep(wait_time)
            restart_count = 0
            last_restart_time = time.time()

        logging.info("Starting the bot...")
        process = start_bot()
        await notify_admin("🚀 Bot is starting...")

        try:
            # Start health check coroutine
            health_task = asyncio.create_task(health_check(process))
            await monitor_bot(process)
        except Exception as e:
            logging.error("Error in bot monitoring: %s", e)
            await notify_admin(f"⚠️ Error in bot monitoring: {e}")

        logging.warning("Bot process terminated. Restarting in %d seconds...", RESTART_DELAY)
        await notify_admin(f"⚠️ The bot has crashed and will be restarted in {RESTART_DELAY} seconds.")
        restart_count += 1
        await asyncio.sleep(RESTART_DELAY)

def signal_handler(signal, frame):
    logging.info("Received signal to terminate. Shutting down gracefully...")
    asyncio.run(notify_admin("🛑 Bot script terminated by user."))
    exit(0)

if __name__ == '__main__':
    try:
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        keep_alive()  # Start the keep_alive server to keep the session active
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Script terminated by user.")
        asyncio.run(notify_admin("🛑 Bot script terminated by user."))
