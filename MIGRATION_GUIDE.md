# Руководство по переходу на PostgreSQL

## Обзор изменений

Проект переведен с SQLite на PostgreSQL с использованием SQLAlchemy ORM для лучшей масштабируемости и производительности.

## Основные изменения

### 1. Новые файлы
- `models.py` - ORM модели для PostgreSQL
- `api_server.py` - обновленный API сервер с PostgreSQL
- `qr_bot_postgres.py` - новая версия бота для PostgreSQL
- `migrate_to_postgres.py` - скрипт миграции данных

### 2. Обновленные файлы
- `config.py` - настроен для PostgreSQL
- `requirements.txt` - добавлена SQLAlchemy
- `requirements_api.txt` - добавлена SQLAlchemy

## Установка и настройка

### 1. Установка PostgreSQL

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# CentOS/RHEL
sudo yum install postgresql-server postgresql-contrib
sudo postgresql-setup initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 2. Создание базы данных

```bash
sudo -u postgres psql

CREATE DATABASE nsp_qr_db;
CREATE USER nsp_user WITH PASSWORD 'nsp_password';
GRANT ALL PRIVILEGES ON DATABASE nsp_qr_db TO nsp_user;
\q
```

### 3. Обновление зависимостей

```bash
pip install -r requirements.txt
pip install -r requirements_api.txt
```

### 4. Настройка конфигурации

Убедитесь, что в `config.py` правильно настроен `DATABASE_URL`:

```python
DATABASE_URL = "postgresql+asyncpg://nsp_user:nsp_password@localhost/nsp_qr_db"
```

### 5. Миграция данных (если есть существующие данные)

```bash
python migrate_to_postgres.py
```

## Запуск системы

### 1. Запуск API сервера

```bash
python api_server.py
```

### 2. Запуск Telegram бота

```bash
python qr_bot_postgres.py
```

## Структура базы данных

### Основные таблицы:

- `app_users` - пользователи мобильного приложения
- `qr_codes` - QR-коды и их информация
- `app_qr_scans` - история сканирований
- `point_transactions` - транзакции баллов
- `user_sessions` - сессии пользователей
- `products` - товары для обмена на баллы
- `news_articles` - новости
- `cars` - автомобили
- `orders` - заказы товаров
- `support_tickets` - тикеты поддержки

## Преимущества PostgreSQL

1. **Масштабируемость** - лучше подходит для больших объемов данных
2. **Производительность** - оптимизированные запросы и индексы
3. **ACID транзакции** - надежность данных
4. **Расширенные типы данных** - JSON, UUID, массивы
5. **Репликация и резервное копирование** - встроенные возможности

## Мониторинг и обслуживание

### Проверка состояния базы данных

```sql
-- Размер базы данных
SELECT pg_size_pretty(pg_database_size('nsp_qr_db'));

-- Активные соединения
SELECT count(*) FROM pg_stat_activity WHERE datname = 'nsp_qr_db';

-- Статистика таблиц
SELECT schemaname,tablename,n_tup_ins,n_tup_upd,n_tup_del 
FROM pg_stat_user_tables;
```

### Резервное копирование

```bash
# Создание бэкапа
pg_dump -U nsp_user -h localhost nsp_qr_db > backup.sql

# Восстановление из бэкапа
psql -U nsp_user -h localhost nsp_qr_db < backup.sql
```

## Устранение неполадок

### Проблемы с подключением

1. Проверьте настройки `pg_hba.conf`
2. Убедитесь, что PostgreSQL запущен
3. Проверьте правильность строки подключения

### Проблемы с производительностью

1. Создайте индексы для часто используемых полей
2. Настройте параметры PostgreSQL
3. Используйте EXPLAIN для анализа запросов

### Логи

- API сервер: `api_server.log`
- Telegram бот: `nsp_bot.log`
- PostgreSQL: `/var/log/postgresql/`

## Обратная совместимость

Старые файлы (`qr_bot.py` с SQLite) сохранены для обратной совместимости. Для полного перехода на PostgreSQL используйте новые файлы:

- `qr_bot_postgres.py` вместо `qr_bot.py`
- Обновленный `api_server.py`