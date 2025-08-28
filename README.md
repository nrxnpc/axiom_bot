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


## Переход на PostgreSQL ✅

Проект успешно переведен на PostgreSQL с использованием SQLAlchemy ORM.

### Новые файлы:
- `models.py` - ORM модели для PostgreSQL
- `qr_bot_postgres.py` - обновленная версия бота
- `api_server.py` - полностью переписанный API сервер
- `migrate_to_postgres.py` - скрипт миграции данных
- `MIGRATION_GUIDE.md` - подробное руководство

### Быстрый старт:

1. **Установка PostgreSQL:**
```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib

# Создание базы
sudo -u postgres createdb nsp_qr_db
sudo -u postgres createuser nsp_user
sudo -u postgres psql -c "ALTER USER nsp_user WITH PASSWORD 'nsp_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE nsp_qr_db TO nsp_user;"
```

2. **Установка зависимостей:**
```bash
pip install -r requirements.txt
pip install -r requirements_api.txt
```

3. **Миграция данных (если есть SQLite):**
```bash
python migrate_to_postgres.py
```

4. **Запуск:**
```bash
# Бот
bash start_postgres_bot.sh

# API сервер
bash start_postgres_api.sh
```

### Преимущества PostgreSQL:
- Масштабируемость и производительность
- ACID транзакции и надежность
- Поддержка JSON, UUID, массивов
- Встроенная репликация и бэкапы 




