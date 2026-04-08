#!/usr/bin/env python3
"""
Run Alembic migrations
"""

import subprocess
import sys
import os

def run_migration():
    """Run the latest Alembic migration"""
    try:
        # Change to backend directory
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(backend_dir)
        
        # Activate virtual environment and run migration
        print("Running Alembic migration...")
        
        # Run alembic upgrade head
        result = subprocess.run([
            'bash', '-c', 
            'source .venv/bin/activate && alembic upgrade head'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Migration completed successfully!")
            print(result.stdout)
        else:
            print("Migration failed!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except Exception as e:
        print(f"Error running migration: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
