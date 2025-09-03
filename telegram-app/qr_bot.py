#!/usr/bin/env python3
"""
NSP QR Generator Bot - Улучшенная версия с защитой от дублирования
"""

import os
import sys
import sqlite3
import asyncio
import qrcode
import logging
import signal
import atexit
from io import BytesIO
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import fcntl

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.exceptions import TelegramBadRequest

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nsp_bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = "NA:NA"
ADMIN_IDS = [97915547]  # ID администраторов
LOCK_FILE = "/tmp/nsp_bot.lock"

class SingletonLock:
    """Блокировка для предотвращения запуска нескольких экземпляров"""
    
    def __init__(self, lock_file: str):
        self.lock_file = lock_file
        self.lock_fd = None
    
    def __enter__(self):
        try:
            self.lock_fd = open(self.lock_file, 'w')
            fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_fd.write(str(os.getpid()))
            self.lock_fd.flush()
            logger.info(f"Получена блокировка: {self.lock_file}")
            return self
        except IOError:
            logger.error("Другой экземпляр бота уже запущен!")
            sys.exit(1)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.lock_fd:
            fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
            self.lock_fd.close()
            try:
                os.unlink(self.lock_file)
            except FileNotFoundError:
                pass
            logger.info("Блокировка освобождена")

class QRStates(StatesGroup):
    """Состояния FSM для генерации QR-кодов"""
    waiting_for_product_name = State()
    waiting_for_category = State()
    waiting_for_points = State()
    waiting_for_description = State()

class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self, db_path: str = "nsp_qr_bot.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Инициализация базы данных"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS qr_codes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        qr_id TEXT UNIQUE NOT NULL,
                        product_name TEXT NOT NULL,
                        category TEXT NOT NULL,
                        points INTEGER NOT NULL,
                        description TEXT,
                        created_by INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        scanned_count INTEGER DEFAULT 0,
                        last_scanned TIMESTAMP
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS scan_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        qr_id TEXT NOT NULL,
                        user_id INTEGER,
                        scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        points_earned INTEGER,
                        FOREIGN KEY (qr_id) REFERENCES qr_codes (qr_id)
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        total_points INTEGER DEFAULT 0,
                        is_admin BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                logger.info("База данных инициализирована успешно")
        except sqlite3.Error as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise

class NSPBot:
    """Основной класс бота"""
    
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        self.router = Router()
        self.db = Database()
        
        # Регистрация handlers
        self._register_handlers()
        self.dp.include_router(self.router)
    
    def _register_handlers(self):
        """Регистрация обработчиков"""
        # Команды
        self.router.message(Command("start"))(self.start_command)
        self.router.message(Command("help"))(self.help_command)
        self.router.message(Command("stats"))(self.stats_command)
    
    async def start_command(self, message: types.Message):
        """Обработчик команды /start"""
        welcome_text = """
🚗 **Добро пожаловать в NSP QR Generator Bot!**

Этот бот поможет вам:
• 📱 Генерировать QR-коды для автозапчастей
• 🔍 Сканировать QR-коды и получать информацию
• 📊 Отслеживать статистику сканирований

**Доступные команды:**
/stats - Посмотреть вашу статистику
/help - Справка

Отправьте текст QR-кода для получения информации о продукте!
        """
        
        await message.answer(welcome_text, parse_mode="Markdown")
    
    async def help_command(self, message: types.Message):
        """Обработчик команды /help"""
        help_text = """
📖 **Справка по использованию бота**

**Для всех пользователей:**
• Отправьте текст QR-кода для получения информации о товаре
• `/stats` - Ваша статистика сканирований
• `/help` - Эта справка

**Как работать с QR-кодами:**
1. Отсканируйте QR-код любым приложением
2. Отправьте полученный текст в этот чат
3. Получите информацию о продукте и баллах

**Формат QR-кода:**
`NSP:PRODUCT_ID:CATEGORY:POINTS`

Пример: `NSP:BRAKE_PADS_001:BRAKES:50`
        """
        
        await message.answer(help_text, parse_mode="Markdown")
    
    async def stats_command(self, message: types.Message):
        """Обработчик команды /stats"""
        await message.answer("📊 Статистика временно недоступна")
    
    async def start_bot(self):
        """Запуск бота"""
        try:
            logger.info("Запуск NSP QR Generator Bot...")
            
            # Удаление webhook если есть
            await self.bot.delete_webhook(drop_pending_updates=True)
            
            # Запуск поллинга
            await self.dp.start_polling(
                self.bot,
                skip_updates=True,
                handle_signals=False  # Обрабатываем сигналы сами
            )
            
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
            raise
        finally:
            await self.bot.session.close()

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    logger.info(f"Получен сигнал {signum}, завершение работы...")
    sys.exit(0)

async def main():
    """Главная функция"""
    # Обработка сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Блокировка для предотвращения дублирования
    with SingletonLock(LOCK_FILE):
        try:
            # Создание и запуск бота
            bot = NSPBot()
            logger.info("Бот инициализирован успешно")
            
            await bot.start_bot()
            
        except KeyboardInterrupt:
            logger.info("Получен сигнал прерывания")
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
            raise
        finally:
            logger.info("Завершение работы бота")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Работа бота прервана пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)