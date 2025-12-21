"""
Migration: Add model_tier column to dd_analysis_run table

This allows users to select the accuracy/cost tier for each analysis run:
- cost_optimized: Haiku -> Sonnet -> Sonnet -> Sonnet (cheapest)
- balanced: Haiku -> Sonnet -> Opus -> Sonnet (default)
- high_accuracy: Haiku -> Sonnet -> Opus -> Opus
- maximum_accuracy: Haiku -> Opus -> Opus -> Opus (most expensive)

Run with: python migrations/add_model_tier_column.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from shared.session import transactional_session


def run_migration():
    """Add model_tier column to dd_analysis_run table."""
    with transactional_session() as session:
        # Check if column already exists
        check_query = text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'dd_analysis_run'
            AND column_name = 'model_tier'
        """)
        result = session.execute(check_query).fetchone()

        if result:
            print("Column 'model_tier' already exists in dd_analysis_run table")
            return

        # Add the column
        alter_query = text("""
            ALTER TABLE dd_analysis_run
            ADD COLUMN model_tier TEXT DEFAULT 'balanced'
        """)
        session.execute(alter_query)
        session.commit()
        print("Successfully added 'model_tier' column to dd_analysis_run table")


if __name__ == "__main__":
    run_migration()
