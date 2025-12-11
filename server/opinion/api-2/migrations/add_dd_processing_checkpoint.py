"""
Migration: Add DD Processing Checkpoint table for optimized pipeline resume capability.

Run this script to create the dd_processing_checkpoint table.
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
    """Create the dd_processing_checkpoint table."""

    create_enum_sql = """
    DO $$ BEGIN
        CREATE TYPE processing_status_enum AS ENUM ('pending', 'processing', 'completed', 'failed', 'paused');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS dd_processing_checkpoint (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        dd_id UUID NOT NULL UNIQUE REFERENCES due_diligence(id) ON DELETE CASCADE,

        -- Current processing state
        current_pass INTEGER DEFAULT 1,
        current_stage VARCHAR(100),
        status processing_status_enum DEFAULT 'pending',

        -- Pass 1 outputs (stored for reuse in later passes)
        pass1_extractions JSONB,

        -- Progress tracking
        documents_processed INTEGER DEFAULT 0,
        total_documents INTEGER,
        clusters_processed JSONB,
        questions_processed INTEGER DEFAULT 0,
        total_questions INTEGER,

        -- Cost tracking
        total_input_tokens INTEGER DEFAULT 0,
        total_output_tokens INTEGER DEFAULT 0,
        estimated_cost_usd FLOAT DEFAULT 0.0,
        cost_by_model JSONB,

        -- Timestamps
        started_at TIMESTAMP DEFAULT NOW(),
        last_updated TIMESTAMP DEFAULT NOW(),
        completed_at TIMESTAMP,

        -- Error handling
        last_error TEXT,
        retry_count INTEGER DEFAULT 0
    );
    """

    create_index_sql = """
    CREATE INDEX IF NOT EXISTS idx_dd_processing_checkpoint_dd_id
    ON dd_processing_checkpoint(dd_id);

    CREATE INDEX IF NOT EXISTS idx_dd_processing_checkpoint_status
    ON dd_processing_checkpoint(status);
    """

    with engine.connect() as conn:
        # Create enum type (if not exists)
        print("Creating processing_status_enum type...")
        conn.execute(text(create_enum_sql))
        conn.commit()

        # Create table
        print("Creating dd_processing_checkpoint table...")
        conn.execute(text(create_table_sql))
        conn.commit()

        # Create indexes
        print("Creating indexes...")
        conn.execute(text(create_index_sql))
        conn.commit()

        print("Migration completed successfully!")


def rollback_migration():
    """Drop the dd_processing_checkpoint table."""

    drop_sql = """
    DROP TABLE IF EXISTS dd_processing_checkpoint CASCADE;
    DROP TYPE IF EXISTS processing_status_enum CASCADE;
    """

    with engine.connect() as conn:
        print("Rolling back: Dropping dd_processing_checkpoint table...")
        conn.execute(text(drop_sql))
        conn.commit()
        print("Rollback completed!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DD Processing Checkpoint migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    args = parser.parse_args()

    if args.rollback:
        rollback_migration()
    else:
        run_migration()
