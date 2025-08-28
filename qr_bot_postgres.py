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

class Database:
    """Класс для работы с PostgreSQL базой данных"""
    
    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL, echo=True)
        self.AsyncSessionLocal = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
    
    async def init_db(self):
        """Инициализация базы данных"""
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                logger.info("База данных инициализирована успешно")
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise
    
    async def add_qr_code(self, qr_data: Dict[str, Any]) -> bool:
        """Добавление QR-кода в базу данных"""
        try:
            async with self.AsyncSessionLocal() as db:
                new_qr = QRCode(
                    qr_id=qr_data['qr_id'],
                    product_name=qr_data['product_name'],
                    category=qr_data['category'],
                    points=qr_data['points'],
                    description=qr_data['description'],
                    created_by=await self.get_or_create_user(db, qr_data['created_by'])
                )
                db.add(new_qr)
                await db.commit()
                logger.info(f"QR-код {qr_data['qr_id']} добавлен в базу данных")
                return True
        except Exception as e:
            logger.error(f"Ошибка добавления QR-кода: {e}")
            return False
    
    async def get_or_create_user(self, db: AsyncSession, telegram_id: int) -> uuid.UUID:
        """Получение или создание пользователя"""
        user = await db.execute(
            select(AppUser).where(AppUser.telegram_id == telegram_id)
        )
        user = user.scalar_one_or_none()
        
        if not user:
            user = AppUser(
                user_id=str(uuid.uuid4()),
                name=f"Telegram User {telegram_id}",
                email=f"telegram_{telegram_id}@nsp.local",
                password_hash="telegram_user",
                telegram_id=telegram_id
            )
            db.add(user)
            await db.flush()
        
        return user.id
    
    async def get_qr_info(self, qr_id: str) -> Optional[Dict[str, Any]]:
        """Получение информации о QR-коде"""
        try:
            async with self.AsyncSessionLocal() as db:
                qr_code = await db.execute(
                    select(QRCode).where(QRCode.qr_id == qr_id)
                )
                qr_code = qr_code.scalar_one_or_none()
                
                if qr_code:
                    return {
                        'id': qr_code.id,
                        'qr_id': qr_code.qr_id,
                        'product_name': qr_code.product_name,
                        'category': qr_code.category,
                        'points': qr_code.points,
                        'description': qr_code.description,
                        'created_at': qr_code.created_at,
                        'scanned_count': qr_code.scanned_count,
                        'is_used': qr_code.is_used
                    }
                return None
        except Exception as e:
            logger.error(f"Ошибка получения QR-кода: {e}")
            return None
    
    async def get_admin_stats(self) -> Dict[str, Any]:
        """Получение административной статистики"""
        try:
            async with self.AsyncSessionLocal() as db:
                # Общая статистика
                total_qrs = await db.execute(select(func.count(QRCode.id)))
                total_qrs = total_qrs.scalar() or 0
                
                total_scans = await db.execute(select(func.count(AppQRScan.id)))
                total_scans = total_scans.scalar() or 0
                
                unique_users = await db.execute(select(func.count(func.distinct(AppQRScan.user_id))))
                unique_users = unique_users.scalar() or 0
                
                # Топ QR-коды
                top_qrs = await db.execute(
                    select(QRCode)
                    .order_by(QRCode.scanned_count.desc())
                    .limit(5)
                )
                top_qrs = top_qrs.scalars().all()
                
                return {
                    'total_qrs': total_qrs,
                    'total_scans': total_scans,
                    'unique_users': unique_users,
                    'top_qrs': [
                        {
                            'product_name': qr.product_name,
                            'scanned_count': qr.scanned_count,
                            'points': qr.points
                        }
                        for qr in top_qrs
                    ]
                }
        except Exception as e:
            logger.error(f"Ошибка получения админ статистики: {e}")
            return {}

class QRGenerator:
    """Класс для генерации QR-кодов"""
    
    @staticmethod
    def generate_qr_code(data: str, size: int = 10) -> BytesIO:
        """Генерация QR-кода"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=size,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Сохранение в BytesIO
            bio = BytesIO()
            img.save(bio, 'PNG')
            bio.seek(0)
            return bio
        except Exception as e:
            logger.error(f"Ошибка генерации QR-кода: {e}")
            raise

class NSPBot:
    """Основной класс бота"""
    
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        self.router = Router()
        self.db = Database()
        self.qr_generator = QRGenerator()
        
        # Регистрация handlers
        self._register_handlers()
        self.dp.include_router(self.router)
    
    def _register_handlers(self):
        """Регистрация обработчиков"""
        # Команды
        self.router.message(Command("start"))(self.start_command)
        self.router.message(Command("help"))(self.help_command)
        self.router.message(Command("admin"))(self.admin_command)
        self.router.message(Command("generate"))(self.generate_command)
        
        # Состояния для генерации QR
        self.router.message(StateFilter(QRStates.waiting_for_product_name))(self.process_product_name)
        self.router.message(StateFilter(QRStates.waiting_for_category))(self.process_category)
        self.router.message(StateFilter(QRStates.waiting_for_points))(self.process_points)
        self.router.message(StateFilter(QRStates.waiting_for_description))(self.process_description)
        
        # Callback queries
        self.router.callback_query()(self.handle_callback)
        
        # Обработка QR-кодов (текстовые сообщения)
        self.router.message()(self.handle_qr_scan)
    
    async def start_command(self, message: types.Message):
        """Обработчик команды /start"""
        welcome_text = """
🚗 **Добро пожаловать в NSP QR Generator Bot!**

Этот бот поможет вам:
• 📱 Генерировать QR-коды для автозапчастей
• 🔍 Сканировать QR-коды и получать информацию
• 📊 Отслеживать статистику сканирований

**Доступные команды:**
/generate - Создать новый QR-код (только для админов)
/admin - Административная панель
/help - Справка

Отправьте текст QR-кода для получения информации о продукте!
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")]
        ])
        
        await message.answer(welcome_text, reply_markup=keyboard, parse_mode="Markdown")
    
    async def help_command(self, message: types.Message):
        """Обработчик команды /help"""
        help_text = """
📖 **Справка по использованию бота**

**Для всех пользователей:**
• Отправьте текст QR-кода для получения информации о товаре
• `/help` - Эта справка

**Для администраторов:**
• `/generate` - Создать новый QR-код
• `/admin` - Административная панель с подробной статистикой

**Формат QR-кода:**
`NSP:PRODUCT_ID:CATEGORY:POINTS`

Пример: `NSP:BRAKE_PADS_001:BRAKES:50`
        """
        
        await message.answer(help_text, parse_mode="Markdown")
    
    async def admin_command(self, message: types.Message):
        """Обработчик команды /admin"""
        if message.from_user.id not in AUTHORIZED_USERS:
            await message.answer("❌ У вас нет прав администратора")
            return
        
        admin_stats = await self.db.get_admin_stats()
        
        admin_text = f"""
👑 **Административная панель**

📈 **Общая статистика:**
• QR-кодов создано: **{admin_stats.get('total_qrs', 0)}**
• Всего сканирований: **{admin_stats.get('total_scans', 0)}**
• Уникальных пользователей: **{admin_stats.get('unique_users', 0)}**

"""
        
        if admin_stats.get('top_qrs'):
            admin_text += "🏆 **Топ QR-коды:**\n"
            for qr in admin_stats['top_qrs'][:3]:
                admin_text += f"• {qr['product_name']} - {qr['scanned_count']} сканирований ({qr['points']} баллов)\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Создать QR", callback_data="create_qr"),
                InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_admin")
            ]
        ])
        
        await message.answer(admin_text, reply_markup=keyboard, parse_mode="Markdown")
    
    async def generate_command(self, message: types.Message, state: FSMContext):
        """Начало процесса генерации QR-кода"""
        if message.from_user.id not in AUTHORIZED_USERS:
            await message.answer("❌ У вас нет прав для создания QR-кодов")
            return
        
        await message.answer(
            "🏷️ **Создание нового QR-кода**\n\n"
            "Введите название продукта/запчасти:",
            parse_mode="Markdown"
        )
        await state.set_state(QRStates.waiting_for_product_name)
    
    async def process_product_name(self, message: types.Message, state: FSMContext):
        """Обработка названия продукта"""
        await state.update_data(product_name=message.text)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔧 Двигатель", callback_data="cat_engine"),
                InlineKeyboardButton(text="🛞 Тормоза", callback_data="cat_brakes")
            ],
            [
                InlineKeyboardButton(text="⚡ Электрика", callback_data="cat_electrical"),
                InlineKeyboardButton(text="🔩 Подвеска", callback_data="cat_suspension")
            ],
            [
                InlineKeyboardButton(text="🛢️ Масла", callback_data="cat_oils"),
                InlineKeyboardButton(text="🧰 Прочее", callback_data="cat_other")
            ]
        ])
        
        await message.answer(
            "📂 Выберите категорию продукта:",
            reply_markup=keyboard
        )
        await state.set_state(QRStates.waiting_for_category)
    
    async def process_category(self, message: types.Message, state: FSMContext):
        """Обработка категории (если введена текстом)"""
        await state.update_data(category=message.text)
        await message.answer("💎 Введите количество баллов за сканирование (число от 1 до 1000):")
        await state.set_state(QRStates.waiting_for_points)
    
    async def process_points(self, message: types.Message, state: FSMContext):
        """Обработка количества баллов"""
        try:
            points = int(message.text)
            if not 1 <= points <= 1000:
                await message.answer("❌ Количество баллов должно быть от 1 до 1000")
                return
            
            await state.update_data(points=points)
            await message.answer("📝 Введите описание продукта (или отправьте 'пропустить'):")
            await state.set_state(QRStates.waiting_for_description)
            
        except ValueError:
            await message.answer("❌ Пожалуйста, введите корректное число")
    
    async def process_description(self, message: types.Message, state: FSMContext):
        """Обработка описания и создание QR-кода"""
        description = message.text if message.text.lower() != 'пропустить' else ""
        
        data = await state.get_data()
        data['description'] = description
        data['created_by'] = message.from_user.id
        
        # Генерация уникального ID
        qr_id = f"NSP_{uuid.uuid4().hex[:8].upper()}"
        data['qr_id'] = qr_id
        
        # Сохранение в базу данных
        if await self.db.add_qr_code(data):
            # Формирование данных для QR-кода
            qr_data = f"NSP:{qr_id}:{data['category']}:{data['points']}"
            
            # Генерация QR-кода
            qr_image = self.qr_generator.generate_qr_code(qr_data)
            
            # Информация о созданном QR-коде
            info_text = f"""
✅ **QR-код успешно создан!**

🆔 ID: `{qr_id}`
🏷️ Продукт: **{data['product_name']}**
📂 Категория: **{data['category']}**
💎 Баллы: **{data['points']}**
📝 Описание: {description or "Не указано"}

📱 **Данные QR-кода:** `{qr_data}`
            """
            
            # Отправка QR-кода
            qr_file = BufferedInputFile(qr_image.read(), filename=f"qr_{qr_id}.png")
            await message.answer_photo(
                photo=qr_file,
                caption=info_text,
                parse_mode="Markdown"
            )
            
            logger.info(f"QR-код {qr_id} создан пользователем {message.from_user.id}")
        else:
            await message.answer("❌ Ошибка при создании QR-кода. Попробуйте еще раз.")
        
        await state.clear()
    
    async def handle_callback(self, callback: types.CallbackQuery, state: FSMContext):
        """Обработчик callback запросов"""
        data = callback.data
        
        try:
            if data == "help":
                await self.help_command(callback.message)
            
            elif data == "refresh_admin":
                await self.admin_command(callback.message)
            
            elif data == "create_qr":
                if callback.from_user.id in AUTHORIZED_USERS:
                    await self.generate_command(callback.message, state)
                else:
                    await callback.answer("❌ Нет прав доступа", show_alert=True)
            
            elif data.startswith("cat_"):
                # Обработка выбора категории
                categories = {
                    "cat_engine": "Двигатель",
                    "cat_brakes": "Тормозная система",
                    "cat_electrical": "Электрика",
                    "cat_suspension": "Подвеска",
                    "cat_oils": "Масла и жидкости",
                    "cat_other": "Прочее"
                }
                
                category = categories.get(data, "Прочее")
                await state.update_data(category=category)
                
                await callback.message.edit_text(
                    f"✅ Выбрана категория: **{category}**\n\n"
                    "💎 Введите количество баллов за сканирование (число от 1 до 1000):",
                    parse_mode="Markdown"
                )
                await state.set_state(QRStates.waiting_for_points)
            
            await callback.answer()
            
        except Exception as e:
            logger.warning(f"Callback error: {e}")
            await callback.answer()
    
    async def handle_qr_scan(self, message: types.Message):
        """Обработчик сканирования QR-кодов"""
        text = message.text
        
        # Проверка формата NSP QR-кода
        if not text.startswith("NSP:"):
            await message.answer(
                "❓ Это не похоже на QR-код NSP.\n\n"
                "Формат должен быть: `NSP:ID:CATEGORY:POINTS`\n"
                "Используйте /help для получения справки.",
                parse_mode="Markdown"
            )
            return
        
        try:
            # Парсинг QR-кода
            parts = text.split(":")
            if len(parts) < 4:
                await message.answer("❌ Неверный формат QR-кода")
                return
            
            qr_id = parts[1]
            
            # Поиск в базе данных
            qr_info = await self.db.get_qr_info(qr_id)
            
            if not qr_info:
                await message.answer(
                    f"❌ QR-код `{qr_id}` не найден в базе данных.\n"
                    "Возможно, он был удален или создан некорректно.",
                    parse_mode="Markdown"
                )
                return
            
            if qr_info['is_used']:
                await message.answer("❌ Этот QR-код уже был использован")
                return
            
            # Формирование ответа
            scan_text = f"""
✅ **QR-код найден!**

🏷️ **Продукт:** {qr_info['product_name']}
📂 **Категория:** {qr_info['category']}
💎 **Баллы:** {qr_info['points']}
📝 **Описание:** {qr_info['description'] or "Не указано"}

📊 **Статистика QR-кода:**
• Всего сканирований: {qr_info['scanned_count']}
• Создан: {qr_info['created_at'].strftime("%d.%m.%Y") if qr_info['created_at'] else "Неизвестно"}

ℹ️ Для получения баллов используйте мобильное приложение NSP
            """
            
            await message.answer(scan_text, parse_mode="Markdown")
            
            logger.info(f"QR-код {qr_id} просмотрен пользователем {message.from_user.id}")
            
        except Exception as e:
            logger.error(f"Ошибка обработки QR-кода: {e}")
            await message.answer(
                "❌ Произошла ошибка при обработке QR-кода.\n"
                "Попробуйте еще раз или обратитесь к администратору."
            )
    
    async def start_bot(self):
        """Запуск бота"""
        try:
            logger.info("Запуск NSP QR Generator Bot...")
            
            # Инициализация базы данных
            await self.db.init_db()
            
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
    asyncio.run(main())