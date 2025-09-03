#!/usr/bin/env python3
# NSP QR Bot Configuration for Telegram App

BOT_TOKEN = "NA"

# База данных PostgreSQL
DATABASE_URL = "postgresql+asyncpg://nsp_user:nsp_password@localhost/nsp_qr_db"

# Авторизованные пользователи (Telegram ID)
AUTHORIZED_USERS = [
    97915547,  # Замените на реальные ID кладовщиков
]

# Логирование
LOG_LEVEL = "INFO"
LOG_FILE = "qr_bot.log"