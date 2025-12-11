"""
Migration: Add granular progress tracking columns to dd_processing_checkpoint table.

These columns enable per-document progress updates for real-time UI.
Run this script to add the new columns.
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
    """Add granular progress columns to dd_processing_checkpoint."""

    add_columns_sql = """
    -- Granular pass progress (0-100)
    ALTER TABLE dd_processing_checkpoint
    ADD COLUMN IF NOT EXISTS pass1_progress INTEGER DEFAULT 0;

    ALTER TABLE dd_processing_checkpoint
    ADD COLUMN IF NOT EXISTS pass2_progress INTEGER DEFAULT 0;

    ALTER TABLE dd_processing_checkpoint
    ADD COLUMN IF NOT EXISTS pass3_progress INTEGER DEFAULT 0;

    ALTER TABLE dd_processing_checkpoint
    ADD COLUMN IF NOT EXISTS pass4_progress INTEGER DEFAULT 0;

    -- Current item being processed (for UI display)
    ALTER TABLE dd_processing_checkpoint
    ADD COLUMN IF NOT EXISTS current_document_id UUID;

    ALTER TABLE dd_processing_checkpoint
    ADD COLUMN IF NOT EXISTS current_document_name TEXT;

    ALTER TABLE dd_processing_checkpoint
    ADD COLUMN IF NOT EXISTS current_question TEXT;

    -- Finding counts (updated as findings are created)
    ALTER TABLE dd_processing_checkpoint
    ADD COLUMN IF NOT EXISTS findings_total INTEGER DEFAULT 0;

    ALTER TABLE dd_processing_checkpoint
    ADD COLUMN IF NOT EXISTS findings_critical INTEGER DEFAULT 0;

    ALTER TABLE dd_processing_checkpoint
    ADD COLUMN IF NOT EXISTS findings_high INTEGER DEFAULT 0;

    ALTER TABLE dd_processing_checkpoint
    ADD COLUMN IF NOT EXISTS findings_medium INTEGER DEFAULT 0;

    ALTER TABLE dd_processing_checkpoint
    ADD COLUMN IF NOT EXISTS findings_low INTEGER DEFAULT 0;

    ALTER TABLE dd_processing_checkpoint
    ADD COLUMN IF NOT EXISTS findings_deal_blockers INTEGER DEFAULT 0;

    ALTER TABLE dd_processing_checkpoint
    ADD COLUMN IF NOT EXISTS findings_cps INTEGER DEFAULT 0;

    -- Cluster info
    ALTER TABLE dd_processing_checkpoint
    ADD COLUMN IF NOT EXISTS clusters_total INTEGER DEFAULT 0;
    """

    with engine.connect() as conn:
        print("Adding granular progress columns to dd_processing_checkpoint...")
        conn.execute(text(add_columns_sql))
        conn.commit()
        print("Migration completed successfully!")


def rollback_migration():
    """Remove the granular progress columns."""

    drop_columns_sql = """
    ALTER TABLE dd_processing_checkpoint
    DROP COLUMN IF EXISTS pass1_progress,
    DROP COLUMN IF EXISTS pass2_progress,
    DROP COLUMN IF EXISTS pass3_progress,
    DROP COLUMN IF EXISTS pass4_progress,
    DROP COLUMN IF EXISTS current_document_id,
    DROP COLUMN IF EXISTS current_document_name,
    DROP COLUMN IF EXISTS current_question,
    DROP COLUMN IF EXISTS findings_total,
    DROP COLUMN IF EXISTS findings_critical,
    DROP COLUMN IF EXISTS findings_high,
    DROP COLUMN IF EXISTS findings_medium,
    DROP COLUMN IF EXISTS findings_low,
    DROP COLUMN IF EXISTS findings_deal_blockers,
    DROP COLUMN IF EXISTS findings_cps,
    DROP COLUMN IF EXISTS clusters_total;
    """

    with engine.connect() as conn:
        print("Rolling back: Dropping granular progress columns...")
        conn.execute(text(drop_columns_sql))
        conn.commit()
        print("Rollback completed!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Granular progress columns migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    args = parser.parse_args()

    if args.rollback:
        rollback_migration()
    else:
        run_migration()
