"""
Migration: Add reasoning column to perspective_risk_finding table

This column stores the Chain of Thought (CoT) reasoning steps as JSON.
Format: {"step_1_identification": "...", "step_2_context": "...", ...}

Run with: python migrations/add_reasoning_column.py
"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.session import engine
from sqlalchemy import text


def migrate():
    """Add reasoning column to perspective_risk_finding table."""

    with engine.connect() as conn:
        # Check if column already exists
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'perspective_risk_finding'
            AND column_name = 'reasoning'
        """))

        if result.fetchone():
            print("Column 'reasoning' already exists in perspective_risk_finding table")
            return

        # Add the column
        print("Adding 'reasoning' column to perspective_risk_finding table...")
        conn.execute(text("""
            ALTER TABLE perspective_risk_finding
            ADD COLUMN reasoning TEXT
        """))
        conn.commit()

        print("Successfully added 'reasoning' column")


if __name__ == "__main__":
    migrate()
