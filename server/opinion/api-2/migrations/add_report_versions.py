"""
Migration: Add dd_report_version table for report versioning.

Enables iterative report improvement through AI-driven refinements
with full version history and diff tracking.

Run with: python migrations/add_report_versions.py
"""
import os
import sys
import json

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Load environment from local.settings.json
settings_path = os.path.join(parent_dir, "local.settings.json")
if os.path.exists(settings_path):
    with open(settings_path) as f:
        settings = json.load(f)
        for key, value in settings.get("Values", {}).items():
            if key not in os.environ:
                os.environ[key] = value

from shared.session import engine
from sqlalchemy import text


def run_migration():
    """Create dd_report_version table."""

    # Check if table already exists
    check_table_sql = """
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_name = 'dd_report_version'
    )
    """

    # Create the table
    create_table_sql = """
    CREATE TABLE dd_report_version (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        run_id UUID NOT NULL REFERENCES dd_analysis_run(id) ON DELETE CASCADE,

        version INTEGER NOT NULL,
        content JSONB NOT NULL,
        refinement_prompt TEXT,
        changes JSONB,

        is_current BOOLEAN DEFAULT TRUE,
        change_summary TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by VARCHAR(200)
    )
    """

    # Create index for faster lookups
    create_index_sql = """
    CREATE INDEX idx_dd_report_version_run_id ON dd_report_version(run_id);
    CREATE INDEX idx_dd_report_version_current ON dd_report_version(run_id, is_current) WHERE is_current = TRUE;
    """

    with engine.connect() as conn:
        # Check if table exists
        result = conn.execute(text(check_table_sql))
        exists = result.scalar()

        if exists:
            print("Table 'dd_report_version' already exists")
            return

        # Create the table
        print("Creating dd_report_version table...")
        conn.execute(text(create_table_sql))

        # Create indexes
        print("Creating indexes...")
        for stmt in create_index_sql.strip().split(';'):
            if stmt.strip():
                conn.execute(text(stmt))

        conn.commit()
        print("Migration completed successfully!")


def rollback_migration():
    """Drop dd_report_version table."""

    drop_table_sql = """
    DROP TABLE IF EXISTS dd_report_version CASCADE
    """

    with engine.connect() as conn:
        print("Rolling back: Dropping dd_report_version table...")
        conn.execute(text(drop_table_sql))
        conn.commit()
        print("Rollback completed!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Add dd_report_version table migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    args = parser.parse_args()

    if args.rollback:
        rollback_migration()
    else:
        run_migration()
