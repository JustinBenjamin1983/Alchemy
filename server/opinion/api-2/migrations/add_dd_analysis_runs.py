"""
Migration: Add DD Analysis Runs table and run_id columns for multiple analysis runs support.

This migration:
1. Creates the dd_analysis_run table
2. Adds run_id column to perspective_risk_finding table
3. Adds run_id column to dd_processing_checkpoint table
4. Removes the UNIQUE constraint on dd_id in dd_processing_checkpoint (allows multiple checkpoints per DD)

Run this script to apply the migration.
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
    """Create dd_analysis_run table and add run_id columns."""

    # Step 1: Create the dd_analysis_run table
    create_analysis_run_table_sql = """
    CREATE TABLE IF NOT EXISTS dd_analysis_run (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,

        -- Run identification
        run_number INTEGER NOT NULL,
        name TEXT NOT NULL,

        -- Status (reuses existing enum)
        status processing_status_enum DEFAULT 'pending',

        -- Document selection
        selected_document_ids JSONB NOT NULL DEFAULT '[]'::jsonb,

        -- Progress tracking
        documents_processed INTEGER DEFAULT 0,
        total_documents INTEGER DEFAULT 0,

        -- Finding summary counts
        findings_total INTEGER DEFAULT 0,
        findings_critical INTEGER DEFAULT 0,
        findings_high INTEGER DEFAULT 0,
        findings_medium INTEGER DEFAULT 0,
        findings_low INTEGER DEFAULT 0,

        -- Cost tracking
        estimated_cost_usd FLOAT DEFAULT 0.0,

        -- Timestamps
        created_at TIMESTAMP DEFAULT NOW(),
        started_at TIMESTAMP,
        completed_at TIMESTAMP,

        -- Error handling
        last_error TEXT
    );
    """

    # Step 2: Create indexes for dd_analysis_run
    create_analysis_run_indexes_sql = """
    CREATE INDEX IF NOT EXISTS idx_dd_analysis_run_dd_id ON dd_analysis_run(dd_id);
    CREATE INDEX IF NOT EXISTS idx_dd_analysis_run_status ON dd_analysis_run(status);
    CREATE INDEX IF NOT EXISTS idx_dd_analysis_run_created_at ON dd_analysis_run(created_at DESC);
    """

    # Step 3: Add run_id column to perspective_risk_finding
    add_run_id_to_findings_sql = """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'perspective_risk_finding' AND column_name = 'run_id'
        ) THEN
            ALTER TABLE perspective_risk_finding
            ADD COLUMN run_id UUID REFERENCES dd_analysis_run(id) ON DELETE CASCADE;
        END IF;
    END $$;
    """

    # Step 4: Add run_id column to dd_processing_checkpoint
    add_run_id_to_checkpoint_sql = """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'dd_processing_checkpoint' AND column_name = 'run_id'
        ) THEN
            ALTER TABLE dd_processing_checkpoint
            ADD COLUMN run_id UUID REFERENCES dd_analysis_run(id) ON DELETE CASCADE;
        END IF;
    END $$;
    """

    # Step 5: Remove UNIQUE constraint on dd_id in dd_processing_checkpoint (if exists)
    # This allows multiple checkpoints per DD (one per run)
    remove_unique_constraint_sql = """
    DO $$
    BEGIN
        -- Try to drop the unique constraint if it exists
        ALTER TABLE dd_processing_checkpoint DROP CONSTRAINT IF EXISTS dd_processing_checkpoint_dd_id_key;
    EXCEPTION
        WHEN undefined_object THEN
            -- Constraint doesn't exist, that's fine
            NULL;
    END $$;
    """

    # Step 6: Create index on run_id for perspective_risk_finding
    create_finding_run_id_index_sql = """
    CREATE INDEX IF NOT EXISTS idx_perspective_risk_finding_run_id
    ON perspective_risk_finding(run_id);
    """

    # Step 7: Create index on run_id for dd_processing_checkpoint
    create_checkpoint_run_id_index_sql = """
    CREATE INDEX IF NOT EXISTS idx_dd_processing_checkpoint_run_id
    ON dd_processing_checkpoint(run_id);
    """

    with engine.connect() as conn:
        # Create dd_analysis_run table
        print("Creating dd_analysis_run table...")
        conn.execute(text(create_analysis_run_table_sql))
        conn.commit()

        # Create indexes for dd_analysis_run
        print("Creating indexes for dd_analysis_run...")
        conn.execute(text(create_analysis_run_indexes_sql))
        conn.commit()

        # Add run_id to perspective_risk_finding
        print("Adding run_id column to perspective_risk_finding...")
        conn.execute(text(add_run_id_to_findings_sql))
        conn.commit()

        # Add run_id to dd_processing_checkpoint
        print("Adding run_id column to dd_processing_checkpoint...")
        conn.execute(text(add_run_id_to_checkpoint_sql))
        conn.commit()

        # Remove UNIQUE constraint on dd_id
        print("Removing UNIQUE constraint on dd_id in dd_processing_checkpoint...")
        conn.execute(text(remove_unique_constraint_sql))
        conn.commit()

        # Create index on run_id for findings
        print("Creating index on run_id for perspective_risk_finding...")
        conn.execute(text(create_finding_run_id_index_sql))
        conn.commit()

        # Create index on run_id for checkpoint
        print("Creating index on run_id for dd_processing_checkpoint...")
        conn.execute(text(create_checkpoint_run_id_index_sql))
        conn.commit()

        print("Migration completed successfully!")


def rollback_migration():
    """Rollback the migration - drops the run_id columns and dd_analysis_run table."""

    # Remove run_id from perspective_risk_finding
    drop_run_id_from_findings_sql = """
    ALTER TABLE perspective_risk_finding DROP COLUMN IF EXISTS run_id;
    """

    # Remove run_id from dd_processing_checkpoint
    drop_run_id_from_checkpoint_sql = """
    ALTER TABLE dd_processing_checkpoint DROP COLUMN IF EXISTS run_id;
    """

    # Re-add UNIQUE constraint on dd_id (restore original behavior)
    add_unique_constraint_sql = """
    DO $$
    BEGIN
        ALTER TABLE dd_processing_checkpoint
        ADD CONSTRAINT dd_processing_checkpoint_dd_id_key UNIQUE (dd_id);
    EXCEPTION
        WHEN duplicate_table THEN
            -- Constraint already exists
            NULL;
    END $$;
    """

    # Drop dd_analysis_run table
    drop_analysis_run_table_sql = """
    DROP TABLE IF EXISTS dd_analysis_run CASCADE;
    """

    with engine.connect() as conn:
        print("Rolling back: Removing run_id from perspective_risk_finding...")
        conn.execute(text(drop_run_id_from_findings_sql))
        conn.commit()

        print("Rolling back: Removing run_id from dd_processing_checkpoint...")
        conn.execute(text(drop_run_id_from_checkpoint_sql))
        conn.commit()

        print("Rolling back: Re-adding UNIQUE constraint on dd_id...")
        conn.execute(text(add_unique_constraint_sql))
        conn.commit()

        print("Rolling back: Dropping dd_analysis_run table...")
        conn.execute(text(drop_analysis_run_table_sql))
        conn.commit()

        print("Rollback completed!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DD Analysis Runs migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    args = parser.parse_args()

    if args.rollback:
        rollback_migration()
    else:
        run_migration()
