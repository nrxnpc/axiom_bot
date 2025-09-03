#!/usr/bin/env python3
"""
Скрипт для создания таблиц в PostgreSQL
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from config import DATABASE_URL
from models import Base

async def create_tables():
    """Создание всех таблиц"""
    # Используем URL с правами суперпользователя
    admin_url = "postgresql+asyncpg://postgres:postgres@localhost/nsp_qr_db"
    
    try:
        engine = create_async_engine(admin_url, echo=True)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Таблицы созданы успешно")
        await engine.dispose()
    except Exception as e:
        print(f"❌ Ошибка создания таблиц: {e}")
        # Попробуем с обычным пользователем
        try:
            engine = create_async_engine(DATABASE_URL, echo=True)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("✅ Таблицы созданы с пользователем nsp_user")
            await engine.dispose()
        except Exception as e2:
            print(f"❌ Ошибка с nsp_user: {e2}")

if __name__ == "__main__":
    asyncio.run(create_tables())