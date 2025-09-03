#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API сервер для интеграции мобильного приложения с базой данных QR-кодов
"""

import asyncio
import logging
import json
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import os
from pathlib import Path

from aiohttp import web, web_request, MultipartReader
from aiohttp.web_response import Response
from aiohttp_cors import setup as cors_setup, ResourceOptions

from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import selectinload

from config import DATABASE_URL, API_KEYS, API_HOST, API_PORT
from models import (
    Base, AppUser, QRCode, Product, NewsArticle, Car, Lottery, Order, 
    PointTransaction, AppQRScan, SupportTicket, SupportMessage, UserSession
)

# Конфигурация
UPLOADS_DIR = "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Создаем директорию для загрузок
Path(UPLOADS_DIR).mkdir(exist_ok=True)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api_server.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Создание движка и сессии
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_database():
    """Инициализация базы данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("База данных инициализирована")

def check_api_key(func):
    """Декоратор для проверки API ключа"""
    async def wrapper(request: web_request.Request):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key not in API_KEYS.values():
            return web.json_response(
                {"error": "Invalid or missing API key"},
                status=401
            )
        return await func(request)
    return wrapper

async def health_check(request: web_request.Request) -> Response:
    """Проверка состояния API"""
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(select(1))
        
        return web.json_response({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "database": "connected"
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return web.json_response({
            "status": "unhealthy",
            "error": str(e)
        }, status=503)

def init_app():
    """Инициализация веб-приложения"""
    app = web.Application(client_max_size=MAX_FILE_SIZE)
    
    # Настройка CORS
    cors = cors_setup(app, defaults={
        "*": ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        )
    })
    
    # Маршруты API
    app.router.add_get('/health', health_check)
    
    # Добавление CORS ко всем маршрутам
    for route in list(app.router.routes()):
        cors.add(route)
    
    return app

async def main():
    """Главная функция"""
    try:
        # Инициализация базы данных
        await init_database()
        
        # Создание приложения
        app = init_app()
        
        # Запуск сервера
        logger.info(f"Запуск API сервера на {API_HOST}:{API_PORT}")
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, API_HOST, API_PORT)
        await site.start()
        
        try:
            await asyncio.Future()  # Бесконечное ожидание
        except KeyboardInterrupt:
            logger.info("Остановка сервера...")
        finally:
            await runner.cleanup()
        
    except Exception as e:
        logger.error(f"Ошибка запуска API сервера: {e}")

if __name__ == "__main__":
    asyncio.run(main())