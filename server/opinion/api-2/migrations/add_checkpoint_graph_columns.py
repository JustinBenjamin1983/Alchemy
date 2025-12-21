"""
Migration: Add graph columns to dd_processing_checkpoint

Phase 5: Knowledge Graph - adds columns to track graph building stats
in the processing checkpoint for progress display.
"""

import os
import psycopg2
from psycopg2 import sql


def run_migration():
    """Add graph_vertices and graph_edges columns to dd_processing_checkpoint."""

    connection_string = os.environ.get("DB_CONNECTION_STRING")
    if not connection_string:
        raise ValueError("DB_CONNECTION_STRING environment variable not set")

    conn = psycopg2.connect(connection_string)
    conn.autocommit = False
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'dd_processing_checkpoint'
            AND column_name IN ('graph_vertices', 'graph_edges')
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]

        columns_added = []

        # Add graph_vertices if not exists
        if 'graph_vertices' not in existing_columns:
            cursor.execute("""
                ALTER TABLE dd_processing_checkpoint
                ADD COLUMN graph_vertices INTEGER DEFAULT 0
            """)
            columns_added.append('graph_vertices')
            print("Added column: graph_vertices")

        # Add graph_edges if not exists
        if 'graph_edges' not in existing_columns:
            cursor.execute("""
                ALTER TABLE dd_processing_checkpoint
                ADD COLUMN graph_edges INTEGER DEFAULT 0
            """)
            columns_added.append('graph_edges')
            print("Added column: graph_edges")

        if columns_added:
            conn.commit()
            print(f"Migration complete: Added {len(columns_added)} column(s)")
        else:
            print("Migration skipped: All columns already exist")

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    run_migration()
