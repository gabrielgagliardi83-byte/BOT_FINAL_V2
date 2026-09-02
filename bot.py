import os
import base64
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()

PAYLOAD = None

try:
    payload_paths = [
        "/app/payload_data.bin",
        "./payload_data.bin",
        os.path.join(os.path.dirname(__file__), "payload_data.bin"),
    ]

    for path in payload_paths:
        if os.path.exists(path):
            size = os.path.getsize(path)
            if size > 0:
                with open(path, "rb") as f:
                    PAYLOAD = f.read()
                logger.info(f"Payload loaded: {len(PAYLOAD)} bytes")
                break
            else:
                logger.warning(f"Empty file: {path}")

    if not PAYLOAD:
        logger.error("Payload not found")

except Exception as e:
    logger.error(f"Error loading payload: {e}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if PAYLOAD:
        mb = len(PAYLOAD) // (1024 * 1024)
        await update.message.reply_text(f"Payload loaded: {mb} MB")
    else:
        await update.message.reply_text("No payload loaded!")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "APK Analyzer Bot\n\n"
        "Commands:\n"
        "/status - Check payload\n"
        "/help - Help"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Help:\n\n"
        "/start - Start\n"
        "/status - Check payload\n"
        "/help - This message"
    )


def main():
    if not TOKEN:
        raise ValueError("TELEGRAM_TOKEN not set")

    logger.info(f"Token OK: {TOKEN[:10]}...")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("help", help_command))

    logger.info("Bot started!")
    app.run_polling()


if __name__ == "__main__":
    main()
