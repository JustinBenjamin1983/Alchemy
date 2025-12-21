"""
Migration: Add folder context columns to perspective_risk_finding table
Date: 2025-12-20
Description: Adds columns for Phase 3 folder-aware processing:
  - folder_category: Links finding to its source folder (01_Corporate, 02_Commercial, etc.)
  - question_id: Links finding to specific blueprint question that generated it
  - is_cross_document: Boolean for cross-document findings
  - related_document_ids: JSON array of document IDs involved in cross-doc findings
"""

import os
import psycopg2
from psycopg2 import sql


def get_connection():
    """Get database connection from environment"""
    conn_string = os.environ.get("DB_CONNECTION_STRING")
    if not conn_string:
        raise ValueError("DB_CONNECTION_STRING environment variable not set")
    return psycopg2.connect(conn_string)


def run_migration():
    """Run the migration to add folder context columns"""
    conn = get_connection()
    cur = conn.cursor()

    try:
        # Get existing columns
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'perspective_risk_finding';
        """)
        existing_columns = {row[0] for row in cur.fetchall()}
        print(f"Existing columns in perspective_risk_finding: {len(existing_columns)} columns")

        # Define new columns for folder-aware processing
        new_columns = [
            # Folder category from blueprint folder structure
            # e.g., "01_Corporate", "02_Commercial", "03_Financial"
            ("folder_category", "VARCHAR(50)"),

            # Question ID from blueprint folder_questions
            # Links finding to specific question that generated it
            ("question_id", "TEXT"),

            # Whether this finding involves multiple documents (cross-doc analysis)
            ("is_cross_document", "BOOLEAN DEFAULT FALSE"),

            # JSON array of document IDs for cross-document findings
            # Stored as TEXT containing JSON: ["uuid1", "uuid2"]
            ("related_document_ids", "TEXT"),

            # Source cluster for Pass 3 findings
            # e.g., "corporate_governance", "financial", "operational_regulatory"
            ("source_cluster", "VARCHAR(50)"),
        ]

        for column_name, column_def in new_columns:
            if column_name not in existing_columns:
                print(f"Adding column: {column_name}")
                cur.execute(
                    sql.SQL("ALTER TABLE perspective_risk_finding ADD COLUMN {} {}").format(
                        sql.Identifier(column_name),
                        sql.SQL(column_def)
                    )
                )
            else:
                print(f"Column {column_name} already exists, skipping")

        # Create index on folder_category for filtering
        print("Creating index on folder_category...")
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_finding_folder_category
            ON perspective_risk_finding (folder_category)
            WHERE folder_category IS NOT NULL;
        """)

        # Create index on question_id for tracking question-to-finding links
        print("Creating index on question_id...")
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_finding_question_id
            ON perspective_risk_finding (question_id)
            WHERE question_id IS NOT NULL;
        """)

        # Create index on is_cross_document for filtering cross-doc findings
        print("Creating index on is_cross_document...")
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_finding_cross_document
            ON perspective_risk_finding (is_cross_document)
            WHERE is_cross_document = TRUE;
        """)

        # Create composite index for folder + run queries
        print("Creating composite index on folder_category + run_id...")
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_finding_folder_run
            ON perspective_risk_finding (folder_category, run_id)
            WHERE folder_category IS NOT NULL AND run_id IS NOT NULL;
        """)

        conn.commit()
        print("Migration completed successfully!")
        print("\nNew columns added:")
        for col_name, col_def in new_columns:
            print(f"  - {col_name}: {col_def}")

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def rollback_migration():
    """Rollback the migration (drop added columns and indexes)"""
    conn = get_connection()
    cur = conn.cursor()

    try:
        # Drop indexes first
        indexes_to_drop = [
            "idx_finding_folder_category",
            "idx_finding_question_id",
            "idx_finding_cross_document",
            "idx_finding_folder_run",
        ]

        for index_name in indexes_to_drop:
            print(f"Dropping index: {index_name}")
            cur.execute(
                sql.SQL("DROP INDEX IF EXISTS {}").format(
                    sql.Identifier(index_name)
                )
            )

        # Drop columns
        columns_to_drop = [
            "folder_category",
            "question_id",
            "is_cross_document",
            "related_document_ids",
            "source_cluster",
        ]

        for column_name in columns_to_drop:
            print(f"Dropping column: {column_name}")
            cur.execute(
                sql.SQL("ALTER TABLE perspective_risk_finding DROP COLUMN IF EXISTS {}").format(
                    sql.Identifier(column_name)
                )
            )

        conn.commit()
        print("Rollback completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"Rollback failed: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def verify_migration():
    """Verify the migration was applied correctly"""
    conn = get_connection()
    cur = conn.cursor()

    try:
        # Check columns exist
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'perspective_risk_finding'
            AND column_name IN ('folder_category', 'question_id', 'is_cross_document', 'related_document_ids', 'source_cluster')
            ORDER BY column_name;
        """)
        columns = cur.fetchall()

        print("Column verification:")
        for col_name, data_type, is_nullable in columns:
            print(f"  - {col_name}: {data_type} (nullable: {is_nullable})")

        if len(columns) != 5:
            print(f"WARNING: Expected 5 columns, found {len(columns)}")
            return False

        # Check indexes exist
        cur.execute("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'perspective_risk_finding'
            AND indexname LIKE 'idx_finding_%';
        """)
        indexes = [row[0] for row in cur.fetchall()]

        print("\nIndex verification:")
        for idx in indexes:
            print(f"  - {idx}")

        print("\nVerification complete!")
        return True

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "rollback":
            rollback_migration()
        elif sys.argv[1] == "verify":
            verify_migration()
        else:
            print(f"Unknown command: {sys.argv[1]}")
            print("Usage: python add_finding_folder_context.py [rollback|verify]")
    else:
        run_migration()
