#!/usr/bin/env python3
# NSP QR Bot Configuration


BOT_TOKEN = "NA"

# База данных PostgreSQL
DATABASE_URL = "postgresql://nsp_user:nsp_password@localhost/nsp_qr_db"

# Авторизованные пользователи (Telegram ID)
# Получить ID можно у @userinfobot
AUTHORIZED_USERS = [
    97915547,  # Замените на реальные ID кладовщиков
]

# API настройки
API_HOST = "0.0.0.0"
API_PORT = 8080

# API ключи
API_KEYS = {
    "nsp_mobile_app": "nsp_mobile_app_api_key_2024",
    "nsp_admin": "nsp_admin_api_key_2024"
}

# Логирование
LOG_LEVEL = "INFO"
LOG_FILE = "qr_bot.log"
API_LOG_FILE = "api_server.log"
