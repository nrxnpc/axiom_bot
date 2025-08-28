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

def require_auth(func):
    """Декоратор для проверки авторизации пользователя"""
    async def wrapper(request: web_request.Request):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return web.json_response(
                {"error": "Missing or invalid authorization header"},
                status=401
            )
        
        token = auth_header.split(' ')[1]
        user = await get_user_by_token(token)
        if not user:
            return web.json_response(
                {"error": "Invalid or expired token"},
                status=401
            )
        
        request['user'] = user
        return await func(request)
    return wrapper

async def get_user_by_token(token: str) -> Optional[AppUser]:
    """Получение пользователя по токену"""
    async with AsyncSessionLocal() as db:
        stmt = (
            select(AppUser)
            .join(UserSession)
            .where(
                UserSession.token == token,
                UserSession.is_active == True,
                UserSession.expires_at > func.now()
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token() -> str:
    """Генерация токена сессии"""
    return secrets.token_urlsafe(32)

def json_response(data: dict, status: int = 200) -> Response:
    """Создание JSON ответа"""
    return web.json_response(data, status=status)

# API Endpoints

async def health_check(request: web_request.Request) -> Response:
    """Проверка состояния API"""
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(select(1))
        
        return json_response({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "database": "connected"
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return json_response({
            "status": "unhealthy",
            "error": str(e)
        }, status=503)

# Регистрация и авторизация

@check_api_key
async def register_user(request: web_request.Request) -> Response:
    """Регистрация нового пользователя"""
    try:
        data = await request.json()
        
        required_fields = ['name', 'email', 'phone', 'password', 'userType']
        if not all(field in data for field in required_fields):
            return json_response({
                "error": "Missing required fields"
            }, status=400)
        
        async with AsyncSessionLocal() as db:
            # Проверка существования пользователя
            existing_user = await db.execute(
                select(AppUser).where(AppUser.email == data['email'])
            )
            if existing_user.scalar_one_or_none():
                return json_response({
                    "error": "User with this email already exists"
                }, status=400)
            
            # Создание нового пользователя
            user_id = str(uuid.uuid4())
            password_hash = hash_password(data['password'])
            
            new_user = AppUser(
                user_id=user_id,
                name=data['name'],
                email=data['email'],
                phone=data['phone'],
                password_hash=password_hash,
                user_type=data['userType'],
                points=100
            )
            db.add(new_user)
            await db.flush()
            
            # Создание сессии
            token = generate_token()
            expires_at = datetime.now() + timedelta(days=30)
            
            session = UserSession(
                user_id=new_user.id,
                token=token,
                expires_at=expires_at,
                device_info=data.get('deviceInfo', '')
            )
            db.add(session)
            
            # Запись транзакции начисления
            transaction = PointTransaction(
                user_id=new_user.id,
                type='bonus',
                amount=100,
                description='Бонус за регистрацию'
            )
            db.add(transaction)
            
            await db.commit()
            
            return json_response({
                "success": True,
                "user": {
                    "id": user_id,
                    "name": data['name'],
                    "email": data['email'],
                    "phone": data['phone'],
                    "userType": data['userType'],
                    "points": 100,
                    "role": "user",
                    "registrationDate": datetime.now().isoformat(),
                    "isActive": True
                },
                "token": token
            })
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return json_response({
            "error": "Registration failed"
        }, status=500)

@check_api_key
async def login_user(request: web_request.Request) -> Response:
    """Авторизация пользователя"""
    try:
        data = await request.json()
        
        if not data.get('email') or not data.get('password'):
            return json_response({
                "error": "Email and password required"
            }, status=400)
        
        async with AsyncSessionLocal() as db:
            password_hash = hash_password(data['password'])
            
            user = await db.execute(
                select(AppUser).where(
                    AppUser.email == data['email'],
                    AppUser.password_hash == password_hash,
                    AppUser.is_active == True
                )
            )
            user = user.scalar_one_or_none()
            
            if not user:
                return json_response({
                    "error": "Invalid credentials"
                }, status=401)
            
            # Создание новой сессии
            token = generate_token()
            expires_at = datetime.now() + timedelta(days=30)
            
            session = UserSession(
                user_id=user.id,
                token=token,
                expires_at=expires_at,
                device_info=data.get('deviceInfo', '')
            )
            db.add(session)
            
            # Обновление времени последнего входа
            user.last_login = func.now()
            
            await db.commit()
            
            return json_response({
                "success": True,
                "user": {
                    "id": user.user_id,
                    "name": user.name,
                    "email": user.email,
                    "phone": user.phone,
                    "userType": user.user_type,
                    "points": user.points,
                    "role": user.role,
                    "registrationDate": user.registration_date.isoformat() if user.registration_date else None,
                    "isActive": user.is_active
                },
                "token": token
            })
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return json_response({
            "error": "Login failed"
        }, status=500)

# QR-коды

@check_api_key
@require_auth
async def scan_qr_code(request: web_request.Request) -> Response:
    """Сканирование QR-кода с одноразовым использованием"""
    try:
        data = await request.json()
        qr_code = data.get('qr_code')
        user = request['user']
        location = data.get('location', 'Unknown')
        
        if not qr_code:
            return json_response({
                "error": "Missing qr_code field"
            }, status=400)
        
        # Парсинг QR-кода
        if not qr_code.startswith("NSP:"):
            return json_response({
                "error": "Invalid QR code format"
            }, status=400)
        
        parts = qr_code.split(":")
        if len(parts) < 4:
            return json_response({
                "error": "Invalid QR code format"
            }, status=400)
        
        qr_id = parts[1]
        
        async with AsyncSessionLocal() as db:
            # Поиск QR-кода в базе данных
            qr_info = await db.execute(
                select(QRCode).where(QRCode.qr_id == qr_id)
            )
            qr_info = qr_info.scalar_one_or_none()
            
            if not qr_info:
                return json_response({
                    "error": "QR code not found",
                    "valid": False
                }, status=404)
            
            # Проверка на использование
            if qr_info.is_used:
                return json_response({
                    "error": "QR code already used",
                    "valid": False,
                    "product_name": qr_info.product_name,
                    "used_at": qr_info.used_at.isoformat() if qr_info.used_at else None
                }, status=409)
            
            # Отметка QR-кода как использованного
            qr_info.is_used = True
            qr_info.used_by = user.id
            qr_info.used_at = func.now()
            qr_info.scanned_count += 1
            qr_info.last_scanned = func.now()
            
            # Запись сканирования
            scan = AppQRScan(
                qr_id=qr_info.id,
                user_id=user.id,
                points_earned=qr_info.points,
                product_name=qr_info.product_name,
                product_category=qr_info.category,
                location=location
            )
            db.add(scan)
            await db.flush()
            
            # Запись транзакции баллов
            transaction = PointTransaction(
                user_id=user.id,
                type='earned',
                amount=qr_info.points,
                description=f"Сканирование QR-кода ({qr_info.product_name})",
                qr_scan_id=scan.id
            )
            db.add(transaction)
            
            await db.commit()
            
            logger.info(f"QR-код {qr_id} отсканирован пользователем {user.user_id}")
            
            return json_response({
                "valid": True,
                "scan_id": str(scan.id),
                "product_name": qr_info.product_name,
                "product_category": qr_info.category,
                "points_earned": qr_info.points,
                "description": qr_info.description,
                "timestamp": datetime.now().isoformat()
            })
        
    except Exception as e:
        logger.error(f"QR scan error: {e}")
        return json_response({
            "error": "QR scan failed"
        }, status=500)

@check_api_key
@require_auth
async def get_user_scans(request: web_request.Request) -> Response:
    """Получение истории сканирований пользователя"""
    try:
        user = request['user']
        limit = int(request.query.get('limit', 50))
        offset = int(request.query.get('offset', 0))
        
        async with AsyncSessionLocal() as db:
            scans = await db.execute(
                select(AppQRScan)
                .where(AppQRScan.user_id == user.id)
                .order_by(AppQRScan.timestamp.desc())
                .limit(limit)
                .offset(offset)
            )
            scans = scans.scalars().all()
            
            total_scans = await db.execute(
                select(func.count(AppQRScan.id)).where(AppQRScan.user_id == user.id)
            )
            total_scans = total_scans.scalar() or 0
            
            total_points = await db.execute(
                select(func.sum(AppQRScan.points_earned)).where(AppQRScan.user_id == user.id)
            )
            total_points = total_points.scalar() or 0
            
            scans_list = []
            for scan in scans:
                scans_list.append({
                    "id": str(scan.id),
                    "qr_code": str(scan.qr_id),
                    "product_name": scan.product_name,
                    "product_category": scan.product_category,
                    "points_earned": scan.points_earned,
                    "timestamp": scan.timestamp.isoformat() if scan.timestamp else None,
                    "location": scan.location
                })
            
            return json_response({
                "user_id": user.user_id,
                "total_scans": total_scans,
                "total_points": total_points,
                "scans": scans_list,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + len(scans_list) < total_scans
                }
            })
        
    except Exception as e:
        logger.error(f"Get user scans error: {e}")
        return json_response({
            "error": "Failed to get user scans"
        }, status=500)

# Автомобили

@check_api_key
async def get_cars(request: web_request.Request) -> Response:
    """Получение списка автомобилей"""
    try:
        limit = int(request.query.get('limit', 50))
        offset = int(request.query.get('offset', 0))
        
        async with AsyncSessionLocal() as db:
            cars = await db.execute(
                select(Car)
                .where(Car.is_active == True)
                .order_by(Car.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            cars = cars.scalars().all()
            
            cars_list = []
            for car in cars:
                cars_list.append({
                    "id": str(car.id),
                    "brand": car.brand,
                    "model": car.model,
                    "year": car.year,
                    "price": car.price,
                    "imageURL": car.image_url or "",
                    "description": car.description or "",
                    "specifications": {
                        "engine": car.engine or "",
                        "transmission": car.transmission or "",
                        "fuelType": car.fuel_type or "",
                        "bodyType": car.body_type or "",
                        "drivetrain": car.drivetrain or "",
                        "color": car.color or ""
                    },
                    "isActive": bool(car.is_active),
                    "createdAt": car.created_at.isoformat() if car.created_at else None
                })
            
            return json_response({
                "cars": cars_list,
                "pagination": {
                    "limit": limit,
                    "offset": offset
                }
            })
        
    except Exception as e:
        logger.error(f"Get cars error: {e}")
        return json_response({
            "error": "Failed to get cars"
        }, status=500)

@check_api_key
@require_auth
async def add_car(request: web_request.Request) -> Response:
    """Добавление нового автомобиля (только для админов)"""
    try:
        user = request['user']
        if user.role != 'admin':
            return json_response({
                "error": "Insufficient permissions"
            }, status=403)
        
        data = await request.json()
        
        required_fields = ['brand', 'model', 'year', 'price']
        if not all(field in data for field in required_fields):
            return json_response({
                "error": "Missing required fields"
            }, status=400)
        
        async with AsyncSessionLocal() as db:
            new_car = Car(
                brand=data['brand'],
                model=data['model'],
                year=data['year'],
                price=data['price'],
                description=data.get('description', ''),
                engine=data.get('engine', ''),
                transmission=data.get('transmission', ''),
                fuel_type=data.get('fuelType', ''),
                body_type=data.get('bodyType', ''),
                drivetrain=data.get('drivetrain', ''),
                color=data.get('color', ''),
                created_by=user.id
            )
            db.add(new_car)
            await db.commit()
            
            return json_response({
                "success": True,
                "car_id": str(new_car.id),
                "message": "Car added successfully"
            })
        
    except Exception as e:
        logger.error(f"Add car error: {e}")
        return json_response({
            "error": "Failed to add car"
        }, status=500)

# Товары

@check_api_key
async def get_products(request: web_request.Request) -> Response:
    """Получение списка товаров"""
    try:
        limit = int(request.query.get('limit', 50))
        offset = int(request.query.get('offset', 0))
        
        async with AsyncSessionLocal() as db:
            products = await db.execute(
                select(Product)
                .where(Product.is_active == True)
                .order_by(Product.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            products = products.scalars().all()
            
            products_list = []
            for product in products:
                products_list.append({
                    "id": str(product.id),
                    "name": product.name,
                    "category": product.category,
                    "pointsCost": product.points_cost,
                    "imageURL": product.image_url or "",
                    "description": product.description or "",
                    "stockQuantity": product.stock_quantity,
                    "isActive": bool(product.is_active),
                    "createdAt": product.created_at.isoformat() if product.created_at else None,
                    "deliveryOptions": product.delivery_options or []
                })
            
            return json_response({
                "products": products_list,
                "pagination": {
                    "limit": limit,
                    "offset": offset
                }
            })
        
    except Exception as e:
        logger.error(f"Get products error: {e}")
        return json_response({
            "error": "Failed to get products"
        }, status=500)

# Новости

@check_api_key
async def get_news(request: web_request.Request) -> Response:
    """Получение списка новостей"""
    try:
        limit = int(request.query.get('limit', 50))
        offset = int(request.query.get('offset', 0))
        
        async with AsyncSessionLocal() as db:
            news = await db.execute(
                select(NewsArticle)
                .where(NewsArticle.is_published == True)
                .order_by(NewsArticle.published_at.desc())
                .limit(limit)
                .offset(offset)
            )
            news = news.scalars().all()
            
            news_list = []
            for article in news:
                news_list.append({
                    "id": str(article.id),
                    "title": article.title,
                    "content": article.content,
                    "imageURL": article.image_url or "",
                    "isImportant": bool(article.is_important),
                    "createdAt": article.created_at.isoformat() if article.created_at else None,
                    "publishedAt": article.published_at.isoformat() if article.published_at else None,
                    "isPublished": bool(article.is_published),
                    "authorId": str(article.author_id) if article.author_id else None,
                    "tags": article.tags or []
                })
            
            return json_response({
                "news": news_list,
                "pagination": {
                    "limit": limit,
                    "offset": offset
                }
            })
        
    except Exception as e:
        logger.error(f"Get news error: {e}")
        return json_response({
            "error": "Failed to get news"
        }, status=500)

# Транзакции баллов

@check_api_key
@require_auth
async def get_user_transactions(request: web_request.Request) -> Response:
    """Получение истории транзакций пользователя"""
    try:
        user = request['user']
        limit = int(request.query.get('limit', 50))
        offset = int(request.query.get('offset', 0))
        
        async with AsyncSessionLocal() as db:
            transactions = await db.execute(
                select(PointTransaction)
                .where(PointTransaction.user_id == user.id)
                .order_by(PointTransaction.timestamp.desc())
                .limit(limit)
                .offset(offset)
            )
            transactions = transactions.scalars().all()
            
            transactions_list = []
            for transaction in transactions:
                transactions_list.append({
                    "id": str(transaction.id),
                    "userId": str(transaction.user_id),
                    "type": transaction.type,
                    "amount": transaction.amount,
                    "description": transaction.description,
                    "timestamp": transaction.timestamp.isoformat() if transaction.timestamp else None,
                    "relatedId": str(transaction.related_id) if transaction.related_id else None
                })
            
            return json_response({
                "transactions": transactions_list,
                "pagination": {
                    "limit": limit,
                    "offset": offset
                }
            })
        
    except Exception as e:
        logger.error(f"Get user transactions error: {e}")
        return json_response({
            "error": "Failed to get user transactions"
        }, status=500)

# Загрузка файлов

@check_api_key
@require_auth
async def upload_file(request: web_request.Request) -> Response:
    """Загрузка файла"""
    try:
        user = request['user']
        if user.role not in ['admin', 'operator']:
            return json_response({
                "error": "Insufficient permissions"
            }, status=403)
        
        reader = await request.multipart()
        field = await reader.next()
        
        if not field or field.name != 'file':
            return json_response({
                "error": "No file provided"
            }, status=400)
        
        # Проверка размера файла
        size = 0
        filename = field.filename or str(uuid.uuid4())
        file_ext = filename.split('.')[-1].lower() if '.' in filename else 'bin'
        
        # Генерация уникального имени файла
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        file_path = os.path.join(UPLOADS_DIR, unique_filename)
        
        with open(file_path, 'wb') as f:
            while True:
                chunk = await field.read_chunk()
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    os.remove(file_path)
                    return json_response({
                        "error": "File too large"
                    }, status=413)
                f.write(chunk)
        
        file_url = f"/uploads/{unique_filename}"
        
        return json_response({
            "success": True,
            "file_url": file_url,
            "filename": filename,
            "size": size
        })
        
    except Exception as e:
        logger.error(f"File upload error: {e}")
        return json_response({
            "error": "File upload failed"
        }, status=500)

# Статистика

@check_api_key
async def get_statistics(request: web_request.Request) -> Response:
    """Получение общей статистики"""
    try:
        async with AsyncSessionLocal() as db:
            # Общая статистика QR-кодов
            total_qr_codes = await db.execute(select(func.count(QRCode.id)))
            total_qr_codes = total_qr_codes.scalar() or 0
            
            unused_qr_codes = await db.execute(
                select(func.count(QRCode.id)).where(QRCode.is_used == False)
            )
            unused_qr_codes = unused_qr_codes.scalar() or 0
            
            used_qr_codes = await db.execute(
                select(func.count(QRCode.id)).where(QRCode.is_used == True)
            )
            used_qr_codes = used_qr_codes.scalar() or 0
            
            total_scans = await db.execute(select(func.sum(QRCode.scanned_count)))
            total_scans = total_scans.scalar() or 0
            
            # Статистика пользователей
            total_users = await db.execute(select(func.count(AppUser.id)))
            total_users = total_users.scalar() or 0
            
            active_users = await db.execute(
                select(func.count(AppUser.id)).where(AppUser.is_active == True)
            )
            active_users = active_users.scalar() or 0
            
            # Статистика сканирований
            total_app_scans = await db.execute(select(func.count(AppQRScan.id)))
            total_app_scans = total_app_scans.scalar() or 0
            
            unique_scanners = await db.execute(
                select(func.count(func.distinct(AppQRScan.user_id)))
            )
            unique_scanners = unique_scanners.scalar() or 0
            
            total_points_earned = await db.execute(
                select(func.sum(AppQRScan.points_earned))
            )
            total_points_earned = total_points_earned.scalar() or 0
            
            return json_response({
                "qr_codes": {
                    "total": total_qr_codes,
                    "unused": unused_qr_codes,
                    "used": used_qr_codes,
                    "total_scans": total_scans
                },
                "users": {
                    "total": total_users,
                    "active": active_users
                },
                "scans": {
                    "total": total_app_scans,
                    "unique_scanners": unique_scanners,
                    "total_points_earned": total_points_earned
                },
                "timestamp": datetime.now().isoformat()
            })
        
    except Exception as e:
        logger.error(f"Get statistics error: {e}")
        return json_response({
            "error": "Failed to get statistics"
        }, status=500)

async def serve_uploads(request: web_request.Request) -> Response:
    """Раздача загруженных файлов"""
    filename = request.match_info['filename']
    file_path = os.path.join(UPLOADS_DIR, filename)
    
    if not os.path.exists(file_path):
        return web.Response(status=404)
    
    return web.FileResponse(file_path)

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
    
    # Авторизация
    app.router.add_post('/api/v1/register', register_user)
    app.router.add_post('/api/v1/login', login_user)
    
    # QR-коды
    app.router.add_post('/api/v1/scan', scan_qr_code)
    app.router.add_get('/api/v1/user/scans', get_user_scans)
    
    # Автомобили
    app.router.add_get('/api/v1/cars', get_cars)
    app.router.add_post('/api/v1/cars', add_car)
    
    # Товары
    app.router.add_get('/api/v1/products', get_products)
    
    # Новости
    app.router.add_get('/api/v1/news', get_news)
    
    # Транзакции
    app.router.add_get('/api/v1/user/transactions', get_user_transactions)
    
    # Загрузка файлов
    app.router.add_post('/api/v1/upload', upload_file)
    app.router.add_get('/uploads/{filename}', serve_uploads)
    
    # Статистика
    app.router.add_get('/api/v1/statistics', get_statistics)
    
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