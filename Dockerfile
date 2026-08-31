FROM python:3.10-slim

WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    default-jdk \
    && rm -rf /var/lib/apt/lists/*

# Instala APKTool (se necessário)
RUN wget https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool \
    && chmod +x apktool \
    && mv apktool /usr/local/bin/

# Copia requirements e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código
COPY bot.py .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# NÃO copia payload.b64 (será adicionado via upload)

ENTRYPOINT ["./entrypoint.sh"]