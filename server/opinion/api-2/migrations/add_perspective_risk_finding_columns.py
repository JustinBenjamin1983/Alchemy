#!/usr/bin/env python3
"""
Migration: Add missing columns to perspective_risk_finding table

Adds Phase 1 Enhancement columns that exist in the ORM model but not in the database.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

def run_migration():
    """Run the migration to add missing columns."""

    connection_string = os.environ.get("DB_CONNECTION_STRING")
    if not connection_string:
        print("ERROR: DB_CONNECTION_STRING environment variable not set")
        sys.exit(1)

    engine = create_engine(connection_string)

    # Columns to add with their SQL definitions
    columns_to_add = [
        # Action Category columns (Task 4)
        ("action_category", "VARCHAR(50)"),
        ("resolution_mechanism", "VARCHAR(100)"),
        ("resolution_responsible_party", "VARCHAR(50)"),
        ("resolution_timeline", "VARCHAR(50)"),
        ("resolution_cost", "FLOAT"),
        ("resolution_cost_confidence", "FLOAT"),
        ("resolution_description", "TEXT"),

        # Materiality columns (Task 3)
        ("materiality_classification", "VARCHAR(50)"),
        ("materiality_ratio", "FLOAT"),
        ("materiality_threshold", "VARCHAR(200)"),
        ("materiality_qualitative_override", "VARCHAR(200)"),

        # Confidence Calibration columns (Task 6)
        ("confidence_finding_exists", "FLOAT"),
        ("confidence_severity", "FLOAT"),
        ("confidence_amount", "FLOAT"),
        ("confidence_basis", "TEXT"),

        # Statutory Reference columns (Task 2)
        ("statutory_act", "VARCHAR(200)"),
        ("statutory_section", "VARCHAR(100)"),
        ("statutory_consequence", "TEXT"),
        ("regulatory_body", "VARCHAR(200)"),
    ]

    with engine.connect() as conn:
        print("Adding missing columns to perspective_risk_finding table...")

        for column_name, column_type in columns_to_add:
            try:
                conn.execute(text(f"""
                    ALTER TABLE perspective_risk_finding
                    ADD COLUMN IF NOT EXISTS {column_name} {column_type};
                """))
                print(f"  - Added column: {column_name}")
            except Exception as e:
                print(f"  - Column {column_name} might already exist or error: {e}")

        conn.commit()
        print("\nMigration completed successfully!")


if __name__ == "__main__":
    run_migration()
