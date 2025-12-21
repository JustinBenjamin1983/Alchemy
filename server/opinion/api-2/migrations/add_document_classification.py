"""
Migration: Add AI Document Classification columns and organisation status table.

This migration:
1. Adds classification columns to the document table
2. Creates the dd_organisation_status table for tracking classification progress

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


# Standardised folder categories for AI classification
FOLDER_CATEGORIES = {
    "01_Corporate": {
        "subcategories": ["Constitutional", "Governance", "Resolutions", "Shareholding"],
        "expected_doc_types": ["MOI", "Shareholders Agreement", "Board Resolution", "Share Certificate", "Company Registration"]
    },
    "02_Commercial": {
        "subcategories": ["Supply Agreements", "Offtake", "Service Contracts", "JV Agreements", "Toll Processing"],
        "expected_doc_types": ["Supply Agreement", "Offtake Agreement", "Service Level Agreement", "Joint Venture Agreement"]
    },
    "03_Financial": {
        "subcategories": ["Loan Agreements", "Security", "Guarantees", "Financial Statements"],
        "expected_doc_types": ["Loan Agreement", "Mortgage Bond", "Guarantee", "Financial Statement", "Audit Report"]
    },
    "04_Regulatory": {
        "subcategories": ["Mining Rights", "Environmental", "Water Use", "Licenses", "Permits"],
        "expected_doc_types": ["Mining Right", "Environmental Authorisation", "Water Use License", "Prospecting Right"]
    },
    "05_Employment": {
        "subcategories": ["Executive Contracts", "Policies", "Union Agreements", "Benefit Plans"],
        "expected_doc_types": ["Employment Contract", "HR Policy", "Recognition Agreement", "Pension Fund Rules"]
    },
    "06_Property": {
        "subcategories": ["Owned", "Leased", "Servitudes", "Surface Rights"],
        "expected_doc_types": ["Title Deed", "Lease Agreement", "Servitude Agreement", "Surface Right Agreement"]
    },
    "07_Insurance": {
        "subcategories": ["Policies", "Claims"],
        "expected_doc_types": ["Insurance Policy", "Certificate of Insurance", "Claims Record"]
    },
    "08_Litigation": {
        "subcategories": ["Pending", "Threatened", "Settled"],
        "expected_doc_types": ["Summons", "Pleading", "Settlement Agreement", "Court Order", "Legal Opinion"]
    },
    "09_Tax": {
        "subcategories": ["Returns", "Assessments", "Rulings", "Disputes"],
        "expected_doc_types": ["Tax Return", "Tax Assessment", "Tax Ruling", "Tax Clearance Certificate"]
    },
    "99_Needs_Review": {
        "subcategories": ["Unclassified", "Low Confidence", "Multiple Categories"],
        "expected_doc_types": []
    }
}


def run_migration():
    """Add classification columns to document table and create organisation status table."""

    # Step 1: Add classification columns to document table
    add_classification_columns_sql = """
    DO $$
    BEGIN
        -- ai_category: The primary category assigned by AI (01_Corporate, 02_Commercial, etc.)
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'document' AND column_name = 'ai_category'
        ) THEN
            ALTER TABLE document ADD COLUMN ai_category VARCHAR(50);
        END IF;

        -- ai_subcategory: More specific classification within category
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'document' AND column_name = 'ai_subcategory'
        ) THEN
            ALTER TABLE document ADD COLUMN ai_subcategory VARCHAR(100);
        END IF;

        -- ai_document_type: Specific document type (e.g., "Shareholders Agreement", "Mining Right")
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'document' AND column_name = 'ai_document_type'
        ) THEN
            ALTER TABLE document ADD COLUMN ai_document_type VARCHAR(100);
        END IF;

        -- ai_confidence: Confidence score from 0-100
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'document' AND column_name = 'ai_confidence'
        ) THEN
            ALTER TABLE document ADD COLUMN ai_confidence DECIMAL(5,2);
        END IF;

        -- category_source: How the category was assigned (pending, ai, manual, zip_structure)
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'document' AND column_name = 'category_source'
        ) THEN
            ALTER TABLE document ADD COLUMN category_source VARCHAR(20) DEFAULT 'pending';
        END IF;

        -- ai_key_parties: JSON array of party names extracted from document
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'document' AND column_name = 'ai_key_parties'
        ) THEN
            ALTER TABLE document ADD COLUMN ai_key_parties JSONB DEFAULT '[]'::jsonb;
        END IF;

        -- classification_status: Current status of classification (pending, classifying, classified, failed)
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'document' AND column_name = 'classification_status'
        ) THEN
            ALTER TABLE document ADD COLUMN classification_status VARCHAR(20) DEFAULT 'pending';
        END IF;

        -- ai_classification_reasoning: AI's explanation for classification
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'document' AND column_name = 'ai_classification_reasoning'
        ) THEN
            ALTER TABLE document ADD COLUMN ai_classification_reasoning TEXT;
        END IF;

        -- classification_error: Error message if classification failed
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'document' AND column_name = 'classification_error'
        ) THEN
            ALTER TABLE document ADD COLUMN classification_error TEXT;
        END IF;

        -- classified_at: Timestamp of when classification completed
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'document' AND column_name = 'classified_at'
        ) THEN
            ALTER TABLE document ADD COLUMN classified_at TIMESTAMP WITH TIME ZONE;
        END IF;
    END $$;
    """

    # Step 2: Create indexes for classification columns
    create_classification_indexes_sql = """
    CREATE INDEX IF NOT EXISTS idx_document_ai_category ON document(ai_category);
    CREATE INDEX IF NOT EXISTS idx_document_classification_status ON document(classification_status);
    CREATE INDEX IF NOT EXISTS idx_document_ai_confidence ON document(ai_confidence);
    """

    # Step 3: Create dd_organisation_status table
    create_organisation_status_table_sql = """
    CREATE TABLE IF NOT EXISTS dd_organisation_status (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,

        -- Status tracking
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        -- status values: 'pending', 'classifying', 'organising', 'completed', 'failed'

        -- Progress counters
        total_documents INTEGER DEFAULT 0,
        classified_count INTEGER DEFAULT 0,
        low_confidence_count INTEGER DEFAULT 0,
        failed_count INTEGER DEFAULT 0,

        -- Category distribution (JSON object with counts per category)
        category_counts JSONB DEFAULT '{}'::jsonb,

        -- Error handling
        error_message TEXT,

        -- Timestamps
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        started_at TIMESTAMP WITH TIME ZONE,
        completed_at TIMESTAMP WITH TIME ZONE,

        -- Ensure one status record per DD
        UNIQUE(dd_id)
    );
    """

    # Step 4: Create index for organisation status
    create_organisation_status_index_sql = """
    CREATE INDEX IF NOT EXISTS idx_dd_org_status_dd_id ON dd_organisation_status(dd_id);
    CREATE INDEX IF NOT EXISTS idx_dd_org_status_status ON dd_organisation_status(status);
    """

    with engine.connect() as conn:
        # Add classification columns to document table
        print("Adding classification columns to document table...")
        conn.execute(text(add_classification_columns_sql))
        conn.commit()

        # Create indexes for classification columns
        print("Creating indexes for classification columns...")
        conn.execute(text(create_classification_indexes_sql))
        conn.commit()

        # Create dd_organisation_status table
        print("Creating dd_organisation_status table...")
        conn.execute(text(create_organisation_status_table_sql))
        conn.commit()

        # Create indexes for organisation status
        print("Creating indexes for dd_organisation_status...")
        conn.execute(text(create_organisation_status_index_sql))
        conn.commit()

        print("Migration completed successfully!")
        print(f"\nSupported categories: {list(FOLDER_CATEGORIES.keys())}")


def rollback_migration():
    """Rollback the migration - drops the classification columns and organisation status table."""

    # Remove classification columns from document table
    drop_classification_columns_sql = """
    ALTER TABLE document DROP COLUMN IF EXISTS ai_category;
    ALTER TABLE document DROP COLUMN IF EXISTS ai_subcategory;
    ALTER TABLE document DROP COLUMN IF EXISTS ai_document_type;
    ALTER TABLE document DROP COLUMN IF EXISTS ai_confidence;
    ALTER TABLE document DROP COLUMN IF EXISTS category_source;
    ALTER TABLE document DROP COLUMN IF EXISTS ai_key_parties;
    ALTER TABLE document DROP COLUMN IF EXISTS classification_status;
    ALTER TABLE document DROP COLUMN IF EXISTS ai_classification_reasoning;
    ALTER TABLE document DROP COLUMN IF EXISTS classification_error;
    ALTER TABLE document DROP COLUMN IF EXISTS classified_at;
    """

    # Drop dd_organisation_status table
    drop_organisation_status_table_sql = """
    DROP TABLE IF EXISTS dd_organisation_status CASCADE;
    """

    with engine.connect() as conn:
        print("Rolling back: Removing classification columns from document table...")
        conn.execute(text(drop_classification_columns_sql))
        conn.commit()

        print("Rolling back: Dropping dd_organisation_status table...")
        conn.execute(text(drop_organisation_status_table_sql))
        conn.commit()

        print("Rollback completed!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Document Classification migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    args = parser.parse_args()

    if args.rollback:
        rollback_migration()
    else:
        run_migration()
