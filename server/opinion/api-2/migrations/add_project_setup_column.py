"""
Migration: Add project_setup column to due_diligence table

This column stores the full wizard data as JSON, enabling the UI to display
all the wizard inputs directly without parsing from the briefing string.

Run with: python migrations/add_project_setup_column.py
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.session import transactional_session
from sqlalchemy import text


def run_migration():
    """Add project_setup JSON column to due_diligence table."""

    with transactional_session() as session:
        # Check if column already exists
        check_sql = text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'due_diligence'
            AND column_name = 'project_setup'
        """)
        result = session.execute(check_sql).fetchone()

        if result:
            print("Column 'project_setup' already exists in 'due_diligence' table. Skipping.")
            return

        # Add the column
        alter_sql = text("""
            ALTER TABLE due_diligence
            ADD COLUMN project_setup JSONB DEFAULT NULL
        """)

        session.execute(alter_sql)
        session.commit()

        print("Successfully added 'project_setup' column to 'due_diligence' table.")


if __name__ == "__main__":
    run_migration()
