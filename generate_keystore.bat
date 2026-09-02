@echo off
REM Generate release keystore for APK signing
REM You need Java JDK installed (keytool is included)

keytool -genkeypair ^
    -keystore release.keystore ^
    -alias release ^
    -keyalg RSA ^
    -keysize 2048 ^
    -validity 10000 ^
    -storepass android ^
    -keypass android ^
    -dname "CN=Release, OU=Dev, O=App, L=City, ST=State, C=US"

echo.
echo Keystore generated: release.keystore
echo Store password: android
echo Key password: android
echo.
echo Copy release.keystore to the same folder as bot.py
pause
