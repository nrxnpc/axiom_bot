#!/usr/bin/env python3
"""
Миграция для добавления функционала компаний
"""

import asyncio
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config import DATABASE_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_company_features():
    """Добавление новых полей и таблиц для функционала компаний"""
    
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    migrations = [
        # Добавление поля company_id в таблицу products
        """
        ALTER TABLE products 
        ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES app_users(id);
        """,
        
        # Добавление полей в таблицу news_articles
        """
        ALTER TABLE news_articles 
        ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES app_users(id),
        ADD COLUMN IF NOT EXISTS article_type VARCHAR DEFAULT 'news';
        """,
        
        # Создание таблицы promo_campaigns
        """
        CREATE TABLE IF NOT EXISTS promo_campaigns (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            title VARCHAR NOT NULL,
            description TEXT NOT NULL,
            campaign_type VARCHAR NOT NULL,
            discount_percent INTEGER DEFAULT 0,
            bonus_points INTEGER DEFAULT 0,
            min_purchase_amount INTEGER DEFAULT 0,
            start_date TIMESTAMP NOT NULL,
            end_date TIMESTAMP NOT NULL,
            is_active BOOLEAN DEFAULT true,
            company_id UUID NOT NULL REFERENCES app_users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            image_url VARCHAR,
            target_audience JSONB,
            usage_count INTEGER DEFAULT 0,
            max_usage INTEGER DEFAULT 0
        );
        """,
        
        # Создание индексов
        """
        CREATE INDEX IF NOT EXISTS idx_products_company_id ON products(company_id);
        CREATE INDEX IF NOT EXISTS idx_news_company_id ON news_articles(company_id);
        CREATE INDEX IF NOT EXISTS idx_campaigns_company_id ON promo_campaigns(company_id);
        CREATE INDEX IF NOT EXISTS idx_campaigns_active ON promo_campaigns(is_active, start_date, end_date);
        """
    ]
    
    try:
        async with engine.begin() as conn:
            for migration in migrations:
                logger.info(f"Выполнение миграции: {migration[:50]}...")
                await conn.execute(text(migration))
                logger.info("✅ Миграция выполнена успешно")
        
        logger.info("🎉 Все миграции выполнены успешно!")
        
    except Exception as e:
        logger.error(f"❌ Ошибка миграции: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate_company_features())