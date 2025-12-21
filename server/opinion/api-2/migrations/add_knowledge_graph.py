"""
Migration: Add Knowledge Graph tables (Phase 5)

Creates relational tables to model a graph structure for DD entity relationships.
Designed for 300-500 documents, 150 parties, 1000 obligations, 2000 edges.

Run this script to create the tables:
    python migrations/add_knowledge_graph.py

Rollback:
    python migrations/add_knowledge_graph.py --rollback
"""
import os
import sys
import json

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Load environment from local.settings.json
settings_path = os.path.join(parent_dir, "local.settings.json")
if os.path.exists(settings_path):
    with open(settings_path) as f:
        settings = json.load(f)
        for key, value in settings.get("Values", {}).items():
            if key not in os.environ:
                os.environ[key] = value

from shared.session import engine
from sqlalchemy import text


def run_migration():
    """Create knowledge graph tables."""

    # ============================================
    # VERTEX TABLES (Nodes)
    # ============================================

    create_party_table = """
    CREATE TABLE IF NOT EXISTS kg_party (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,
        run_id UUID REFERENCES dd_analysis_run(id) ON DELETE CASCADE,

        -- Party identification
        name VARCHAR(500) NOT NULL,
        normalized_name VARCHAR(500) NOT NULL,  -- Lowercase, trimmed for matching
        party_type VARCHAR(50),  -- company, individual, government, trust
        role VARCHAR(100),  -- buyer, seller, borrower, lender, landlord, tenant

        -- Additional details
        jurisdiction VARCHAR(100),
        registration_number VARCHAR(100),

        -- Source tracking
        first_seen_document_id UUID REFERENCES document(id) ON DELETE SET NULL,
        source_documents JSONB DEFAULT '[]'::jsonb,  -- All docs mentioning this party

        -- Metadata
        metadata JSONB DEFAULT '{}'::jsonb,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

        -- Unique constraint per DD (deduplicated by normalized name)
        UNIQUE(dd_id, normalized_name)
    );
    """

    create_agreement_table = """
    CREATE TABLE IF NOT EXISTS kg_agreement (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,
        run_id UUID REFERENCES dd_analysis_run(id) ON DELETE CASCADE,
        document_id UUID REFERENCES document(id) ON DELETE CASCADE,

        -- Agreement details
        name VARCHAR(500) NOT NULL,
        agreement_type VARCHAR(100),  -- loan, supply, shareholders, lease, service, etc.

        -- Key dates
        effective_date DATE,
        expiry_date DATE,

        -- Legal details
        governing_law VARCHAR(100),

        -- Transaction-relevant flags
        has_change_of_control BOOLEAN DEFAULT FALSE,
        has_assignment_restriction BOOLEAN DEFAULT FALSE,
        has_consent_requirement BOOLEAN DEFAULT FALSE,

        -- Metadata
        metadata JSONB DEFAULT '{}'::jsonb,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """

    create_obligation_table = """
    CREATE TABLE IF NOT EXISTS kg_obligation (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,
        run_id UUID REFERENCES dd_analysis_run(id) ON DELETE CASCADE,
        document_id UUID REFERENCES document(id) ON DELETE CASCADE,
        agreement_id UUID REFERENCES kg_agreement(id) ON DELETE CASCADE,

        -- Obligation details
        description TEXT NOT NULL,
        obligation_type VARCHAR(100),  -- payment, delivery, consent, notification, compliance

        -- Parties (references to kg_party)
        obligor_party_id UUID REFERENCES kg_party(id) ON DELETE SET NULL,
        obligee_party_id UUID REFERENCES kg_party(id) ON DELETE SET NULL,

        -- Source reference
        clause_reference VARCHAR(100),

        -- Timing
        due_date DATE,
        due_date_description VARCHAR(500),  -- e.g., "within 30 days of X"

        -- Financial
        amount DECIMAL(20,2),
        currency VARCHAR(10) DEFAULT 'ZAR',

        -- Importance
        is_material BOOLEAN DEFAULT FALSE,

        -- Metadata
        metadata JSONB DEFAULT '{}'::jsonb,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """

    create_trigger_table = """
    CREATE TABLE IF NOT EXISTS kg_trigger (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,
        run_id UUID REFERENCES dd_analysis_run(id) ON DELETE CASCADE,
        document_id UUID REFERENCES document(id) ON DELETE CASCADE,
        agreement_id UUID REFERENCES kg_agreement(id) ON DELETE CASCADE,

        -- Trigger details
        trigger_type VARCHAR(100) NOT NULL,  -- change_of_control, default, termination, expiry, breach, insolvency
        description TEXT,

        -- Source
        clause_reference VARCHAR(100),

        -- Conditions
        threshold_description VARCHAR(500),  -- e.g., ">50% shareholding change"

        -- Effects
        consequences TEXT,  -- What happens when triggered

        -- Metadata
        metadata JSONB DEFAULT '{}'::jsonb,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """

    create_amount_table = """
    CREATE TABLE IF NOT EXISTS kg_amount (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,
        run_id UUID REFERENCES dd_analysis_run(id) ON DELETE CASCADE,
        document_id UUID REFERENCES document(id) ON DELETE CASCADE,

        -- Amount details
        value DECIMAL(20,2) NOT NULL,
        currency VARCHAR(10) DEFAULT 'ZAR',
        context VARCHAR(500),  -- What is this amount for
        amount_type VARCHAR(100),  -- principal, limit, fee, penalty, purchase_price, rental

        -- Source
        clause_reference VARCHAR(100),

        -- Metadata
        metadata JSONB DEFAULT '{}'::jsonb,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """

    create_date_table = """
    CREATE TABLE IF NOT EXISTS kg_date (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,
        run_id UUID REFERENCES dd_analysis_run(id) ON DELETE CASCADE,
        document_id UUID REFERENCES document(id) ON DELETE CASCADE,

        -- Date details
        date_value DATE,
        date_description VARCHAR(500),  -- For relative dates like "30 days after signing"
        significance VARCHAR(500),  -- What this date represents
        date_type VARCHAR(100),  -- effective, expiry, deadline, milestone

        -- Importance
        is_critical BOOLEAN DEFAULT FALSE,

        -- Metadata
        metadata JSONB DEFAULT '{}'::jsonb,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """

    # ============================================
    # EDGE TABLES (Relationships)
    # ============================================

    create_edge_party_to = """
    CREATE TABLE IF NOT EXISTS kg_edge_party_to (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,
        party_id UUID NOT NULL REFERENCES kg_party(id) ON DELETE CASCADE,

        -- Target can be document or agreement
        target_type VARCHAR(50) NOT NULL,  -- 'document' or 'agreement'
        document_id UUID REFERENCES document(id) ON DELETE CASCADE,
        agreement_id UUID REFERENCES kg_agreement(id) ON DELETE CASCADE,

        -- Role in this relationship
        role VARCHAR(100),  -- buyer, seller, borrower, lender, landlord, tenant, etc.

        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

        -- Prevent duplicates
        UNIQUE(party_id, target_type, document_id, agreement_id),

        CHECK (
            (target_type = 'document' AND document_id IS NOT NULL) OR
            (target_type = 'agreement' AND agreement_id IS NOT NULL)
        )
    );
    """

    create_edge_triggers = """
    CREATE TABLE IF NOT EXISTS kg_edge_triggers (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,
        trigger_id UUID NOT NULL REFERENCES kg_trigger(id) ON DELETE CASCADE,
        obligation_id UUID NOT NULL REFERENCES kg_obligation(id) ON DELETE CASCADE,

        -- Effect of trigger on obligation
        trigger_effect VARCHAR(100),  -- accelerates, terminates, requires_consent, suspends

        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

        UNIQUE(trigger_id, obligation_id)
    );
    """

    create_edge_requires_consent = """
    CREATE TABLE IF NOT EXISTS kg_edge_requires_consent (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,
        agreement_id UUID NOT NULL REFERENCES kg_agreement(id) ON DELETE CASCADE,
        party_id UUID NOT NULL REFERENCES kg_party(id) ON DELETE CASCADE,

        -- Consent details
        consent_type VARCHAR(100),  -- change_of_control, assignment, amendment, waiver
        clause_reference VARCHAR(100),

        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

        UNIQUE(agreement_id, party_id, consent_type)
    );
    """

    create_edge_references = """
    CREATE TABLE IF NOT EXISTS kg_edge_references (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,

        -- Source (document or agreement)
        source_document_id UUID REFERENCES document(id) ON DELETE CASCADE,
        source_agreement_id UUID REFERENCES kg_agreement(id) ON DELETE CASCADE,

        -- Target (document or agreement)
        target_document_id UUID REFERENCES document(id) ON DELETE CASCADE,
        target_agreement_id UUID REFERENCES kg_agreement(id) ON DELETE CASCADE,

        -- Reference details
        reference_type VARCHAR(100),  -- incorporates, amends, supplements, replaces, refers_to
        reference_text VARCHAR(500),  -- The actual reference text found

        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """

    create_edge_conflicts_with = """
    CREATE TABLE IF NOT EXISTS kg_edge_conflicts_with (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,

        -- Conflicting obligations
        source_obligation_id UUID REFERENCES kg_obligation(id) ON DELETE CASCADE,
        target_obligation_id UUID REFERENCES kg_obligation(id) ON DELETE CASCADE,

        -- Conflict details
        conflict_description TEXT,
        severity VARCHAR(20),  -- critical, high, medium, low

        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """

    create_edge_secures = """
    CREATE TABLE IF NOT EXISTS kg_edge_secures (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,
        security_agreement_id UUID NOT NULL REFERENCES kg_agreement(id) ON DELETE CASCADE,
        secured_obligation_id UUID NOT NULL REFERENCES kg_obligation(id) ON DELETE CASCADE,

        -- Security details
        security_type VARCHAR(100),  -- mortgage, pledge, cession, guarantee, surety
        asset_description TEXT,

        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """

    # ============================================
    # GRAPH BUILD STATUS TABLE
    # ============================================

    create_graph_status_table = """
    CREATE TABLE IF NOT EXISTS kg_build_status (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        dd_id UUID NOT NULL REFERENCES due_diligence(id) ON DELETE CASCADE,
        run_id UUID REFERENCES dd_analysis_run(id) ON DELETE CASCADE,

        -- Build status
        status VARCHAR(50) DEFAULT 'pending',  -- pending, building, completed, failed

        -- Statistics
        party_count INTEGER DEFAULT 0,
        agreement_count INTEGER DEFAULT 0,
        obligation_count INTEGER DEFAULT 0,
        trigger_count INTEGER DEFAULT 0,
        amount_count INTEGER DEFAULT 0,
        date_count INTEGER DEFAULT 0,
        edge_count INTEGER DEFAULT 0,

        documents_processed INTEGER DEFAULT 0,
        total_documents INTEGER DEFAULT 0,

        -- Timing
        started_at TIMESTAMP WITH TIME ZONE,
        completed_at TIMESTAMP WITH TIME ZONE,

        -- Error handling
        error_message TEXT,

        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

        UNIQUE(dd_id, run_id)
    );
    """

    # ============================================
    # INDEXES FOR GRAPH TRAVERSAL
    # ============================================

    create_indexes = """
    -- Party indexes
    CREATE INDEX IF NOT EXISTS idx_kg_party_dd ON kg_party(dd_id);
    CREATE INDEX IF NOT EXISTS idx_kg_party_normalized ON kg_party(dd_id, normalized_name);
    CREATE INDEX IF NOT EXISTS idx_kg_party_type ON kg_party(dd_id, party_type);

    -- Agreement indexes
    CREATE INDEX IF NOT EXISTS idx_kg_agreement_dd ON kg_agreement(dd_id);
    CREATE INDEX IF NOT EXISTS idx_kg_agreement_doc ON kg_agreement(document_id);
    CREATE INDEX IF NOT EXISTS idx_kg_agreement_type ON kg_agreement(dd_id, agreement_type);
    CREATE INDEX IF NOT EXISTS idx_kg_agreement_coc ON kg_agreement(dd_id, has_change_of_control)
        WHERE has_change_of_control = TRUE;
    CREATE INDEX IF NOT EXISTS idx_kg_agreement_consent ON kg_agreement(dd_id, has_consent_requirement)
        WHERE has_consent_requirement = TRUE;

    -- Obligation indexes
    CREATE INDEX IF NOT EXISTS idx_kg_obligation_dd ON kg_obligation(dd_id);
    CREATE INDEX IF NOT EXISTS idx_kg_obligation_agreement ON kg_obligation(agreement_id);
    CREATE INDEX IF NOT EXISTS idx_kg_obligation_material ON kg_obligation(dd_id, is_material)
        WHERE is_material = TRUE;

    -- Trigger indexes
    CREATE INDEX IF NOT EXISTS idx_kg_trigger_dd ON kg_trigger(dd_id);
    CREATE INDEX IF NOT EXISTS idx_kg_trigger_type ON kg_trigger(dd_id, trigger_type);
    CREATE INDEX IF NOT EXISTS idx_kg_trigger_agreement ON kg_trigger(agreement_id);

    -- Amount indexes
    CREATE INDEX IF NOT EXISTS idx_kg_amount_dd ON kg_amount(dd_id);
    CREATE INDEX IF NOT EXISTS idx_kg_amount_type ON kg_amount(dd_id, amount_type);

    -- Date indexes
    CREATE INDEX IF NOT EXISTS idx_kg_date_dd ON kg_date(dd_id);
    CREATE INDEX IF NOT EXISTS idx_kg_date_critical ON kg_date(dd_id, is_critical)
        WHERE is_critical = TRUE;

    -- Edge indexes
    CREATE INDEX IF NOT EXISTS idx_kg_edge_party_to_party ON kg_edge_party_to(party_id);
    CREATE INDEX IF NOT EXISTS idx_kg_edge_party_to_doc ON kg_edge_party_to(document_id);
    CREATE INDEX IF NOT EXISTS idx_kg_edge_party_to_agreement ON kg_edge_party_to(agreement_id);

    CREATE INDEX IF NOT EXISTS idx_kg_edge_triggers_trigger ON kg_edge_triggers(trigger_id);
    CREATE INDEX IF NOT EXISTS idx_kg_edge_triggers_obligation ON kg_edge_triggers(obligation_id);

    CREATE INDEX IF NOT EXISTS idx_kg_edge_requires_consent_agreement ON kg_edge_requires_consent(agreement_id);
    CREATE INDEX IF NOT EXISTS idx_kg_edge_requires_consent_party ON kg_edge_requires_consent(party_id);

    CREATE INDEX IF NOT EXISTS idx_kg_edge_references_source ON kg_edge_references(source_document_id);
    CREATE INDEX IF NOT EXISTS idx_kg_edge_references_target ON kg_edge_references(target_document_id);

    -- Build status indexes
    CREATE INDEX IF NOT EXISTS idx_kg_build_status_dd ON kg_build_status(dd_id);
    CREATE INDEX IF NOT EXISTS idx_kg_build_status_status ON kg_build_status(status);
    """

    with engine.connect() as conn:
        print("Creating kg_party table...")
        conn.execute(text(create_party_table))
        conn.commit()

        print("Creating kg_agreement table...")
        conn.execute(text(create_agreement_table))
        conn.commit()

        print("Creating kg_obligation table...")
        conn.execute(text(create_obligation_table))
        conn.commit()

        print("Creating kg_trigger table...")
        conn.execute(text(create_trigger_table))
        conn.commit()

        print("Creating kg_amount table...")
        conn.execute(text(create_amount_table))
        conn.commit()

        print("Creating kg_date table...")
        conn.execute(text(create_date_table))
        conn.commit()

        print("Creating edge tables...")
        conn.execute(text(create_edge_party_to))
        conn.commit()
        conn.execute(text(create_edge_triggers))
        conn.commit()
        conn.execute(text(create_edge_requires_consent))
        conn.commit()
        conn.execute(text(create_edge_references))
        conn.commit()
        conn.execute(text(create_edge_conflicts_with))
        conn.commit()
        conn.execute(text(create_edge_secures))
        conn.commit()

        print("Creating kg_build_status table...")
        conn.execute(text(create_graph_status_table))
        conn.commit()

        print("Creating indexes...")
        conn.execute(text(create_indexes))
        conn.commit()

        print("\nMigration completed successfully!")
        print("")
        print("Vertex tables created:")
        print("  - kg_party: Parties mentioned in documents")
        print("  - kg_agreement: Agreements/contracts extracted")
        print("  - kg_obligation: Obligations and commitments")
        print("  - kg_trigger: Triggering events (CoC, default, etc.)")
        print("  - kg_amount: Monetary amounts")
        print("  - kg_date: Significant dates")
        print("")
        print("Edge tables created:")
        print("  - kg_edge_party_to: Party involvement in docs/agreements")
        print("  - kg_edge_triggers: Trigger -> Obligation relationships")
        print("  - kg_edge_requires_consent: Consent requirements")
        print("  - kg_edge_references: Cross-document references")
        print("  - kg_edge_conflicts_with: Conflicting obligations")
        print("  - kg_edge_secures: Security arrangements")
        print("")
        print("Status table created:")
        print("  - kg_build_status: Graph build progress tracking")


def rollback_migration():
    """Drop all knowledge graph tables."""

    drop_tables_sql = """
    -- Drop edge tables first (foreign key dependencies)
    DROP TABLE IF EXISTS kg_edge_secures CASCADE;
    DROP TABLE IF EXISTS kg_edge_conflicts_with CASCADE;
    DROP TABLE IF EXISTS kg_edge_references CASCADE;
    DROP TABLE IF EXISTS kg_edge_requires_consent CASCADE;
    DROP TABLE IF EXISTS kg_edge_triggers CASCADE;
    DROP TABLE IF EXISTS kg_edge_party_to CASCADE;

    -- Drop vertex tables
    DROP TABLE IF EXISTS kg_date CASCADE;
    DROP TABLE IF EXISTS kg_amount CASCADE;
    DROP TABLE IF EXISTS kg_trigger CASCADE;
    DROP TABLE IF EXISTS kg_obligation CASCADE;
    DROP TABLE IF EXISTS kg_agreement CASCADE;
    DROP TABLE IF EXISTS kg_party CASCADE;

    -- Drop status table
    DROP TABLE IF EXISTS kg_build_status CASCADE;
    """

    with engine.connect() as conn:
        print("Dropping all knowledge graph tables...")
        conn.execute(text(drop_tables_sql))
        conn.commit()
        print("Rollback completed!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Phase 5 Knowledge Graph migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    args = parser.parse_args()

    if args.rollback:
        rollback_migration()
    else:
        run_migration()
