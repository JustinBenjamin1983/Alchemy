# File: server/opinion/api-2/migrations/add_pipeline_progress_tracking.py
"""
Migration: Add Enhanced Pipeline Progress Tracking

Adds new columns to dd_processing_checkpoint and creates dd_entity_confirmation table
for granular progress tracking and entity confirmation auto-save.

Run with: python migrations/add_pipeline_progress_tracking.py
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_connection_string():
    """Get database connection string from environment."""
    return os.environ.get("DB_CONNECTION_STRING")


def run_migration():
    """Run the migration to add pipeline progress tracking."""
    conn_string = get_connection_string()
    if not conn_string:
        logger.error("DB_CONNECTION_STRING not set")
        return False

    engine = create_engine(conn_string)

    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()

        try:
            # 1. Add new columns to dd_processing_checkpoint
            logger.info("Adding pipeline_stage column to dd_processing_checkpoint...")

            # Pipeline stage - tracks current position in the full pipeline
            try:
                conn.execute(text("""
                    ALTER TABLE dd_processing_checkpoint
                    ADD COLUMN IF NOT EXISTS pipeline_stage VARCHAR(100) DEFAULT 'wizard'
                """))
            except ProgrammingError:
                logger.info("pipeline_stage column already exists")

            # Stage completion tracking (JSON array of completed stage names)
            try:
                conn.execute(text("""
                    ALTER TABLE dd_processing_checkpoint
                    ADD COLUMN IF NOT EXISTS completed_stages JSONB DEFAULT '[]'::jsonb
                """))
            except ProgrammingError:
                logger.info("completed_stages column already exists")

            # Pre-processing stage progress
            try:
                conn.execute(text("""
                    ALTER TABLE dd_processing_checkpoint
                    ADD COLUMN IF NOT EXISTS classification_progress INTEGER DEFAULT 0
                """))
            except ProgrammingError:
                pass

            try:
                conn.execute(text("""
                    ALTER TABLE dd_processing_checkpoint
                    ADD COLUMN IF NOT EXISTS readability_progress INTEGER DEFAULT 0
                """))
            except ProgrammingError:
                pass

            try:
                conn.execute(text("""
                    ALTER TABLE dd_processing_checkpoint
                    ADD COLUMN IF NOT EXISTS entity_mapping_progress INTEGER DEFAULT 0
                """))
            except ProgrammingError:
                pass

            # Processing phase progress (passes 5-7)
            try:
                conn.execute(text("""
                    ALTER TABLE dd_processing_checkpoint
                    ADD COLUMN IF NOT EXISTS pass5_progress INTEGER DEFAULT 0
                """))
            except ProgrammingError:
                pass

            try:
                conn.execute(text("""
                    ALTER TABLE dd_processing_checkpoint
                    ADD COLUMN IF NOT EXISTS pass6_progress INTEGER DEFAULT 0
                """))
            except ProgrammingError:
                pass

            try:
                conn.execute(text("""
                    ALTER TABLE dd_processing_checkpoint
                    ADD COLUMN IF NOT EXISTS pass7_progress INTEGER DEFAULT 0
                """))
            except ProgrammingError:
                pass

            # Classification granular tracking
            try:
                conn.execute(text("""
                    ALTER TABLE dd_processing_checkpoint
                    ADD COLUMN IF NOT EXISTS classified_doc_ids JSONB DEFAULT '[]'::jsonb
                """))
            except ProgrammingError:
                pass

            try:
                conn.execute(text("""
                    ALTER TABLE dd_processing_checkpoint
                    ADD COLUMN IF NOT EXISTS classification_errors JSONB DEFAULT '[]'::jsonb
                """))
            except ProgrammingError:
                pass

            # Resume capability
            try:
                conn.execute(text("""
                    ALTER TABLE dd_processing_checkpoint
                    ADD COLUMN IF NOT EXISTS resume_from_stage VARCHAR(100) DEFAULT NULL
                """))
            except ProgrammingError:
                pass

            try:
                conn.execute(text("""
                    ALTER TABLE dd_processing_checkpoint
                    ADD COLUMN IF NOT EXISTS paused_at TIMESTAMP DEFAULT NULL
                """))
            except ProgrammingError:
                pass

            try:
                conn.execute(text("""
                    ALTER TABLE dd_processing_checkpoint
                    ADD COLUMN IF NOT EXISTS resumed_at TIMESTAMP DEFAULT NULL
                """))
            except ProgrammingError:
                pass

            logger.info("Added columns to dd_processing_checkpoint")

            # 2. Create dd_validation_checkpoint table if it doesn't exist (dependency)
            logger.info("Creating dd_validation_checkpoint table if needed...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS dd_validation_checkpoint (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,
                    run_id UUID,
                    checkpoint_type VARCHAR(50) NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
                    preliminary_summary TEXT,
                    questions JSONB,
                    missing_docs JSONB,
                    financial_confirmations JSONB,
                    user_responses JSONB,
                    uploaded_doc_ids JSONB,
                    manual_data_inputs JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    completed_at TIMESTAMP,
                    completed_by VARCHAR(255)
                )
            """))
            logger.info("dd_validation_checkpoint table ready")

            # 3. Create dd_entity_confirmation table for auto-save
            logger.info("Creating dd_entity_confirmation table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS dd_entity_confirmation (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,
                    checkpoint_id UUID REFERENCES dd_validation_checkpoint(id) ON DELETE SET NULL,

                    -- Entity pair being confirmed
                    entity_a_name VARCHAR(500) NOT NULL,
                    entity_a_type VARCHAR(100),
                    entity_b_name VARCHAR(500),
                    entity_b_type VARCHAR(100),

                    -- Relationship details
                    relationship_type VARCHAR(100),  -- parent, subsidiary, related_party, counterparty, unknown
                    relationship_detail TEXT,
                    ai_confidence FLOAT,

                    -- User decision
                    user_decision VARCHAR(50),  -- confirmed, rejected, corrected, skipped
                    user_correction TEXT,  -- If user corrected the relationship
                    user_notes TEXT,

                    -- Document evidence
                    source_document_ids JSONB DEFAULT '[]'::jsonb,
                    evidence_text TEXT,

                    -- Timestamps
                    created_at TIMESTAMP DEFAULT NOW(),
                    confirmed_at TIMESTAMP,
                    confirmed_by VARCHAR(255),

                    -- Ensure uniqueness per DD and entity pair
                    UNIQUE(dd_id, entity_a_name, entity_b_name)
                )
            """))

            # Create index for faster lookups
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_entity_confirmation_dd_id
                ON dd_entity_confirmation(dd_id)
            """))

            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_entity_confirmation_checkpoint
                ON dd_entity_confirmation(checkpoint_id)
            """))

            logger.info("Created dd_entity_confirmation table")

            # 4. Create dd_classification_progress table for granular saves
            logger.info("Creating dd_classification_progress table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS dd_classification_progress (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,
                    document_id UUID NOT NULL REFERENCES document(id) ON DELETE CASCADE,

                    -- Classification result
                    status VARCHAR(50) DEFAULT 'pending',  -- pending, classifying, classified, failed
                    category VARCHAR(100),
                    subcategory VARCHAR(100),
                    document_type VARCHAR(200),
                    confidence INTEGER,
                    key_parties JSONB DEFAULT '[]'::jsonb,
                    reasoning TEXT,

                    -- Error tracking
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,

                    -- Timestamps
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,

                    UNIQUE(dd_id, document_id)
                )
            """))

            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_classification_progress_dd_id
                ON dd_classification_progress(dd_id)
            """))

            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_classification_progress_status
                ON dd_classification_progress(status)
            """))

            logger.info("Created dd_classification_progress table")

            # Commit transaction
            trans.commit()
            logger.info("Migration completed successfully!")
            return True

        except Exception as e:
            trans.rollback()
            logger.error(f"Migration failed: {e}")
            raise


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
