#!/usr/bin/env python3
"""
Migration: Add Entity Mapping columns to dd_wizard_draft table

Adds Phase 1 Enhancement columns for entity mapping context:
- target_registration_number: Company registration number
- known_subsidiaries: JSON array of known subsidiaries
- holding_company: JSON object with holding company details
- expected_counterparties: JSON array of counterparty names
- key_contractors: JSON array for contractors (separate from customers)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text


def run_migration():
    """Run the migration to add entity mapping columns."""

    connection_string = os.environ.get("DB_CONNECTION_STRING")
    if not connection_string:
        print("ERROR: DB_CONNECTION_STRING environment variable not set")
        sys.exit(1)

    engine = create_engine(connection_string)

    # Columns to add with their SQL definitions
    columns_to_add = [
        # Entity Mapping Context columns
        ("target_registration_number", "TEXT"),
        ("known_subsidiaries", "TEXT"),  # JSON array
        ("holding_company", "TEXT"),  # JSON object
        ("expected_counterparties", "TEXT"),  # JSON array
        ("key_contractors", "TEXT"),  # JSON array
    ]

    with engine.connect() as conn:
        print("Adding entity mapping columns to dd_wizard_draft table...")

        for column_name, column_type in columns_to_add:
            try:
                conn.execute(text(f"""
                    ALTER TABLE dd_wizard_draft
                    ADD COLUMN IF NOT EXISTS {column_name} {column_type};
                """))
                print(f"  - Added column: {column_name}")
            except Exception as e:
                print(f"  - Column {column_name} might already exist or error: {e}")

        conn.commit()
        print("\nMigration completed successfully!")


if __name__ == "__main__":
    run_migration()
