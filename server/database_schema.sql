-- NSP QR Bot Database Schema for PostgreSQL

-- Пользователи приложения
CREATE TABLE IF NOT EXISTS app_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    phone VARCHAR,
    password_hash VARCHAR NOT NULL,
    user_type VARCHAR DEFAULT 'individual',
    points INTEGER DEFAULT 0,
    role VARCHAR DEFAULT 'user',
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    telegram_id INTEGER
);

-- QR коды
CREATE TABLE IF NOT EXISTS qr_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    qr_id VARCHAR UNIQUE NOT NULL,
    product_name VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    points INTEGER NOT NULL,
    description TEXT,
    created_by UUID REFERENCES app_users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scanned_count INTEGER DEFAULT 0,
    last_scanned TIMESTAMP,
    is_used BOOLEAN DEFAULT FALSE,
    used_by UUID REFERENCES app_users(id),
    used_at TIMESTAMP
);

-- Сканирования QR кодов
CREATE TABLE IF NOT EXISTS app_qr_scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    qr_id UUID REFERENCES qr_codes(id) NOT NULL,
    user_id UUID REFERENCES app_users(id) NOT NULL,
    points_earned INTEGER NOT NULL,
    product_name VARCHAR NOT NULL,
    product_category VARCHAR NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    location VARCHAR
);

-- Транзакции баллов
CREATE TABLE IF NOT EXISTS point_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES app_users(id) NOT NULL,
    type VARCHAR NOT NULL,
    amount INTEGER NOT NULL,
    description TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    related_id UUID,
    qr_scan_id UUID
);

-- Сессии пользователей
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES app_users(id) NOT NULL,
    token VARCHAR UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    device_info TEXT
);

-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_qr_codes_qr_id ON qr_codes(qr_id);
CREATE INDEX IF NOT EXISTS idx_app_users_email ON app_users(email);
CREATE INDEX IF NOT EXISTS idx_app_users_telegram_id ON app_users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(token);
CREATE INDEX IF NOT EXISTS idx_point_transactions_user_id ON point_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_app_qr_scans_user_id ON app_qr_scans(user_id);