"""
Migration: Add folder organisation columns for Phase 2 Blueprint Folder Organisation.

This migration:
1. Adds organisation columns to folder table (folder_category, is_blueprint_folder, etc.)
2. Adds original_folder_id to document table (to preserve ZIP origin)
3. Adds folder_assignment_source to document table

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
    """Add folder organisation columns to folder and document tables."""

    # Step 1: Add organisation columns to folder table
    add_folder_columns_sql = """
    DO $$
    BEGIN
        -- folder_category: Standard category code (01_Corporate, 02_Commercial, etc.)
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'folder' AND column_name = 'folder_category'
        ) THEN
            ALTER TABLE folder ADD COLUMN folder_category VARCHAR(50);
        END IF;

        -- is_blueprint_folder: TRUE for blueprint-created folders, FALSE for original ZIP folders
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'folder' AND column_name = 'is_blueprint_folder'
        ) THEN
            ALTER TABLE folder ADD COLUMN is_blueprint_folder BOOLEAN DEFAULT FALSE;
        END IF;

        -- expected_doc_types: JSON array of expected document types for this folder
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'folder' AND column_name = 'expected_doc_types'
        ) THEN
            ALTER TABLE folder ADD COLUMN expected_doc_types JSONB DEFAULT '[]'::jsonb;
        END IF;

        -- sort_order: Numeric sort order (01, 02, 03... extracted from category)
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'folder' AND column_name = 'sort_order'
        ) THEN
            ALTER TABLE folder ADD COLUMN sort_order INTEGER DEFAULT 99;
        END IF;

        -- relevance: Transaction-type-specific relevance (critical, high, medium, low, n/a)
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'folder' AND column_name = 'relevance'
        ) THEN
            ALTER TABLE folder ADD COLUMN relevance VARCHAR(20);
        END IF;

        -- document_count: Cached count of documents in folder (for display)
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'folder' AND column_name = 'document_count'
        ) THEN
            ALTER TABLE folder ADD COLUMN document_count INTEGER DEFAULT 0;
        END IF;
    END $$;
    """

    # Step 2: Add indexes for folder sorting and filtering
    create_folder_indexes_sql = """
    CREATE INDEX IF NOT EXISTS idx_folder_sort_order ON folder(dd_id, sort_order);
    CREATE INDEX IF NOT EXISTS idx_folder_category ON folder(folder_category);
    CREATE INDEX IF NOT EXISTS idx_folder_blueprint ON folder(is_blueprint_folder);
    """

    # Step 3: Add original_folder_id to document table (preserves ZIP origin)
    add_document_columns_sql = """
    DO $$
    BEGIN
        -- original_folder_id: The folder document was originally in from ZIP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'document' AND column_name = 'original_folder_id'
        ) THEN
            ALTER TABLE document ADD COLUMN original_folder_id UUID REFERENCES folder(id) ON DELETE SET NULL;
        END IF;

        -- folder_assignment_source: How doc was assigned to current folder
        -- Values: 'original_zip', 'ai', 'manual'
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'document' AND column_name = 'folder_assignment_source'
        ) THEN
            ALTER TABLE document ADD COLUMN folder_assignment_source VARCHAR(20) DEFAULT 'original_zip';
        END IF;
    END $$;
    """

    # Step 4: Create index on original_folder_id
    create_document_indexes_sql = """
    CREATE INDEX IF NOT EXISTS idx_document_original_folder ON document(original_folder_id);
    CREATE INDEX IF NOT EXISTS idx_document_assignment_source ON document(folder_assignment_source);
    """

    # Step 5: Add Phase 2 columns to dd_organisation_status table
    add_org_status_columns_sql = """
    DO $$
    BEGIN
        -- organised_count: Documents moved to blueprint folders
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'dd_organisation_status' AND column_name = 'organised_count'
        ) THEN
            ALTER TABLE dd_organisation_status ADD COLUMN organised_count INTEGER DEFAULT 0;
        END IF;

        -- needs_review_count: Documents in 99_Needs_Review folder
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'dd_organisation_status' AND column_name = 'needs_review_count'
        ) THEN
            ALTER TABLE dd_organisation_status ADD COLUMN needs_review_count INTEGER DEFAULT 0;
        END IF;

        -- organised_at: Timestamp when organisation completed
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'dd_organisation_status' AND column_name = 'organised_at'
        ) THEN
            ALTER TABLE dd_organisation_status ADD COLUMN organised_at TIMESTAMP;
        END IF;
    END $$;
    """

    with engine.connect() as conn:
        # Add folder columns
        print("Adding organisation columns to folder table...")
        conn.execute(text(add_folder_columns_sql))
        conn.commit()

        # Create folder indexes
        print("Creating indexes for folder table...")
        conn.execute(text(create_folder_indexes_sql))
        conn.commit()

        # Add document columns
        print("Adding original_folder_id and folder_assignment_source to document table...")
        conn.execute(text(add_document_columns_sql))
        conn.commit()

        # Create document indexes
        print("Creating indexes for document table...")
        conn.execute(text(create_document_indexes_sql))
        conn.commit()

        # Add organisation status columns
        print("Adding Phase 2 columns to dd_organisation_status table...")
        conn.execute(text(add_org_status_columns_sql))
        conn.commit()

        print("Migration completed successfully!")


def rollback_migration():
    """Rollback the migration - drops the organisation columns."""

    # Remove folder columns
    drop_folder_columns_sql = """
    ALTER TABLE folder DROP COLUMN IF EXISTS folder_category;
    ALTER TABLE folder DROP COLUMN IF EXISTS is_blueprint_folder;
    ALTER TABLE folder DROP COLUMN IF EXISTS expected_doc_types;
    ALTER TABLE folder DROP COLUMN IF EXISTS sort_order;
    ALTER TABLE folder DROP COLUMN IF EXISTS relevance;
    ALTER TABLE folder DROP COLUMN IF EXISTS document_count;
    """

    # Remove document columns
    drop_document_columns_sql = """
    ALTER TABLE document DROP COLUMN IF EXISTS original_folder_id;
    ALTER TABLE document DROP COLUMN IF EXISTS folder_assignment_source;
    """

    # Remove organisation status columns
    drop_org_status_columns_sql = """
    ALTER TABLE dd_organisation_status DROP COLUMN IF EXISTS organised_count;
    ALTER TABLE dd_organisation_status DROP COLUMN IF EXISTS needs_review_count;
    ALTER TABLE dd_organisation_status DROP COLUMN IF EXISTS organised_at;
    """

    with engine.connect() as conn:
        print("Rolling back: Removing folder organisation columns...")
        conn.execute(text(drop_folder_columns_sql))
        conn.commit()

        print("Rolling back: Removing document organisation columns...")
        conn.execute(text(drop_document_columns_sql))
        conn.commit()

        print("Rolling back: Removing organisation status columns...")
        conn.execute(text(drop_org_status_columns_sql))
        conn.commit()

        print("Rollback completed!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Folder Organisation migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    args = parser.parse_args()

    if args.rollback:
        rollback_migration()
    else:
        run_migration()
