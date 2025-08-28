#!/usr/bin/env python3
"""
Скрипт миграции данных из SQLite в PostgreSQL
"""

import sqlite3
import asyncio
import uuid
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from config import DATABASE_URL
from models import Base, QRCode, AppUser, AppQRScan, PointTransaction

async def migrate_data():
    """Миграция данных из SQLite в PostgreSQL"""
    
    # Подключение к PostgreSQL
    engine = create_async_engine(DATABASE_URL, echo=True)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Создание таблиц
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("Таблицы PostgreSQL созданы")
    
    # Подключение к SQLite
    sqlite_conn = sqlite3.connect("nsp_qr_bot.db")
    sqlite_conn.row_factory = sqlite3.Row
    
    async with AsyncSessionLocal() as db:
        try:
            # Миграция QR-кодов
            print("Миграция QR-кодов...")
            cursor = sqlite_conn.execute("SELECT * FROM qr_codes")
            qr_codes = cursor.fetchall()
            
            user_mapping = {}  # Маппинг telegram_id -> user_id
            
            for row in qr_codes:
                # Создаем пользователя если не существует
                telegram_id = row['created_by']
                if telegram_id not in user_mapping:
                    user = AppUser(
                        user_id=str(uuid.uuid4()),
                        name=f"Telegram User {telegram_id}",
                        email=f"telegram_{telegram_id}@nsp.local",
                        password_hash="migrated_user",
                        telegram_id=telegram_id,
                        role="admin" if telegram_id in [97915547] else "user"
                    )
                    db.add(user)
                    await db.flush()
                    user_mapping[telegram_id] = user.id
                
                # Создаем QR-код
                qr_code = QRCode(
                    qr_id=row['qr_id'],
                    product_name=row['product_name'],
                    category=row['category'],
                    points=row['points'],
                    description=row['description'],
                    created_by=user_mapping[telegram_id],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    scanned_count=row['scanned_count'] or 0,
                    last_scanned=datetime.fromisoformat(row['last_scanned']) if row['last_scanned'] else None
                )
                db.add(qr_code)
            
            await db.commit()
            print(f"Мигрировано {len(qr_codes)} QR-кодов")
            
            # Миграция истории сканирований
            print("Миграция истории сканирований...")
            cursor = sqlite_conn.execute("SELECT * FROM scan_history")
            scan_history = cursor.fetchall()
            
            for row in scan_history:
                telegram_id = row['user_id']
                if telegram_id and telegram_id not in user_mapping:
                    user = AppUser(
                        user_id=str(uuid.uuid4()),
                        name=f"Telegram User {telegram_id}",
                        email=f"telegram_{telegram_id}@nsp.local",
                        password_hash="migrated_user",
                        telegram_id=telegram_id
                    )
                    db.add(user)
                    await db.flush()
                    user_mapping[telegram_id] = user.id
                
                # Находим QR-код
                qr_code = await db.execute(
                    select(QRCode).where(QRCode.qr_id == row['qr_id'])
                )
                qr_code = qr_code.scalar_one_or_none()
                
                if qr_code and telegram_id:
                    # Создаем запись сканирования
                    scan = AppQRScan(
                        qr_id=qr_code.id,
                        user_id=user_mapping[telegram_id],
                        points_earned=row['points_earned'] or 0,
                        product_name=qr_code.product_name,
                        product_category=qr_code.category,
                        timestamp=datetime.fromisoformat(row['scanned_at']) if row['scanned_at'] else datetime.now()
                    )
                    db.add(scan)
                    
                    # Создаем транзакцию баллов
                    transaction = PointTransaction(
                        user_id=user_mapping[telegram_id],
                        type='earned',
                        amount=row['points_earned'] or 0,
                        description=f'Сканирование QR-кода: {qr_code.product_name}',
                        timestamp=datetime.fromisoformat(row['scanned_at']) if row['scanned_at'] else datetime.now(),
                        qr_scan_id=scan.id
                    )
                    db.add(transaction)
            
            # Обновляем баллы пользователей
            for telegram_id, user_id in user_mapping.items():
                total_points = await db.execute(
                    select(func.sum(PointTransaction.amount))
                    .where(PointTransaction.user_id == user_id, PointTransaction.type == 'earned')
                )
                total_points = total_points.scalar() or 0
                
                user = await db.get(AppUser, user_id)
                user.points = total_points
            
            await db.commit()
            print(f"Мигрировано {len(scan_history)} записей сканирований")
            
            print("Миграция завершена успешно!")
            
        except Exception as e:
            print(f"Ошибка миграции: {e}")
            await db.rollback()
            raise
        finally:
            sqlite_conn.close()

if __name__ == "__main__":
    asyncio.run(migrate_data())