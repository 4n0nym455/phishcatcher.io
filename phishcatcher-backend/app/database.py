"""
PhishCatcher Database Module

This module handles database connections and session management for:
- PostgreSQL (primary database for users, jobs, audit logs)
- MongoDB (analysis results storage)
- Redis (caching and sessions)
"""

from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager
import logging

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    AsyncEngine,
    async_sessionmaker
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
import motor.motor_asyncio
import redis.asyncio as redis

from app.config import get_settings

logger = logging.getLogger(__name__)

# SQLAlchemy Base for PostgreSQL models
Base = declarative_base()

# Global connection pools
_engine: Optional[AsyncEngine] = None
_async_session_maker: Optional[async_sessionmaker] = None
_mongodb_client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
_redis_client: Optional[redis.Redis] = None


def get_engine() -> AsyncEngine:
    """Get or create async database engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.DATABASE_URL,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_pre_ping=True,  # Verify connections before using
            echo=settings.DEBUG,  # Log SQL queries in debug mode
            future=True
        )
    return _engine


def get_session_maker() -> async_sessionmaker:
    """Get or create async session maker."""
    global _async_session_maker
    if _async_session_maker is None:
        engine = get_engine()
        _async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
    return _async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_mongodb_client() -> motor.motor_asyncio.AsyncIOMotorClient:
    """Get or create MongoDB client."""
    global _mongodb_client
    if _mongodb_client is None:
        settings = get_settings()
        _mongodb_client = motor.motor_asyncio.AsyncIOMotorClient(
            settings.MONGODB_URL,
            maxPoolSize=50,
            minPoolSize=10,
            serverSelectionTimeoutMS=5000
        )
    return _mongodb_client


def get_mongodb_database() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    """Get MongoDB database instance."""
    client = get_mongodb_client()
    settings = get_settings()
    return client[settings.MONGODB_DB_NAME]


async def get_mongodb() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    """Dependency for getting MongoDB database."""
    return get_mongodb_database()


def get_redis_client() -> redis.Redis:
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.REDIS_POOL_SIZE
        )
    return _redis_client


async def get_redis() -> redis.Redis:
    """Dependency for getting Redis client."""
    return get_redis_client()


async def init_databases():
    """Initialize all database connections."""
    logger.info("Initializing database connections...")
    
    # Initialize PostgreSQL
    engine = get_engine()
    async with engine.begin() as conn:
        # Create tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)
    logger.info("PostgreSQL initialized")
    
    # Test MongoDB connection
    mongodb = get_mongodb_database()
    await mongodb.command("ping")
    logger.info("MongoDB initialized")
    
    # Test Redis connection
    redis_client = get_redis_client()
    await redis_client.ping()
    logger.info("Redis initialized")
    
    logger.info("All database connections initialized successfully")


async def close_databases():
    """Close all database connections."""
    global _engine, _mongodb_client, _redis_client
    
    logger.info("Closing database connections...")
    
    # Close PostgreSQL
    if _engine:
        await _engine.dispose()
        _engine = None
        logger.info("PostgreSQL connection closed")
    
    # Close MongoDB
    if _mongodb_client:
        _mongodb_client.close()
        _mongodb_client = None
        logger.info("MongoDB connection closed")
    
    # Close Redis
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")
    
    logger.info("All database connections closed")


async def check_database_health() -> dict:
    """Check health of all database connections."""
    health = {
        "postgresql": False,
        "mongodb": False,
        "redis": False
    }
    
    try:
        # Check PostgreSQL
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        health["postgresql"] = True
    except Exception as e:
        logger.error(f"PostgreSQL health check failed: {e}")
    
    try:
        # Check MongoDB
        mongodb = get_mongodb_database()
        await mongodb.command("ping")
        health["mongodb"] = True
    except Exception as e:
        logger.error(f"MongoDB health check failed: {e}")
    
    try:
        # Check Redis
        redis_client = get_redis_client()
        await redis_client.ping()
        health["redis"] = True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
    
    return health
