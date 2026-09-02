FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    default-jdk \
    && rm -rf /var/lib/apt/lists/*

# Install apktool script
RUN wget -q https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool \
    && chmod +x apktool \
    && mv apktool /usr/local/bin/

# Install apktool JAR (REQUIRED - without this, apktool command does nothing)
RUN wget -q https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_2.9.3.jar \
    && mv apktool_2.9.3.jar /usr/local/bin/apktool.jar

# Generate release keystore for signing
RUN keytool -genkeypair \
    -keystore /app/release.keystore \
    -alias release \
    -keyalg RSA \
    -keysize 2048 \
    -validity 10000 \
    -storepass android \
    -keypass android \
    -dname "CN=Release, OU=Dev, O=App, L=City, ST=State, C=US"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .
COPY payload_data.bin .

CMD ["python", "bot.py"]
