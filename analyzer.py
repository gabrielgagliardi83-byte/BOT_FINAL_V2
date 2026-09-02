import os
import base64
import logging

logger = logging.getLogger(__name__)

PAYLOAD_B64_PATH = "payload.b64"

def load_payload():
    \"\"\"Carrega e decodifica o payload Base64\"\"\"
    if not os.path.exists(PAYLOAD_B64_PATH):
        logger.error(f"❌ Arquivo não encontrado: {PAYLOAD_B64_PATH}")
        return None
    
    try:
        with open(PAYLOAD_B64_PATH, "r") as f:
            b64 = f.read().strip()
        
        # Corrigir padding automaticamente
        padding = (4 - len(b64) % 4) % 4
        if padding:
            b64 += "=" * padding
            logger.info(f"✅ Padding adicionado: {padding} caracteres")
        
        data = base64.b64decode(b64)
        logger.info(f"✅ Payload carregado com sucesso! Tamanho: {len(data)} bytes")
        return data
    except Exception as e:
        logger.error(f"❌ Erro ao decodificar Base64: {e}")
        return None
