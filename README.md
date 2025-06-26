# NSP QR Bot - Система управления QR-кодами

![Python](https://img.shields.io/badge/Python-3.8+-green.svg)
![aiogram](https://img.shields.io/badge/aiogram-3.4+-blue.svg)
![SQLite](https://img.shields.io/badge/SQLite-3.0+-lightgrey.svg)

Telegram бот и REST API сервер для управления QR-кодами в программе лояльности NSP.

## Назначение

NSP QR Bot обеспечивает серверную часть программы лояльности для автозапчастей:

**Создание QR-кодов**
- Кладовщики через Telegram генерируют уникальные QR-коды для автозапчастей
- Каждый код содержит информацию о продукте и количестве баллов за покупку
- Автоматическое создание изображений QR-кодов для печати на упаковку

**Валидация сканирований**
- Проверка подлинности QR-кодов из мобильного приложения
- Одноразовое использование кодов (защита от мошенничества)
- Автоматическое начисление баллов пользователям

**API для мобильного приложения**
- Синхронизация данных между ботом и iOS приложением
- Управление пользователями, балансом баллов, товарами
- Поддержка офлайн режима с последующей синхронизацией

## Архитектура
Telegram Bot (создание QR) ←→ SQLite / PostgreSQL Database ←→ REST API ←→ iOS App
## Компоненты

**qr_bot.py** - Telegram бот
- Создание QR-кодов через интерактивный чат
- Статистика использования
- Административные функции

**api_server.py** - REST API сервер
- Аутентификация пользователей мобильного приложения
- Обработка сканирований QR-кодов
- Синхронизация данных (товары, новости, автомобили)

**database_schema.sql** - База данных
- QR-коды и статистика сканирований
- Пользователи мобильного приложения
- Транзакции баллов

## Установка

### Требования
- Python 3.8+
- Telegram Bot Token (от @BotFather)

### Настройка

1. Клонирование и установка зависимостей:
```bash
git clone https://github.com/your-username/nsp-qr-bot.git
cd nsp-qr-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements_api.txt


**### Проблемы (что вижу)**
В конфигурации (config.py):
python# База данных PostgreSQL
DATABASE_URL = "postgresql://nsp_user:nsp_password@localhost/nsp_qr_db"
В requirements указан PostgreSQL драйвер:
asyncpg==0.29.0
Но в коде фактически используется SQLite:
api_server.py
Код реально работает с SQLite, поэтому нужно исправить конфигурацию 




