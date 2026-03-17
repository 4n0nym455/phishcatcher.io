"""Add normalized_email column to users table

Revision ID: 20250226_2130_norm_email
Revises: 20250225_1750_add_gmail_fields
Create Date: 2026-02-26 21:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250226_2130_norm_email'
down_revision = '20250225_1750_add_gmail_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add normalized_email column to users table."""
    # Add the column
    op.add_column('users', sa.Column('normalized_email', sa.String(255), nullable=True))
    
    # Create index for performance
    op.create_index('ix_users_normalized_email', 'users', ['normalized_email'])
    
    # Update existing records with normalized emails
    connection = op.get_bind()
    
    # Update all existing users to have normalized emails (basic)
    connection.execute(sa.text("""
        UPDATE users 
        SET normalized_email = LOWER(TRIM(email))
        WHERE normalized_email IS NULL
    """))
    
    # Handle Gmail aliases (remove + and .)
    connection.execute(sa.text("""
        UPDATE users 
        SET normalized_email = 
            REPLACE(
                SPLIT_PART(LOWER(TRIM(email)), '+', 1),
                '.', ''
            ) || '@' || SPLIT_PART(LOWER(TRIM(email)), '@', 2)
        WHERE normalized_email IS NULL 
        AND (LOWER(SPLIT_PART(email, '@', 2)) LIKE '%@gmail.com' OR LOWER(SPLIT_PART(email, '@', 2)) LIKE '%@googlemail.com')
    """))
    
    # Handle Outlook/Hotmail aliases (remove +)
    connection.execute(sa.text("""
        UPDATE users 
        SET normalized_email = 
            SPLIT_PART(LOWER(TRIM(email)), '+', 1) || '@' || SPLIT_PART(LOWER(TRIM(email)), '@', 2)
        WHERE normalized_email IS NULL
        AND LOWER(SPLIT_PART(email, '@', 2)) IN ('outlook.com', 'hotmail.com', 'live.com')
    """))
    
    # Handle Yahoo aliases (remove -)
    connection.execute(sa.text("""
        UPDATE users 
        SET normalized_email = 
            SPLIT_PART(LOWER(TRIM(email)), '-', 1) || '@' || SPLIT_PART(LOWER(TRIM(email)), '@', 2)
        WHERE normalized_email IS NULL
        AND LOWER(SPLIT_PART(email, '@', 2)) IN ('yahoo.com', 'ymail.com')
    """))
    
    # Make the column NOT NULL after filling it
    op.alter_column('users', 'normalized_email', nullable=False)


def downgrade() -> None:
    """Remove normalized_email column from users table."""
    op.drop_index('ix_users_normalized_email', table_name='users')
    op.drop_column('users', 'normalized_email')
