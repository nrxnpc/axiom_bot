#!/usr/bin/env python3
"""
NSP QR Generator Bot - PostgreSQL версия
"""

import asyncio
import qrcode
import logging
import uuid
from io import BytesIO
from datetime import datetime
from typing import Optional, Dict, Any

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from config import BOT_TOKEN, AUTHORIZED_USERS, DATABASE_URL
from models import Base, QRCode, AppUser, AppQRScan, PointTransaction

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nsp_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class QRStates(StatesGroup):
    """Состояния FSM для генерации QR-кодов"""
    waiting_for_product_name = State()
    waiting_for_category = State()
    waiting_for_points = State()
    waiting_for_description = State()

class NSPBot:
    """Основной класс бота"""
    
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        self.router = Router()
        
        # Регистрация handlers
        self._register_handlers()
        self.dp.include_router(self.router)
    
    def _register_handlers(self):
        """Регистрация обработчиков"""
        self.router.message(Command("start"))(self.start_command)
        self.router.message(Command("help"))(self.help_command)
    
    async def start_command(self, message: types.Message):
        """Обработчик команды /start"""
        welcome_text = """
🚗 **Добро пожаловать в NSP QR Generator Bot!**

Этот бот поможет вам:
• 📱 Генерировать QR-коды для автозапчастей
• 🔍 Сканировать QR-коды и получать информацию
• 📊 Отслеживать статистику сканирований

**Доступные команды:**
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
• `/help` - Эта справка

**Формат QR-кода:**
`NSP:PRODUCT_ID:CATEGORY:POINTS`

Пример: `NSP:BRAKE_PADS_001:BRAKES:50`
        """
        
        await message.answer(help_text, parse_mode="Markdown")
    
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
                handle_signals=False
            )
            
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
            raise
        finally:
            await self.bot.session.close()

async def main():
    """Главная функция"""
    try:
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
    asyncio.run(main())