"""
Migration: Add parallel processing tables for Phase 6

Creates tables for:
- Document processing state (for incremental runs)
- Job execution tracking (audit trail)
- Synthesis results (hierarchical synthesis)
"""

import os
import psycopg2


def run_migration():
    """Add parallel processing tables."""

    connection_string = os.environ.get("DB_CONNECTION_STRING")
    if not connection_string:
        raise ValueError("DB_CONNECTION_STRING environment variable not set")

    conn = psycopg2.connect(connection_string)
    conn.autocommit = False
    cursor = conn.cursor()

    try:
        # Track document processing state for incremental runs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dd_document_processing_state (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                run_id UUID NOT NULL,
                document_id UUID NOT NULL,
                document_name VARCHAR(500),
                content_hash VARCHAR(32),
                folder_category VARCHAR(100),
                ai_category VARCHAR(100),
                pass1_completed BOOLEAN DEFAULT FALSE,
                pass2_completed BOOLEAN DEFAULT FALSE,
                entity_extracted BOOLEAN DEFAULT FALSE,
                compressed BOOLEAN DEFAULT FALSE,
                pass1_result JSONB,
                pass2_findings JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

                UNIQUE(run_id, document_id)
            )
        """)
        print("Created table: dd_document_processing_state")

        # Track parallel job execution (audit trail)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dd_job_execution (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                run_id UUID NOT NULL,
                job_id VARCHAR(100) NOT NULL,
                job_type VARCHAR(50) NOT NULL,
                document_id UUID,
                batch_id VARCHAR(100),
                cluster_id VARCHAR(100),
                status VARCHAR(20) DEFAULT 'pending',
                priority INTEGER DEFAULT 5,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                estimated_tokens INTEGER,
                actual_tokens INTEGER,
                started_at TIMESTAMP WITH TIME ZONE,
                completed_at TIMESTAMP WITH TIME ZONE,
                duration_ms INTEGER,
                error_message TEXT,
                result_summary JSONB,
                worker_id INTEGER,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

                UNIQUE(run_id, job_id)
            )
        """)
        print("Created table: dd_job_execution")

        # Track synthesis hierarchy results
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dd_synthesis_result (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                run_id UUID NOT NULL,
                synthesis_level VARCHAR(20) NOT NULL,
                source_id VARCHAR(100),
                source_ids JSONB DEFAULT '[]'::jsonb,
                parent_synthesis_id UUID REFERENCES dd_synthesis_result(id),
                summary TEXT,
                key_risks JSONB DEFAULT '[]'::jsonb,
                deal_blockers JSONB DEFAULT '[]'::jsonb,
                recommendations JSONB DEFAULT '[]'::jsonb,
                patterns JSONB DEFAULT '[]'::jsonb,
                gaps JSONB DEFAULT '[]'::jsonb,
                findings_count INTEGER DEFAULT 0,
                input_tokens INTEGER,
                output_tokens INTEGER,
                model_used VARCHAR(50),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        print("Created table: dd_synthesis_result")

        # Track failed documents for retry
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dd_failed_documents (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                run_id UUID NOT NULL,
                document_id UUID NOT NULL,
                document_name VARCHAR(500),
                failed_stage VARCHAR(50),
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                last_retry_at TIMESTAMP WITH TIME ZONE,
                resolved BOOLEAN DEFAULT FALSE,
                resolved_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

                UNIQUE(run_id, document_id, failed_stage)
            )
        """)
        print("Created table: dd_failed_documents")

        # Add parallel processing columns to dd_processing_checkpoint
        cursor.execute("""
            ALTER TABLE dd_processing_checkpoint
            ADD COLUMN IF NOT EXISTS processing_mode VARCHAR(20) DEFAULT 'sequential',
            ADD COLUMN IF NOT EXISTS parallel_workers INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS documents_from_cache INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS documents_failed INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS failed_documents JSONB DEFAULT '[]'::jsonb,
            ADD COLUMN IF NOT EXISTS partial_results BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS previous_run_id UUID,
            ADD COLUMN IF NOT EXISTS synthesis_progress INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS synthesis_level VARCHAR(20)
        """)
        print("Added parallel processing columns to dd_processing_checkpoint")

        # Create indexes
        indexes = [
            ("idx_doc_proc_state_run", "dd_document_processing_state", "run_id"),
            ("idx_doc_proc_state_doc", "dd_document_processing_state", "document_id"),
            ("idx_doc_proc_state_hash", "dd_document_processing_state", "content_hash"),
            ("idx_job_exec_run", "dd_job_execution", "run_id"),
            ("idx_job_exec_status", "dd_job_execution", "run_id, status"),
            ("idx_job_exec_type", "dd_job_execution", "run_id, job_type"),
            ("idx_job_exec_doc", "dd_job_execution", "document_id"),
            ("idx_synthesis_run", "dd_synthesis_result", "run_id"),
            ("idx_synthesis_level", "dd_synthesis_result", "run_id, synthesis_level"),
            ("idx_synthesis_parent", "dd_synthesis_result", "parent_synthesis_id"),
            ("idx_failed_docs_run", "dd_failed_documents", "run_id"),
            ("idx_failed_docs_resolved", "dd_failed_documents", "run_id, resolved"),
        ]

        for idx_name, table, columns in indexes:
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({columns})
            """)
            print(f"Created index: {idx_name}")

        # Add foreign key constraints if tables exist
        # Note: These are optional - we don't enforce FK to allow flexibility
        cursor.execute("""
            DO $$
            BEGIN
                -- Try to add FK to dd_analysis_run if it exists
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'dd_analysis_run') THEN
                    BEGIN
                        ALTER TABLE dd_document_processing_state
                        ADD CONSTRAINT fk_doc_proc_state_run
                        FOREIGN KEY (run_id) REFERENCES dd_analysis_run(id) ON DELETE CASCADE;
                    EXCEPTION WHEN duplicate_object THEN NULL;
                    END;

                    BEGIN
                        ALTER TABLE dd_job_execution
                        ADD CONSTRAINT fk_job_exec_run
                        FOREIGN KEY (run_id) REFERENCES dd_analysis_run(id) ON DELETE CASCADE;
                    EXCEPTION WHEN duplicate_object THEN NULL;
                    END;

                    BEGIN
                        ALTER TABLE dd_synthesis_result
                        ADD CONSTRAINT fk_synthesis_run
                        FOREIGN KEY (run_id) REFERENCES dd_analysis_run(id) ON DELETE CASCADE;
                    EXCEPTION WHEN duplicate_object THEN NULL;
                    END;

                    BEGIN
                        ALTER TABLE dd_failed_documents
                        ADD CONSTRAINT fk_failed_docs_run
                        FOREIGN KEY (run_id) REFERENCES dd_analysis_run(id) ON DELETE CASCADE;
                    EXCEPTION WHEN duplicate_object THEN NULL;
                    END;
                END IF;

                -- Try to add FK to document if it exists
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'document') THEN
                    BEGIN
                        ALTER TABLE dd_document_processing_state
                        ADD CONSTRAINT fk_doc_proc_state_doc
                        FOREIGN KEY (document_id) REFERENCES document(id) ON DELETE CASCADE;
                    EXCEPTION WHEN duplicate_object THEN NULL;
                    END;

                    BEGIN
                        ALTER TABLE dd_job_execution
                        ADD CONSTRAINT fk_job_exec_doc
                        FOREIGN KEY (document_id) REFERENCES document(id) ON DELETE SET NULL;
                    EXCEPTION WHEN duplicate_object THEN NULL;
                    END;

                    BEGIN
                        ALTER TABLE dd_failed_documents
                        ADD CONSTRAINT fk_failed_docs_doc
                        FOREIGN KEY (document_id) REFERENCES document(id) ON DELETE CASCADE;
                    EXCEPTION WHEN duplicate_object THEN NULL;
                    END;
                END IF;
            END $$;
        """)
        print("Added foreign key constraints (where applicable)")

        conn.commit()
        print("Migration complete: Parallel processing tables created")

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    run_migration()
