"""
Migration: Add enhanced finding columns to perspective_risk_finding table
Date: 2025-12-11
Description: Adds new columns for deal impact, financial exposure, and analysis tracking
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
    """Run the migration to add enhanced finding columns"""
    conn = get_connection()
    cur = conn.cursor()

    try:
        # Check if DealImpactEnum type exists
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'deal_impact_enum'
            );
        """)
        enum_exists = cur.fetchone()[0]

        if not enum_exists:
            print("Creating deal_impact_enum type...")
            cur.execute("""
                CREATE TYPE deal_impact_enum AS ENUM (
                    'deal_blocker', 'condition_precedent', 'price_chip',
                    'warranty_indemnity', 'post_closing', 'noted', 'none'
                );
            """)

        # Get existing columns
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'perspective_risk_finding';
        """)
        existing_columns = {row[0] for row in cur.fetchall()}
        print(f"Existing columns: {existing_columns}")

        # Define new columns to add
        new_columns = [
            ("deal_impact", "deal_impact_enum DEFAULT 'none'"),
            ("financial_exposure_amount", "FLOAT"),
            ("financial_exposure_currency", "VARCHAR(10) DEFAULT 'ZAR'"),
            ("financial_exposure_calculation", "TEXT"),
            ("clause_reference", "TEXT"),
            ("cross_doc_source", "TEXT"),
            ("analysis_pass", "INTEGER DEFAULT 2"),
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

        conn.commit()
        print("Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def rollback_migration():
    """Rollback the migration (drop added columns)"""
    conn = get_connection()
    cur = conn.cursor()

    try:
        columns_to_drop = [
            "deal_impact",
            "financial_exposure_amount",
            "financial_exposure_currency",
            "financial_exposure_calculation",
            "clause_reference",
            "cross_doc_source",
            "analysis_pass",
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

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        run_migration()
