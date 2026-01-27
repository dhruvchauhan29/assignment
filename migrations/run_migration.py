#!/usr/bin/env python3
"""
Database migration script for milestone-driven system.

This script adds new columns to support:
- Document uploads in projects
- Approval actions (proceed/regenerate/reject)
"""
from sqlalchemy import create_engine, text
from app.config import get_settings

def run_migration():
    """Run database migration."""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    migrations = [
        # Add documents column to projects
        """
        ALTER TABLE projects 
        ADD COLUMN IF NOT EXISTS documents JSON;
        """,
        
        # Add action column to approvals
        """
        ALTER TABLE approvals 
        ADD COLUMN IF NOT EXISTS action VARCHAR(50) DEFAULT 'proceed';
        """,
        
        # Create indexes
        """
        CREATE INDEX IF NOT EXISTS idx_approvals_action 
        ON approvals(action);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_approvals_stage_run 
        ON approvals(run_id, stage);
        """
    ]
    
    print("Running database migrations...")
    
    with engine.connect() as conn:
        for i, migration in enumerate(migrations, 1):
            try:
                conn.execute(text(migration))
                conn.commit()
                print(f"✓ Migration {i}/{len(migrations)} completed successfully")
            except Exception as e:
                print(f"✗ Migration {i}/{len(migrations)} failed: {e}")
                # Continue with other migrations
    
    print("\nMigrations completed!")
    print("\nNote: If using SQLite for testing, some ALTER TABLE operations may not be supported.")
    print("In that case, the tables will be recreated automatically by SQLAlchemy on startup.")


if __name__ == "__main__":
    run_migration()
