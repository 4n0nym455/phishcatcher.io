#!/usr/bin/env python3
"""
Database migration script to add missing columns to analysis_jobs table
"""

import asyncio
import sys
import os

# Add the backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db_session
from sqlalchemy import text

async def run_migration():
    """Add missing columns to analysis_jobs table"""
    
    async with get_db_session() as db:
        try:
            # Add ml_score column if it doesn't exist
            await db.execute(text("""
                ALTER TABLE analysis_jobs 
                ADD COLUMN IF NOT EXISTS ml_score FLOAT;
            """))
            print("✅ Added ml_score column")
            
            # Add ti_score column if it doesn't exist
            await db.execute(text("""
                ALTER TABLE analysis_jobs 
                ADD COLUMN IF NOT EXISTS ti_score FLOAT;
            """))
            print("✅ Added ti_score column")
            
            await db.commit()
            print("✅ Migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            await db.rollback()
            return False
    
    return True

if __name__ == "__main__":
    asyncio.run(run_migration())
