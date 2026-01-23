"""
Migration: Add actual_page_number and clause_reference columns to perspective_risk_finding table

These columns enable:
- actual_page_number: Integer page number for document navigation (1-indexed)
- clause_reference: Specific clause/section reference (e.g., "Clause 15.2.1")

Also adds extracted_text_with_pages and total_pages to document table.

Run with: python migrations/add_page_clause_columns.py
"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.session import engine
from sqlalchemy import text


def migrate():
    """Add page and clause columns to relevant tables."""

    with engine.connect() as conn:
        # 1. Add actual_page_number to perspective_risk_finding
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'perspective_risk_finding'
            AND column_name = 'actual_page_number'
        """))

        if result.fetchone():
            print("Column 'actual_page_number' already exists in perspective_risk_finding table")
        else:
            print("Adding 'actual_page_number' column to perspective_risk_finding table...")
            conn.execute(text("""
                ALTER TABLE perspective_risk_finding
                ADD COLUMN actual_page_number INTEGER
            """))
            print("Successfully added 'actual_page_number' column")

        # 2. Add clause_reference to perspective_risk_finding (if not exists)
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'perspective_risk_finding'
            AND column_name = 'clause_reference'
        """))

        if result.fetchone():
            print("Column 'clause_reference' already exists in perspective_risk_finding table")
        else:
            print("Adding 'clause_reference' column to perspective_risk_finding table...")
            conn.execute(text("""
                ALTER TABLE perspective_risk_finding
                ADD COLUMN clause_reference TEXT
            """))
            print("Successfully added 'clause_reference' column")

        # 3. Add extracted_text_with_pages to document table
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'document'
            AND column_name = 'extracted_text_with_pages'
        """))

        if result.fetchone():
            print("Column 'extracted_text_with_pages' already exists in document table")
        else:
            print("Adding 'extracted_text_with_pages' column to document table...")
            conn.execute(text("""
                ALTER TABLE document
                ADD COLUMN extracted_text_with_pages TEXT
            """))
            print("Successfully added 'extracted_text_with_pages' column")

        # 4. Add total_pages to document table
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'document'
            AND column_name = 'total_pages'
        """))

        if result.fetchone():
            print("Column 'total_pages' already exists in document table")
        else:
            print("Adding 'total_pages' column to document table...")
            conn.execute(text("""
                ALTER TABLE document
                ADD COLUMN total_pages INTEGER
            """))
            print("Successfully added 'total_pages' column")

        conn.commit()
        print("\nMigration completed successfully!")


if __name__ == "__main__":
    migrate()
