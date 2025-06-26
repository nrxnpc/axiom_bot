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
BOT_TOKEN = "7712440966:AAH3DnVoTl72XmOHryYbDzLx_1185H7U9BU"
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
    
    def add_qr_code(self, qr_data: Dict[str, Any]) -> bool:
        """Добавление QR-кода в базу данных"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO qr_codes (qr_id, product_name, category, points, description, created_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    qr_data['qr_id'],
                    qr_data['product_name'],
                    qr_data['category'],
                    qr_data['points'],
                    qr_data['description'],
                    qr_data['created_by']
                ))
                conn.commit()
                logger.info(f"QR-код {qr_data['qr_id']} добавлен в базу данных")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"QR-код {qr_data['qr_id']} уже существует")
            return False
        except sqlite3.Error as e:
            logger.error(f"Ошибка добавления QR-кода: {e}")
            return False
    
    def get_qr_info(self, qr_id: str) -> Optional[Dict[str, Any]]:
        """Получение информации о QR-коде"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute('''
                    SELECT * FROM qr_codes WHERE qr_id = ?
                ''', (qr_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения QR-кода: {e}")
            return None
    
    def update_scan_count(self, qr_id: str):
        """Обновление счетчика сканирований"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    UPDATE qr_codes 
                    SET scanned_count = scanned_count + 1, 
                        last_scanned = CURRENT_TIMESTAMP 
                    WHERE qr_id = ?
                ''', (qr_id,))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Ошибка обновления счетчика: {e}")
    
    def add_scan_record(self, qr_id: str, user_id: int, points: int):
        """Добавление записи о сканировании"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO scan_history (qr_id, user_id, points_earned)
                    VALUES (?, ?, ?)
                ''', (qr_id, user_id, points))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Ошибка добавления записи сканирования: {e}")
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Получение статистики пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Статистика сканирований
                cursor = conn.execute('''
                    SELECT COUNT(*) as scan_count, COALESCE(SUM(points_earned), 0) as total_points
                    FROM scan_history WHERE user_id = ?
                ''', (user_id,))
                scan_stats = cursor.fetchone()
                
                # Последние сканирования
                cursor = conn.execute('''
                    SELECT sh.scanned_at, qr.product_name, sh.points_earned
                    FROM scan_history sh
                    JOIN qr_codes qr ON sh.qr_id = qr.qr_id
                    WHERE sh.user_id = ?
                    ORDER BY sh.scanned_at DESC
                    LIMIT 5
                ''', (user_id,))
                recent_scans = cursor.fetchall()
                
                return {
                    'scan_count': scan_stats['scan_count'],
                    'total_points': scan_stats['total_points'],
                    'recent_scans': [dict(row) for row in recent_scans]
                }
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {'scan_count': 0, 'total_points': 0, 'recent_scans': []}
    
    def get_admin_stats(self) -> Dict[str, Any]:
        """Получение административной статистики"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Общая статистика
                cursor = conn.execute('SELECT COUNT(*) as total_qrs FROM qr_codes')
                total_qrs = cursor.fetchone()['total_qrs']
                
                cursor = conn.execute('SELECT COUNT(*) as total_scans FROM scan_history')
                total_scans = cursor.fetchone()['total_scans']
                
                cursor = conn.execute('SELECT COUNT(DISTINCT user_id) as unique_users FROM scan_history')
                unique_users = cursor.fetchone()['unique_users']
                
                # Топ QR-коды
                cursor = conn.execute('''
                    SELECT product_name, scanned_count, points
                    FROM qr_codes
                    ORDER BY scanned_count DESC
                    LIMIT 5
                ''')
                top_qrs = cursor.fetchall()
                
                # Активность за последние дни
                cursor = conn.execute('''
                    SELECT DATE(scanned_at) as date, COUNT(*) as scans
                    FROM scan_history
                    WHERE scanned_at >= datetime('now', '-7 days')
                    GROUP BY DATE(scanned_at)
                    ORDER BY date DESC
                ''')
                daily_activity = cursor.fetchall()
                
                return {
                    'total_qrs': total_qrs,
                    'total_scans': total_scans,
                    'unique_users': unique_users,
                    'top_qrs': [dict(row) for row in top_qrs],
                    'daily_activity': [dict(row) for row in daily_activity]
                }
        except sqlite3.Error as e:
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
        self.router.message(Command("stats"))(self.stats_command)
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
/stats - Посмотреть вашу статистику
/admin - Административная панель
/help - Справка

Отправьте текст QR-кода для получения информации о продукте!
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats"),
                InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")
            ]
        ])
        
        await message.answer(welcome_text, reply_markup=keyboard, parse_mode="Markdown")
    
    async def help_command(self, message: types.Message):
        """Обработчик команды /help"""
        help_text = """
📖 **Справка по использованию бота**

**Для всех пользователей:**
• Отправьте текст QR-кода для получения информации о товаре
• `/stats` - Ваша статистика сканирований
• `/help` - Эта справка

**Для администраторов:**
• `/generate` - Создать новый QR-код
• `/admin` - Административная панель с подробной статистикой

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
        user_stats = self.db.get_user_stats(message.from_user.id)
        
        stats_text = f"""
📊 **Ваша статистика**

🔍 Всего сканирований: **{user_stats['scan_count']}**
💎 Всего баллов: **{user_stats['total_points']}**

"""
        
        if user_stats['recent_scans']:
            stats_text += "🕒 **Последние сканирования:**\n"
            for scan in user_stats['recent_scans']:
                date = datetime.fromisoformat(scan['scanned_at']).strftime("%d.%m.%Y %H:%M")
                stats_text += f"• {scan['product_name']} (+{scan['points_earned']} баллов) - {date}\n"
        else:
            stats_text += "📱 Отсканируйте ваш первый QR-код!"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_stats")]
        ])
        
        await message.answer(stats_text, reply_markup=keyboard, parse_mode="Markdown")
    
    async def admin_command(self, message: types.Message):
        """Обработчик команды /admin"""
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("❌ У вас нет прав администратора")
            return
        
        admin_stats = self.db.get_admin_stats()
        
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
        
        if admin_stats.get('daily_activity'):
            admin_text += "\n📅 **Активность за последние дни:**\n"
            for day in admin_stats['daily_activity'][:5]:
                admin_text += f"• {day['date']}: {day['scans']} сканирований\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Создать QR", callback_data="create_qr"),
                InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_admin")
            ]
        ])
        
        await message.answer(admin_text, reply_markup=keyboard, parse_mode="Markdown")
    
    async def generate_command(self, message: types.Message, state: FSMContext):
        """Начало процесса генерации QR-кода"""
        if message.from_user.id not in ADMIN_IDS:
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
        import uuid
        qr_id = f"NSP_{uuid.uuid4().hex[:8].upper()}"
        data['qr_id'] = qr_id
        
        # Сохранение в базу данных
        if self.db.add_qr_code(data):
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
            if data == "my_stats":
                user_stats = self.db.get_user_stats(callback.from_user.id)
                stats_text = f"""
📊 **Ваша статистика**

🔍 Всего сканирований: **{user_stats['scan_count']}**
💎 Всего баллов: **{user_stats['total_points']}**
                """
                
                if user_stats['recent_scans']:
                    stats_text += "\n🕒 **Последние сканирования:**\n"
                    for scan in user_stats['recent_scans'][:3]:
                        date = datetime.fromisoformat(scan['scanned_at']).strftime("%d.%m")
                        stats_text += f"• {scan['product_name']} (+{scan['points_earned']}) - {date}\n"
                
                await callback.message.edit_text(stats_text, parse_mode="Markdown")
            
            elif data == "help":
                await self.help_command(callback.message)
            
            elif data == "refresh_stats":
                await self.stats_command(callback.message)
            
            elif data == "refresh_admin":
                await self.admin_command(callback.message)
            
            elif data == "create_qr":
                if callback.from_user.id in ADMIN_IDS:
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
            
        except TelegramBadRequest as e:
            logger.warning(f"Telegram error in callback: {e}")
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
            qr_info = self.db.get_qr_info(qr_id)
            
            if not qr_info:
                await message.answer(
                    f"❌ QR-код `{qr_id}` не найден в базе данных.\n"
                    "Возможно, он был удален или создан некорректно.",
                    parse_mode="Markdown"
                )
                return
            
            # Обновление статистики
            self.db.update_scan_count(qr_id)
            self.db.add_scan_record(qr_id, message.from_user.id, qr_info['points'])
            
            # Формирование ответа
            scan_text = f"""
✅ **QR-код успешно отсканирован!**

🏷️ **Продукт:** {qr_info['product_name']}
📂 **Категория:** {qr_info['category']}
💎 **Баллы:** +{qr_info['points']}
📝 **Описание:** {qr_info['description'] or "Не указано"}

📊 **Статистика QR-кода:**
• Всего сканирований: {qr_info['scanned_count'] + 1}
• Создан: {datetime.fromisoformat(qr_info['created_at']).strftime("%d.%m.%Y")}

🎉 **Поздравляем! Вы получили {qr_info['points']} баллов!**
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats")]
            ])
            
            await message.answer(scan_text, reply_markup=keyboard, parse_mode="Markdown")
            
            logger.info(f"QR-код {qr_id} отсканирован пользователем {message.from_user.id}")
            
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
