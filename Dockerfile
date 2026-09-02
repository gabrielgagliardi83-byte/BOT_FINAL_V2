FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    default-jdk \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool \
    && chmod +x apktool \
    && mv apktool /usr/local/bin/

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CORREÇÃO: Copia o bot.py com a função de payload
COPY bot.py .

# NÃO copia o payload pelo Git (será feito upload manual)
# COPY payload.b64 .

CMD ["python", "bot.py"]