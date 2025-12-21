"""
Migration: Add resume capability columns to dd_processing_checkpoint table.

These columns store intermediate processing state to enable resuming
after long pauses (> 1 hour when the thread exits to save resources).

Run this script to add the new columns:
    python migrations/add_checkpoint_resume_columns.py

Rollback with:
    python migrations/add_checkpoint_resume_columns.py --rollback
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
    """Add resume capability columns to dd_processing_checkpoint."""

    add_columns_sql = """
    -- Pass 2 findings (for resume capability after long pause)
    ALTER TABLE dd_processing_checkpoint
    ADD COLUMN IF NOT EXISTS pass2_findings JSONB;

    -- Processed document IDs (to know which docs to skip on resume)
    ALTER TABLE dd_processing_checkpoint
    ADD COLUMN IF NOT EXISTS processed_doc_ids JSONB;
    """

    with engine.connect() as conn:
        print("Adding resume capability columns to dd_processing_checkpoint...")
        conn.execute(text(add_columns_sql))
        conn.commit()
        print("Migration completed successfully!")


def rollback_migration():
    """Remove the resume capability columns."""

    drop_columns_sql = """
    ALTER TABLE dd_processing_checkpoint
    DROP COLUMN IF EXISTS pass2_findings,
    DROP COLUMN IF EXISTS processed_doc_ids;
    """

    with engine.connect() as conn:
        print("Rolling back: Dropping resume capability columns...")
        conn.execute(text(drop_columns_sql))
        conn.commit()
        print("Rollback completed!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Resume capability columns migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    args = parser.parse_args()

    if args.rollback:
        rollback_migration()
    else:
        run_migration()
