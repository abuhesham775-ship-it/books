"""
Database Module - إعداد الاتصال بقاعدة البيانات
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from config.settings import get_settings

settings = get_settings()

# إنشاء قاعدة البيانات - استخدام NullPool دائماً لتجنب مشاكل الاتصال
# NullPool لا يدعم pool_size و max_overflow
engine = create_engine(
    settings.database_url,
    poolclass=NullPool,
    echo=settings.debug
)

# إنشاء Session Maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base Class للنماذج
Base = declarative_base()


def get_db():
    """الحصول على جلسة قاعدة البيانات"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """تهيئة قاعدة البيانات - إنشاء جميع الجداول"""
    import app.models  # مهم جدًا لتسجيل جميع النماذج قبل إنشاء الجداول
    Base.metadata.create_all(bind=engine)
