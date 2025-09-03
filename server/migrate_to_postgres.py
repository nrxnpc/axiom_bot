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
    
    print("Миграция завершена успешно!")

if __name__ == "__main__":
    asyncio.run(migrate_data())