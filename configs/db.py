"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine("postgresql://postgres:123456789@localhost:5432/escuela")
Base = declarative_base()
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, declarative_base


# Configuración de la base de datos

# URL para conexión síncrona
DATABASE_URL_SYNC = "postgresql://postgres:123456789@localhost:5432/escuela"

# URL para conexión asincrónica
DATABASE_URL_ASYNC = "postgresql+asyncpg://postgres:123456789@localhost:5432/escuela"

# Motor síncrono
engine = create_engine(DATABASE_URL_SYNC, echo=True)

# Motor asincrónico
async_engine = create_async_engine(DATABASE_URL_ASYNC, echo=True)

# Base declarativa
Base = declarative_base()

# Sesión síncrona (para endpoints tradicionales)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Sesión asincrónica (para endpoints async) - CORREGIDO
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)