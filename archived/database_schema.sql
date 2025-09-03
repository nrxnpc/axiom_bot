-- Обновленная схема базы данных для полной интеграции

-- Таблица QR-кодов (существующая, дополненная)
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
    last_scanned TIMESTAMP,
    is_used BOOLEAN DEFAULT FALSE,  -- Новое поле для одноразового использования
    used_by INTEGER,  -- ID пользователя, который использовал код
    used_at TIMESTAMP  -- Время использования
);

-- Таблица пользователей мобильного приложения
CREATE TABLE IF NOT EXISTS app_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE NOT NULL,  -- UUID из приложения
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    password_hash TEXT NOT NULL,
    user_type TEXT DEFAULT 'individual', -- individual, business
    points INTEGER DEFAULT 0,
    role TEXT DEFAULT 'user', -- user, admin, operator
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    telegram_id INTEGER  -- Связь с Telegram ID если есть
);

-- Таблица автомобилей
CREATE TABLE IF NOT EXISTS cars (
    id TEXT PRIMARY KEY,
    brand TEXT NOT NULL,
    model TEXT NOT NULL,
    year INTEGER NOT NULL,
    price TEXT NOT NULL,
    image_url TEXT,
    description TEXT,
    engine TEXT,
    transmission TEXT,
    fuel_type TEXT,
    body_type TEXT,
    drivetrain TEXT,
    color TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    FOREIGN KEY (created_by) REFERENCES app_users(user_id)
);

-- Таблица товаров для обмена баллов
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL, -- merchandise, discounts, accessories, services
    points_cost INTEGER NOT NULL,
    image_url TEXT,
    description TEXT,
    stock_quantity INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    delivery_options TEXT, -- JSON array of delivery options
    created_by TEXT,
    FOREIGN KEY (created_by) REFERENCES app_users(user_id)
);

-- Таблица новостей
CREATE TABLE IF NOT EXISTS news_articles (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    image_url TEXT,
    is_important BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP,
    is_published BOOLEAN DEFAULT FALSE,
    author_id TEXT NOT NULL,
    tags TEXT, -- JSON array of tags
    FOREIGN KEY (author_id) REFERENCES app_users(user_id)
);

-- Таблица лотерей
CREATE TABLE IF NOT EXISTS lotteries (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    prize TEXT NOT NULL,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    participants TEXT, -- JSON array of user IDs
    winner_id TEXT,
    min_points_required INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    image_url TEXT,
    FOREIGN KEY (winner_id) REFERENCES app_users(user_id)
);

-- Таблица заказов
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    points_spent INTEGER NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, confirmed, processing, shipped, delivered, cancelled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    delivery_address TEXT,
    delivery_option TEXT NOT NULL, -- pickup, delivery, digital
    tracking_number TEXT,
    FOREIGN KEY (user_id) REFERENCES app_users(user_id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Таблица запросов цены
CREATE TABLE IF NOT EXISTS price_requests (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    car_id TEXT NOT NULL,
    user_message TEXT,
    status TEXT DEFAULT 'pending', -- pending, responded, expired
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dealer_response TEXT,
    estimated_price TEXT,
    responded_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES app_users(user_id),
    FOREIGN KEY (car_id) REFERENCES cars(id)
);

-- Таблица транзакций баллов
CREATE TABLE IF NOT EXISTS point_transactions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    type TEXT NOT NULL, -- earned, spent, bonus, penalty
    amount INTEGER NOT NULL,
    description TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    related_id TEXT, -- ID связанной записи (заказ, скан и т.д.)
    qr_scan_id TEXT, -- ID сканирования QR-кода
    FOREIGN KEY (user_id) REFERENCES app_users(user_id)
);

-- Таблица сканирований QR-кодов из приложения
CREATE TABLE IF NOT EXISTS app_qr_scans (
    id TEXT PRIMARY KEY,
    qr_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    points_earned INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    product_category TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    location TEXT,
    FOREIGN KEY (qr_id) REFERENCES qr_codes(qr_id),
    FOREIGN KEY (user_id) REFERENCES app_users(user_id)
);

-- Таблица тикетов поддержки
CREATE TABLE IF NOT EXISTS support_tickets (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    status TEXT DEFAULT 'open', -- open, inProgress, resolved, closed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    priority TEXT DEFAULT 'medium', -- low, medium, high, urgent
    FOREIGN KEY (user_id) REFERENCES app_users(user_id)
);

-- Таблица сообщений поддержки
CREATE TABLE IF NOT EXISTS support_messages (
    id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL,
    content TEXT NOT NULL,
    sender_id TEXT NOT NULL,
    sender_role TEXT NOT NULL, -- user, admin, operator
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    attachments TEXT, -- JSON array of attachment URLs
    FOREIGN KEY (ticket_id) REFERENCES support_tickets(id),
    FOREIGN KEY (sender_id) REFERENCES app_users(user_id)
);

-- Таблица сессий пользователей
CREATE TABLE IF NOT EXISTS user_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    device_info TEXT,
    FOREIGN KEY (user_id) REFERENCES app_users(user_id)
);

-- Создание индексов для производительности
CREATE INDEX IF NOT EXISTS idx_qr_codes_qr_id ON qr_codes(qr_id);
CREATE INDEX IF NOT EXISTS idx_qr_codes_used ON qr_codes(is_used);
CREATE INDEX IF NOT EXISTS idx_app_users_email ON app_users(email);
CREATE INDEX IF NOT EXISTS idx_app_users_user_id ON app_users(user_id);
CREATE INDEX IF NOT EXISTS idx_point_transactions_user_id ON point_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_app_qr_scans_user_id ON app_qr_scans(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(token);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);

-- Триггер для обновления updated_at в support_tickets
CREATE TRIGGER IF NOT EXISTS update_support_tickets_updated_at
    AFTER UPDATE ON support_tickets
    FOR EACH ROW
    BEGIN
        UPDATE support_tickets SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- Триггер для автоматического начисления баллов при сканировании QR
CREATE TRIGGER IF NOT EXISTS update_user_points_on_qr_scan
    AFTER INSERT ON app_qr_scans
    FOR EACH ROW
    BEGIN
        UPDATE app_users 
        SET points = points + NEW.points_earned 
        WHERE user_id = NEW.user_id;
    END;

-- Триггер для обновления баллов при транзакциях
CREATE TRIGGER IF NOT EXISTS update_user_points_on_transaction
    AFTER INSERT ON point_transactions
    FOR EACH ROW
    WHEN NEW.type IN ('spent', 'penalty')
    BEGIN
        UPDATE app_users 
        SET points = points - NEW.amount 
        WHERE user_id = NEW.user_id;
    END;