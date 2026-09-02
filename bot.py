import os, base64, logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
TOKEN = "8673484762:AAG52YGWBfZlgl_rBQ3VrdmICxayMf59v8A"

PAYLOAD_B64 = """"""

PAYLOAD = None
try:
    PAYLOAD = base64.b64decode(PAYLOAD_B64)
    logger.info(f"✅ Payload: {len(PAYLOAD)} bytes")
except Exception as e:
    logger.error(f"❌ Erro: {e}")

async def status(update, context):
    if PAYLOAD:
        await update.message.reply_text(f"✅ Payload: {len(PAYLOAD)//(1024*1024)} MB")
    else:
        await update.message.reply_text("❌ Sem payload")

async def start(update, context):
    await update.message.reply_text("🤖 Bot APK Injector")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    logger.info("✅ Bot rodando!")
    app.run_polling()

if __name__ == "__main__":
    main()
