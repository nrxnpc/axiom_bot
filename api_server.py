#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API сервер для интеграции мобильного приложения с базой данных QR-кодов
"""

import asyncio
import logging
import json
import sqlite3
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
import aiohttp_cors

# Конфигурация
DATABASE_PATH = "nsp_qr_bot.db"  # Используем базу данных бота
API_HOST = "0.0.0.0"
API_PORT = 8080
UPLOADS_DIR = "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# API ключи для авторизации
API_KEYS = {
    "nsp_mobile_app": "nsp_mobile_app_api_key_2024",
    "nsp_admin": "nsp_admin_api_key_2024"
}

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

def get_db_connection():
    """Получение подключения к базе данных"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Инициализация базы данных с новыми таблицами"""
    with open('database_schema.sql', 'r', encoding='utf-8') as f:
        schema = f.read()
    
    conn = get_db_connection()
    try:
        conn.executescript(schema)
        conn.commit()
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
        raise
    finally:
        conn.close()

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

async def get_user_by_token(token: str) -> Optional[Dict]:
    """Получение пользователя по токену"""
    conn = get_db_connection()
    try:
        cursor = conn.execute('''
            SELECT u.*, s.expires_at 
            FROM app_users u
            JOIN user_sessions s ON u.user_id = s.user_id
            WHERE s.token = ? AND s.is_active = 1 AND s.expires_at > datetime('now')
        ''', (token,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

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
        conn = get_db_connection()
        conn.execute("SELECT 1").fetchone()
        conn.close()
        
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
        
        # Проверка существования пользователя
        conn = get_db_connection()
        existing_user = conn.execute(
            "SELECT user_id FROM app_users WHERE email = ?",
            (data['email'],)
        ).fetchone()
        
        if existing_user:
            conn.close()
            return json_response({
                "error": "User with this email already exists"
            }, status=400)
        
        # Создание нового пользователя
        user_id = str(uuid.uuid4())
        password_hash = hash_password(data['password'])
        
        conn.execute('''
            INSERT INTO app_users (user_id, name, email, phone, password_hash, user_type)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, data['name'], data['email'], data['phone'], password_hash, data['userType']))
        
        # Создание сессии
        token = generate_token()
        session_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(days=30)
        
        conn.execute('''
            INSERT INTO user_sessions (id, user_id, token, expires_at, device_info)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_id, user_id, token, expires_at, data.get('deviceInfo', '')))
        
        # Начальное начисление баллов
        conn.execute('''
            UPDATE app_users SET points = 100 WHERE user_id = ?
        ''', (user_id,))
        
        # Запись транзакции начисления
        transaction_id = str(uuid.uuid4())
        conn.execute('''
            INSERT INTO point_transactions (id, user_id, type, amount, description)
            VALUES (?, ?, 'bonus', 100, 'Бонус за регистрацию')
        ''', (transaction_id, user_id))
        
        conn.commit()
        conn.close()
        
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
        
        conn = get_db_connection()
        password_hash = hash_password(data['password'])
        
        user = conn.execute('''
            SELECT * FROM app_users 
            WHERE email = ? AND password_hash = ? AND is_active = 1
        ''', (data['email'], password_hash)).fetchone()
        
        if not user:
            conn.close()
            return json_response({
                "error": "Invalid credentials"
            }, status=401)
        
        # Создание новой сессии
        token = generate_token()
        session_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(days=30)
        
        conn.execute('''
            INSERT INTO user_sessions (id, user_id, token, expires_at, device_info)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_id, user['user_id'], token, expires_at, data.get('deviceInfo', '')))
        
        # Обновление времени последнего входа
        conn.execute('''
            UPDATE app_users SET last_login = datetime('now') WHERE user_id = ?
        ''', (user['user_id'],))
        
        conn.commit()
        conn.close()
        
        return json_response({
            "success": True,
            "user": {
                "id": user['user_id'],
                "name": user['name'],
                "email": user['email'],
                "phone": user['phone'],
                "userType": user['user_type'],
                "points": user['points'],
                "role": user['role'],
                "registrationDate": user['registration_date'],
                "isActive": user['is_active']
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
        user_id = request['user']['user_id']
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
        
        conn = get_db_connection()
        
        # Поиск QR-кода в базе данных
        qr_info = conn.execute('''
            SELECT * FROM qr_codes WHERE qr_id = ?
        ''', (qr_id,)).fetchone()
        
        if not qr_info:
            conn.close()
            return json_response({
                "error": "QR code not found",
                "valid": False
            }, status=404)
        
        # Проверка на использование
        if qr_info['is_used']:
            conn.close()
            return json_response({
                "error": "QR code already used",
                "valid": False,
                "product_name": qr_info['product_name'],
                "used_at": qr_info['used_at']
            }, status=409)
        
        # Отметка QR-кода как использованного
        conn.execute('''
            UPDATE qr_codes 
            SET is_used = 1, used_by = ?, used_at = datetime('now'),
                scanned_count = scanned_count + 1, last_scanned = datetime('now')
            WHERE qr_id = ?
        ''', (user_id, qr_id))
        
        # Запись сканирования
        scan_id = str(uuid.uuid4())
        conn.execute('''
            INSERT INTO app_qr_scans 
            (id, qr_id, user_id, points_earned, product_name, product_category, location)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (scan_id, qr_id, user_id, qr_info['points'],
              qr_info['product_name'], qr_info['category'], location))
        
        # Запись транзакции баллов
        transaction_id = str(uuid.uuid4())
        conn.execute('''
            INSERT INTO point_transactions 
            (id, user_id, type, amount, description, qr_scan_id)
            VALUES (?, ?, 'earned', ?, ?, ?)
        ''', (transaction_id, user_id, qr_info['points'],
              f"Сканирование QR-кода ({qr_info['product_name']})", scan_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"QR-код {qr_id} отсканирован пользователем {user_id}")
        
        return json_response({
            "valid": True,
            "scan_id": scan_id,
            "product_name": qr_info['product_name'],
            "product_category": qr_info['category'],
            "points_earned": qr_info['points'],
            "description": qr_info['description'],
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
        user_id = request['user']['user_id']
        limit = int(request.query.get('limit', 50))
        offset = int(request.query.get('offset', 0))
        
        conn = get_db_connection()
        
        scans = conn.execute('''
            SELECT * FROM app_qr_scans 
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        ''', (user_id, limit, offset)).fetchall()
        
        total_scans = conn.execute('''
            SELECT COUNT(*) as count FROM app_qr_scans WHERE user_id = ?
        ''', (user_id,)).fetchone()['count']
        
        total_points = conn.execute('''
            SELECT COALESCE(SUM(points_earned), 0) as total 
            FROM app_qr_scans WHERE user_id = ?
        ''', (user_id,)).fetchone()['total']
        
        conn.close()
        
        scans_list = []
        for scan in scans:
            scans_list.append({
                "id": scan['id'],
                "qr_code": scan['qr_id'],
                "product_name": scan['product_name'],
                "product_category": scan['product_category'],
                "points_earned": scan['points_earned'],
                "timestamp": scan['timestamp'],
                "location": scan['location']
            })
        
        return json_response({
            "user_id": user_id,
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
        
        conn = get_db_connection()
        
        cars = conn.execute('''
            SELECT * FROM cars 
            WHERE is_active = 1
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset)).fetchall()
        
        conn.close()
        
        cars_list = []
        for car in cars:
            cars_list.append({
                "id": car['id'],
                "brand": car['brand'],
                "model": car['model'],
                "year": car['year'],
                "price": car['price'],
                "imageURL": car['image_url'] or "",
                "description": car['description'] or "",
                "specifications": {
                    "engine": car['engine'] or "",
                    "transmission": car['transmission'] or "",
                    "fuelType": car['fuel_type'] or "",
                    "bodyType": car['body_type'] or "",
                    "drivetrain": car['drivetrain'] or "",
                    "color": car['color'] or ""
                },
                "isActive": bool(car['is_active']),
                "createdAt": car['created_at']
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
        if user['role'] != 'admin':
            return json_response({
                "error": "Insufficient permissions"
            }, status=403)
        
        data = await request.json()
        
        required_fields = ['brand', 'model', 'year', 'price']
        if not all(field in data for field in required_fields):
            return json_response({
                "error": "Missing required fields"
            }, status=400)
        
        car_id = str(uuid.uuid4())
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO cars (
                id, brand, model, year, price, description, 
                engine, transmission, fuel_type, body_type, 
                drivetrain, color, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            car_id, data['brand'], data['model'], data['year'], data['price'],
            data.get('description', ''), data.get('engine', ''),
            data.get('transmission', ''), data.get('fuelType', ''),
            data.get('bodyType', ''), data.get('drivetrain', ''),
            data.get('color', ''), user['user_id']
        ))
        conn.commit()
        conn.close()
        
        return json_response({
            "success": True,
            "car_id": car_id,
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
        
        conn = get_db_connection()
        
        products = conn.execute('''
            SELECT * FROM products 
            WHERE is_active = 1
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset)).fetchall()
        
        conn.close()
        
        products_list = []
        for product in products:
            delivery_options = json.loads(product['delivery_options']) if product['delivery_options'] else []
            
            products_list.append({
                "id": product['id'],
                "name": product['name'],
                "category": product['category'],
                "pointsCost": product['points_cost'],
                "imageURL": product['image_url'] or "",
                "description": product['description'] or "",
                "stockQuantity": product['stock_quantity'],
                "isActive": bool(product['is_active']),
                "createdAt": product['created_at'],
                "deliveryOptions": delivery_options
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
        
        conn = get_db_connection()
        
        news = conn.execute('''
            SELECT * FROM news_articles 
            WHERE is_published = 1
            ORDER BY published_at DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset)).fetchall()
        
        conn.close()
        
        news_list = []
        for article in news:
            tags = json.loads(article['tags']) if article['tags'] else []
            
            news_list.append({
                "id": article['id'],
                "title": article['title'],
                "content": article['content'],
                "imageURL": article['image_url'] or "",
                "isImportant": bool(article['is_important']),
                "createdAt": article['created_at'],
                "publishedAt": article['published_at'],
                "isPublished": bool(article['is_published']),
                "authorId": article['author_id'],
                "tags": tags
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
        user_id = request['user']['user_id']
        limit = int(request.query.get('limit', 50))
        offset = int(request.query.get('offset', 0))
        
        conn = get_db_connection()
        
        transactions = conn.execute('''
            SELECT * FROM point_transactions 
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        ''', (user_id, limit, offset)).fetchall()
        
        conn.close()
        
        transactions_list = []
        for transaction in transactions:
            transactions_list.append({
                "id": transaction['id'],
                "userId": transaction['user_id'],
                "type": transaction['type'],
                "amount": transaction['amount'],
                "description": transaction['description'],
                "timestamp": transaction['timestamp'],
                "relatedId": transaction['related_id']
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
        if user['role'] not in ['admin', 'operator']:
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
        conn = get_db_connection()
        
        # Общая статистика QR-кодов
        qr_stats = conn.execute('''
            SELECT 
                COUNT(*) as total_qr_codes,
                COUNT(*) FILTER (WHERE is_used = 0) as unused_qr_codes,
                COUNT(*) FILTER (WHERE is_used = 1) as used_qr_codes,
                COALESCE(SUM(scanned_count), 0) as total_scans
            FROM qr_codes
        ''').fetchone()
        
        # Статистика пользователей
        user_stats = conn.execute('''
            SELECT 
                COUNT(*) as total_users,
                COUNT(*) FILTER (WHERE is_active = 1) as active_users
            FROM app_users
        ''').fetchone()
        
        # Статистика сканирований
        scan_stats = conn.execute('''
            SELECT 
                COUNT(*) as total_app_scans,
                COUNT(DISTINCT user_id) as unique_scanners,
                COALESCE(SUM(points_earned), 0) as total_points_earned
            FROM app_qr_scans
        ''').fetchone()
        
        conn.close()
        
        return json_response({
            "qr_codes": {
                "total": qr_stats['total_qr_codes'],
                "unused": qr_stats['unused_qr_codes'],
                "used": qr_stats['used_qr_codes'],
                "total_scans": qr_stats['total_scans']
            },
            "users": {
                "total": user_stats['total_users'],
                "active": user_stats['active_users']
            },
            "scans": {
                "total": scan_stats['total_app_scans'],
                "unique_scanners": scan_stats['unique_scanners'],
                "total_points_earned": scan_stats['total_points_earned']
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

def main():
    """Главная функция"""
    try:
        # Инициализация базы данных
        init_database()
        
        # Создание приложения
        app = init_app()
        
        # Запуск сервера
        logger.info(f"Запуск API сервера на {API_HOST}:{API_PORT}")
        web.run_app(app, host=API_HOST, port=API_PORT)
        
    except Exception as e:
        logger.error(f"Ошибка запуска API сервера: {e}")

if __name__ == "__main__":
    main()
