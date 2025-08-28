#!/bin/bash

# Скрипт запуска Telegram бота с PostgreSQL

echo "Запуск NSP QR Bot (PostgreSQL версия)..."

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo "Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активация виртуального окружения
source venv/bin/activate

# Установка зависимостей
echo "Установка зависимостей..."
pip install -r requirements.txt

# Проверка конфигурации
if [ ! -f "config.py" ]; then
    echo "Ошибка: файл config.py не найден!"
    exit 1
fi

# Проверка подключения к PostgreSQL
echo "Проверка подключения к базе данных..."
python3 -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from config import DATABASE_URL

async def test_connection():
    try:
        engine = create_async_engine(DATABASE_URL)
        async with engine.begin() as conn:
            await conn.execute('SELECT 1')
        print('✓ Подключение к PostgreSQL успешно')
        await engine.dispose()
        return True
    except Exception as e:
        print(f'✗ Ошибка подключения к PostgreSQL: {e}')
        return False

if not asyncio.run(test_connection()):
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "Не удалось подключиться к базе данных. Проверьте настройки в config.py"
    exit 1
fi

# Запуск бота
echo "Запуск бота..."
python3 qr_bot_postgres.py