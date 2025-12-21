"""
Migration: Add synthesis_data column to dd_analysis_run table.

This stores the Pass 4 synthesis output including:
- executive_summary
- deal_assessment
- financial_exposures
- deal_blockers
- conditions_precedent
- recommendations

Run with: python migrations/add_synthesis_data.py
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
    """Add synthesis_data column to dd_analysis_run table."""

    # Check if column already exists
    check_column_sql = """
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'dd_analysis_run'
    AND column_name = 'synthesis_data'
    """

    # Add the synthesis_data column
    add_column_sql = """
    ALTER TABLE dd_analysis_run
    ADD COLUMN synthesis_data JSONB DEFAULT NULL
    """

    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text(check_column_sql))
        if result.fetchone():
            print("Column 'synthesis_data' already exists in dd_analysis_run table")
            return

        # Add the column
        print("Adding synthesis_data column to dd_analysis_run table...")
        conn.execute(text(add_column_sql))
        conn.commit()

        print("Migration completed successfully!")


def rollback_migration():
    """Remove synthesis_data column from dd_analysis_run table."""

    drop_column_sql = """
    ALTER TABLE dd_analysis_run DROP COLUMN IF EXISTS synthesis_data
    """

    with engine.connect() as conn:
        print("Rolling back: Removing synthesis_data column...")
        conn.execute(text(drop_column_sql))
        conn.commit()

        print("Rollback completed!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Add synthesis_data column migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    args = parser.parse_args()

    if args.rollback:
        rollback_migration()
    else:
        run_migration()
