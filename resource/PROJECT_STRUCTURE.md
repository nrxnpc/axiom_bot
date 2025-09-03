# Структура проекта NSP QR Bot

## Директории

```
axiom_bot/
├── Makefile                     # Точка запуска проекта
├── scripts/                     # Скрипты для запуска и управления
│   ├── start-api.sh            # Запуск API сервера
│   ├── start-bot.sh            # Запуск Telegram бота
│   ├── start-postgres-api.sh   # Запуск PostgreSQL API сервера
│   ├── start-postgres-bot.sh   # Запуск PostgreSQL Telegram бота
│   ├── manage-services.sh      # Управление сервисами
│   └── install-deps.sh         # Установка зависимостей
├── server/                      # Код API сервера
│   ├── api_server.py           # Основной файл API сервера
│   ├── config.py               # Конфигурация сервера
│   ├── models.py               # Модели базы данных
│   ├── database_schema.sql     # Схема PostgreSQL
│   ├── migrate_to_postgres.py  # Скрипт миграции
│   └── requirements_api.txt    # Зависимости API
└── telegram-app/               # Код Telegram бота
    ├── qr_bot.py               # Основной файл бота (SQLite)
    ├── qr_bot_postgres.py      # Версия для PostgreSQL
    ├── config.py               # Конфигурация бота
    ├── models.py               # Модели для бота
    └── requirements.txt        # Зависимости бота
```

## Команды запуска

### Установка зависимостей
```bash
make install
```

### Запуск сервисов
```bash
make start-server   # Сервер (API + База данных)
make start-bot      # Telegram бот
```

### Копирование исходников в буфер обмена
```bash
make clipboard
```

## Использование

1. Установите зависимости: `make install`
2. Запустите сервер в одном терминале: `make start-server`
3. Запустите Telegram бота в другом терминале: `make start-bot`

Все команды выполняются из корневой директории проекта.