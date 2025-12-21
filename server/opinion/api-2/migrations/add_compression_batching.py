"""
Migration: Add tables for Phase 4 Summary Compression + Batching.

Creates:
1. dd_compressed_summaries - Store compressed document summaries for reuse
2. dd_batch_execution - Track batch execution for Pass 3

Run this script to create the tables:
    python migrations/add_compression_batching.py

Rollback:
    python migrations/add_compression_batching.py --rollback
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
    """Create compression and batching tables."""

    # Create enum for priority tiers
    create_priority_enum_sql = """
    DO $$ BEGIN
        CREATE TYPE document_priority_enum AS ENUM (
            'critical', 'high', 'medium', 'low', 'routine'
        );
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """

    # Create compressed summaries table
    create_summaries_table_sql = """
    CREATE TABLE IF NOT EXISTS dd_compressed_summaries (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,
        document_id UUID NOT NULL,
        run_id UUID REFERENCES dd_analysis_run(id) ON DELETE CASCADE,

        -- Document metadata
        document_name VARCHAR(500),
        folder_category VARCHAR(100),
        document_type VARCHAR(200),

        -- Priority information
        priority document_priority_enum DEFAULT 'medium',
        priority_score FLOAT DEFAULT 50.0,
        priority_reasons JSONB,

        -- Compressed content
        summary TEXT NOT NULL,
        summary_tokens INTEGER DEFAULT 0,
        key_provisions JSONB,
        key_parties JSONB,
        key_dates JSONB,
        key_amounts JSONB,
        risk_flags JSONB,

        -- Context from Pass 2
        pass2_finding_summary TEXT,
        finding_count INTEGER DEFAULT 0,

        -- Compression metrics
        original_tokens INTEGER DEFAULT 0,
        compression_ratio FLOAT DEFAULT 0.0,
        compression_error TEXT,

        -- Timestamps
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),

        -- Unique constraint: one summary per document per run
        UNIQUE(dd_id, document_id, run_id)
    );
    """

    # Create batch execution tracking table
    create_batch_table_sql = """
    CREATE TABLE IF NOT EXISTS dd_batch_execution (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,
        run_id UUID REFERENCES dd_analysis_run(id) ON DELETE CASCADE,
        batch_number INTEGER NOT NULL,

        -- Batch composition
        document_count INTEGER DEFAULT 0,
        total_tokens INTEGER DEFAULT 0,
        document_ids JSONB,
        folders JSONB,
        primary_folder VARCHAR(100),

        -- Priority composition
        critical_count INTEGER DEFAULT 0,
        high_count INTEGER DEFAULT 0,

        -- Execution status
        status VARCHAR(50) DEFAULT 'pending',
        started_at TIMESTAMP,
        completed_at TIMESTAMP,

        -- Cross-batch context
        prior_findings_used INTEGER DEFAULT 0,

        -- Results
        findings_generated INTEGER DEFAULT 0,
        error_message TEXT,

        -- Timestamps
        created_at TIMESTAMP DEFAULT NOW(),

        -- Unique constraint: one batch number per run
        UNIQUE(dd_id, run_id, batch_number)
    );
    """

    # Add compression columns to checkpoint table
    alter_checkpoint_sql = """
    ALTER TABLE dd_processing_checkpoint
    ADD COLUMN IF NOT EXISTS compression_enabled BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS batching_enabled BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS total_batches INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS batches_completed INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS compression_stats JSONB,
    ADD COLUMN IF NOT EXISTS batch_stats JSONB;
    """

    # Create indexes
    create_indexes_sql = """
    -- Compressed summaries indexes
    CREATE INDEX IF NOT EXISTS idx_dd_compressed_summaries_dd_id
    ON dd_compressed_summaries(dd_id);

    CREATE INDEX IF NOT EXISTS idx_dd_compressed_summaries_run_id
    ON dd_compressed_summaries(run_id);

    CREATE INDEX IF NOT EXISTS idx_dd_compressed_summaries_document_id
    ON dd_compressed_summaries(document_id);

    CREATE INDEX IF NOT EXISTS idx_dd_compressed_summaries_priority
    ON dd_compressed_summaries(priority);

    -- Batch execution indexes
    CREATE INDEX IF NOT EXISTS idx_dd_batch_execution_dd_id
    ON dd_batch_execution(dd_id);

    CREATE INDEX IF NOT EXISTS idx_dd_batch_execution_run_id
    ON dd_batch_execution(run_id);

    CREATE INDEX IF NOT EXISTS idx_dd_batch_execution_status
    ON dd_batch_execution(status);
    """

    with engine.connect() as conn:
        # Create enum type
        print("Creating document_priority_enum type...")
        conn.execute(text(create_priority_enum_sql))
        conn.commit()

        # Create compressed summaries table
        print("Creating dd_compressed_summaries table...")
        conn.execute(text(create_summaries_table_sql))
        conn.commit()

        # Create batch execution table
        print("Creating dd_batch_execution table...")
        conn.execute(text(create_batch_table_sql))
        conn.commit()

        # Alter checkpoint table
        print("Adding compression columns to dd_processing_checkpoint...")
        conn.execute(text(alter_checkpoint_sql))
        conn.commit()

        # Create indexes
        print("Creating indexes...")
        conn.execute(text(create_indexes_sql))
        conn.commit()

        print("Migration completed successfully!")
        print("")
        print("Tables created:")
        print("  - dd_compressed_summaries: Store compressed document summaries")
        print("  - dd_batch_execution: Track batch execution progress")
        print("")
        print("Columns added to dd_processing_checkpoint:")
        print("  - compression_enabled, batching_enabled")
        print("  - total_batches, batches_completed")
        print("  - compression_stats, batch_stats (JSONB)")


def rollback_migration():
    """Drop the compression and batching tables."""

    drop_tables_sql = """
    DROP TABLE IF EXISTS dd_batch_execution CASCADE;
    DROP TABLE IF EXISTS dd_compressed_summaries CASCADE;
    """

    remove_columns_sql = """
    ALTER TABLE dd_processing_checkpoint
    DROP COLUMN IF EXISTS compression_enabled,
    DROP COLUMN IF EXISTS batching_enabled,
    DROP COLUMN IF EXISTS total_batches,
    DROP COLUMN IF EXISTS batches_completed,
    DROP COLUMN IF EXISTS compression_stats,
    DROP COLUMN IF EXISTS batch_stats;
    """

    drop_enum_sql = """
    DROP TYPE IF EXISTS document_priority_enum CASCADE;
    """

    with engine.connect() as conn:
        print("Dropping tables...")
        conn.execute(text(drop_tables_sql))
        conn.commit()

        print("Removing columns from dd_processing_checkpoint...")
        conn.execute(text(remove_columns_sql))
        conn.commit()

        print("Dropping enum type...")
        conn.execute(text(drop_enum_sql))
        conn.commit()

        print("Rollback completed!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Phase 4 Compression & Batching migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    args = parser.parse_args()

    if args.rollback:
        rollback_migration()
    else:
        run_migration()
