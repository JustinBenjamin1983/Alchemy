#!/usr/bin/env python3
"""
Migration: Add Entity Mapping Tables

Creates the following tables:
- dd_entity_map: Entity mapping for transaction parties
- dd_document_reference: References to other documents

These tables support entity confirmation checkpoint and document gap analysis.
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

def run_migration():
    """Run the migration to add entity mapping tables."""

    connection_string = os.environ.get("DB_CONNECTION_STRING")
    if not connection_string:
        print("ERROR: DB_CONNECTION_STRING environment variable not set")
        sys.exit(1)

    engine = create_engine(connection_string)

    with engine.connect() as conn:
        # Create dd_entity_map table
        print("Creating dd_entity_map table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dd_entity_map (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,
                run_id UUID REFERENCES dd_analysis_run(id) ON DELETE CASCADE,

                -- Entity identification
                entity_name VARCHAR(500) NOT NULL,
                registration_number VARCHAR(100),

                -- Relationship classification
                relationship_to_target VARCHAR(50) NOT NULL,
                relationship_detail TEXT,

                -- Confidence and evidence
                confidence FLOAT DEFAULT 0.5,
                documents_appearing_in JSONB,
                evidence TEXT,

                -- Human confirmation
                requires_human_confirmation BOOLEAN DEFAULT FALSE,
                human_confirmed BOOLEAN DEFAULT FALSE,
                human_confirmation_value VARCHAR(50),

                -- Timestamps
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """))
        print("  - dd_entity_map table created")

        # Create indexes for dd_entity_map
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_dd_entity_map_dd_id ON dd_entity_map(dd_id);
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_dd_entity_map_run_id ON dd_entity_map(run_id);
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_dd_entity_map_entity_name ON dd_entity_map(entity_name);
        """))
        print("  - Indexes created for dd_entity_map")

        # Create dd_document_reference table
        print("Creating dd_document_reference table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dd_document_reference (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                run_id UUID NOT NULL REFERENCES dd_analysis_run(id) ON DELETE CASCADE,
                source_document_id UUID NOT NULL REFERENCES document(id) ON DELETE CASCADE,

                -- Reference details
                referenced_document_name VARCHAR(500) NOT NULL,
                reference_context TEXT,
                reference_type VARCHAR(50),
                criticality VARCHAR(20),
                clause_reference VARCHAR(200),
                quote TEXT,

                -- Matching status
                found_in_data_room BOOLEAN,
                matched_document_id UUID REFERENCES document(id) ON DELETE SET NULL,

                -- Timestamps
                created_at TIMESTAMP DEFAULT NOW()
            );
        """))
        print("  - dd_document_reference table created")

        # Create indexes for dd_document_reference
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_dd_document_reference_run_id ON dd_document_reference(run_id);
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_dd_document_reference_source_doc ON dd_document_reference(source_document_id);
        """))
        print("  - Indexes created for dd_document_reference")

        conn.commit()
        print("\nMigration completed successfully!")


if __name__ == "__main__":
    run_migration()
