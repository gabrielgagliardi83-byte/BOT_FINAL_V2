#!/bin/bash

echo "🔍 Verificando payload..."

if [ -f "payload.b64" ]; then
    SIZE=$(wc -c < payload.b64 | xargs)
    SIZE_MB=$((SIZE / 1048576))
    echo "✅ Payload encontrado! Tamanho: ${SIZE_MB} MB"
else
    echo "⚠️ PAYLOAD NÃO ENCONTRADO!"
fi

echo "🚀 Iniciando bot..."
python bot.py