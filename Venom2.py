import subprocess
import time
import logging
from aiogram import Bot
import asyncio
from asyncio.exceptions import TimeoutError
from keep_alive import keep_alive

API_TOKEN = '7399735507:AAHrbAgM3NLApic89e57d1C87U-0876Sg-8'
ADMIN_ID = '6092284993'
MAX_RESTARTS = 5
RESTART_PERIOD = 60  # Seconds
CHECK_INTERVAL = 5  # Seconds
RESTART_DELAY = 10  # Seconds
BOT_TIMEOUT = 300  # Seconds for bot to stay alive before considering it crashed

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
            await monitor_bot(process)
        except Exception as e:
            logging.error("Error in bot monitoring: %s", e)
            await notify_admin(f"⚠️ Error in bot monitoring: {e}")

        logging.warning("Bot process terminated. Restarting in %d seconds...", RESTART_DELAY)
        await notify_admin(f"⚠️ The bot has crashed and will be restarted in {RESTART_DELAY} seconds.")
        restart_count += 1
        await asyncio.sleep(RESTART_DELAY)

if __name__ == '__main__':
    try:
        keep_alive()  # Start the keep_alive server to keep the session active
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Script terminated by user.")
        asyncio.run(notify_admin("🛑 Bot script terminated by user."))
