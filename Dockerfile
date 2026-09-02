FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    default-jdk \
    && rm -rf /var/lib/apt/lists/*

# Install apktool
RUN wget -q https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool \
    && chmod +x apktool \
    && mv apktool /usr/local/bin/

RUN wget -q https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_2.9.3.jar \
    && mv apktool_2.9.3.jar /usr/local/bin/apktool.jar

# Install Android SDK command-line tools
RUN mkdir -p /opt/android-sdk/cmdline-tools && \
    cd /tmp && \
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip && \
    unzip -q commandlinetools-linux-11076708_latest.zip -d /opt/android-sdk/cmdline-tools && \
    mv /opt/android-sdk/cmdline-tools/cmdline-tools /opt/android-sdk/cmdline-tools/latest && \
    rm commandlinetools-linux-11076708_latest.zip

ENV ANDROID_HOME=/opt/android-sdk
ENV PATH="${PATH}:/opt/android-sdk/cmdline-tools/latest/bin"

# Accept licenses and install build-tools (includes apksigner + zipalign)
RUN yes | sdkmanager --licenses > /dev/null 2>&1 && \
    sdkmanager "build-tools;34.0.0" > /dev/null 2>&1

# Create symlinks for apksigner and zipalign
RUN ln -sf /opt/android-sdk/build-tools/34.0.0/apksigner /usr/local/bin/apksigner && \
    ln -sf /opt/android-sdk/build-tools/34.0.0/zipalign /usr/local/bin/zipalign && \
    chmod +x /opt/android-sdk/build-tools/34.0.0/apksigner && \
    chmod +x /opt/android-sdk/build-tools/34.0.0/zipalign

# Generate release keystore
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
